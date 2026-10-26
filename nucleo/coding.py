"""Coding con la bóveda delante (Biblia Parte VII + VIII). Una tarea de
código pasa por tres manos de Claude —spec, builder, revisor—, todas por
la CLI (`claude -p`, la sesión de Max: sin clave, sin cobro aparte). Nunca
OpenRouter ni Venice para este trabajo: si Max llega a su límite, la
corrida para y lo dice; no cae a un motor que cobra.

Antes de la primera llamada se consulta la bóveda con el texto de la tarea
y viajan las lecciones relevantes (máximo `MAX_LECCIONES`, resumidas), con
el aviso de no re-investigarlas: ahí está el ahorro de tokens. Al terminar,
si el revisor trae una lección nueva, entra por la misma puerta que
`POST /experiencia` (`experiencia.crear_leccion`).

El builder PROPONE el cambio como diff; no escribe en disco. Aplicarlo es
de Juan Camilo (o de una sesión de Claude Code en una rama aparte).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
import experiencia
import pensar

router = APIRouter(prefix="/coding", tags=["coding"])

TEMA = "coding"
MOTOR = "claude-max"
MAX_LECCIONES = 6
AVISO_BOVEDA = "Estas son decisiones y errores previos del proyecto. Úsalas, no las re-investigues."
# Cuánto de cada sección viaja: la lección entera vive en la bóveda, al
# prompt solo le hace falta reconocerla.
LARGO_RESUMEN = 220


# — La bóveda —


def _palabras(texto: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[\wáéíóúñü]{3,}", texto.lower())))


def _consulta_fts(texto: str) -> str:
    """El texto libre de la tarea, como consulta FTS5 que no revienta: cada
    palabra de 3+ letras entre comillas, unidas con OR."""
    return " OR ".join(f'"{p}"' for p in _palabras(texto)[:12])


def _por_palabras(tarea: str, k: int) -> list[experiencia.LeccionGuardada]:
    """Respaldo directo sobre la bóveda: el índice FTS solo se reconstruye
    con `--reindexar`, así que una lección recién guardada no aparece en
    `experiencia.buscar` hasta entonces. Las lecciones son pocas; contar
    palabras en común es barato y siempre está al día."""
    buscadas = set(_palabras(tarea))
    puntaje: list[tuple[int, experiencia.LeccionGuardada]] = []
    for leccion in experiencia.listar():
        texto = " ".join((leccion.titulo, leccion.resumen, *leccion.secciones.values()))
        comunes = len(buscadas & set(_palabras(texto)))
        if comunes:
            puntaje.append((comunes, leccion))
    puntaje.sort(key=lambda p: (p[0], p[1].ultima_vez), reverse=True)
    return [leccion for _, leccion in puntaje[:k]]


def _es_de_coding(leccion: experiencia.LeccionGuardada) -> bool:
    return "coding" in leccion.tema or "error" in leccion.tema


def lecciones_para(tarea: str, k: int = MAX_LECCIONES) -> list[experiencia.LeccionGuardada]:
    """Las lecciones de la bóveda que tienen que ver con la tarea, mejor
    primero: la búsqueda híbrida y, detrás, el respaldo por palabras. Solo
    lecciones (no libros ni episodios que también indexa la búsqueda)."""
    consulta = _consulta_fts(tarea)
    if not consulta:
        return []
    carpeta = experiencia.carpeta().resolve()
    conexion = db.conectar()
    try:
        try:
            encontrados = experiencia.buscar(conexion, consulta, k=k * 2)
        except Exception as error:  # vectores sin modelo, índice roto: no tumba la tarea
            print(f"[coding] la búsqueda híbrida falló ({error}): sigo por palabras", file=sys.stderr)
            encontrados = []
    finally:
        conexion.close()
    lecciones: list[experiencia.LeccionGuardada] = []
    for resultado in encontrados:
        ruta = Path(resultado.ruta)
        if ruta.resolve().parent != carpeta or not ruta.exists():
            continue
        leida = experiencia._parsear(ruta)
        if leida is not None:
            lecciones.append(leida)
    vistas = {l.ruta.resolve() for l in lecciones}
    lecciones += [l for l in _por_palabras(tarea, k) if l.ruta.resolve() not in vistas]
    return lecciones[:k]


def ultimas_de_coding(n: int = 5) -> list[experiencia.LeccionGuardada]:
    """Las más recientes cuyo tema dice «coding» o «error»."""
    propias = [l for l in experiencia.listar() if _es_de_coding(l)]
    return sorted(propias, key=lambda l: l.ultima_vez, reverse=True)[:n]


def _recortar(texto: str, largo: int = LARGO_RESUMEN) -> str:
    plano = " ".join(texto.split())
    return plano if len(plano) <= largo else plano[: largo - 1].rstrip() + "…"


def resumen_de(leccion: experiencia.LeccionGuardada) -> str:
    """Una línea por lección: lo justo para no repetir el error o el acierto."""
    s = leccion.secciones
    if leccion.clase == "error":
        cuerpo = f"causa: {s.get('Causa real', '')} · cura: {s.get('Cura', '')}"
        if s.get("Cómo verlo antes"):
            cuerpo += f" · verlo antes: {s['Cómo verlo antes']}"
    else:
        cuerpo = f"funcionó: {s.get('Qué funcionó', '')} · cuándo: {s.get('Cuándo usarlo', '')}"
    return f"- [{leccion.clase}] {leccion.titulo} — {_recortar(cuerpo)}"


def bloque_de_experiencia(lecciones: list[experiencia.LeccionGuardada]) -> str:
    if not lecciones:
        return "La bóveda no tiene lecciones sobre esto todavía."
    return "\n".join((AVISO_BOVEDA, "", *(resumen_de(l) for l in lecciones)))


# — Las tres manos de Claude —

Etapa = Literal["spec", "builder", "revisor"]


@dataclass(frozen=True)
class Mano:
    modelo: str
    techo_segundos: float
    vueltas: int
    instrucciones: str


COMUN = (
    "Trabajas para Juan Camilo en sus repos de ~/proyectos. Español, directo, sin relleno. "
    "Solo puedes leer código (Read, Grep, Glob); no escribas archivos ni ejecutes nada. "
    "Lee solo lo que la tarea necesite."
)

MANOS: dict[Etapa, Mano] = {
    "spec": Mano(
        "sonnet",
        300.0,
        12,
        COMUN
        + " Eres el Spec Writer. Devuelve un spec corto en markdown: objetivo, archivos exactos "
        "(ruta:línea), pasos, lo que NO se toca, cómo se prueba. Si una lección de la bóveda ya "
        "responde algo, cítala en vez de investigarlo.",
    ),
    "builder": Mano(
        "opus",
        600.0,
        20,
        COMUN
        + " Eres el Builder. Con el spec, propone el cambio completo como un diff unificado "
        "(```diff). Respeta las lecciones de la bóveda: no repitas un error que ya está anotado. "
        "Al final, una línea con cómo se revierte.",
    ),
    "revisor": Mano(
        "sonnet",
        300.0,
        12,
        COMUN
        + " Eres el revisor (otro modelo del que construyó). Revisa el diff contra el spec y las "
        "lecciones. Contesta SOLO un objeto JSON, sin texto alrededor:\n"
        '{"veredicto": "aprobado" | "rechazado", "motivo": "una o dos frases", '
        '"leccion": null | {"clase": "error" | "acierto", "titulo": "...", "resumen": "...", '
        '"donde": "<repo>/<archivo>", "secciones": {...}}}\n'
        'Para "error" las secciones son exactamente: "Síntoma", "Lo que creímos", "Causa real", '
        '"Cura", "Cómo verlo antes". Para "acierto": "Qué funcionó", "Evidencia", "Cuándo usarlo". '
        "Si rechazas por un error nuevo, anótalo como \"error\". Si apruebas y hubo un fix o una "
        "decisión que sirva la próxima vez, anótala como \"acierto\". Pon una lección SOLO si es "
        "nueva: si ya está en las lecciones que te pasé, deja null.",
    ),
}


class LimiteDeMax(Exception):
    """Max llegó a su límite de uso. La corrida para: nada de caer a un
    motor que cobre aparte."""


@dataclass(frozen=True)
class Respuesta:
    texto: str
    tokens_entrada: int
    tokens_salida: int


Llamador = Callable[[Etapa, str], Respuesta | None]
"""(etapa, mensaje) → respuesta; el system prompt sale de `MANOS[etapa]`. Se inyecta en pruebas."""


def _comando(mano: Mano) -> list[str]:
    lectura = ",".join(pensar.HERRAMIENTAS_DE_LECTURA)
    return [
        pensar.BINARIO,
        "-p",
        "--model",
        mano.modelo,
        "--output-format",
        "json",
        "--system-prompt",
        mano.instrucciones,
        "--tools",
        lectura,
        *pensar._carpetas_de_codigo(),
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--allowedTools",
        lectura,
        "--disallowedTools",
        ",".join(pensar.reglas_de_no_leer()),
        "--max-turns",
        str(mano.vueltas),
    ]


def llamar_claude(etapa: Etapa, mensaje: str) -> Respuesta | None:
    """Una mano por la CLI con la sesión de Max. El entorno sale de
    `pensar._entorno`, que borra las claves de API: nunca se factura aparte."""
    mano = MANOS[etapa]
    entorno = pensar._entorno(pensar.MODOS["inteligente"] if mano.modelo == "opus" else None)
    try:
        terminado = subprocess.run(
            _comando(mano),
            input=mensaje,
            capture_output=True,
            text=True,
            timeout=mano.techo_segundos,
            env=entorno,
            cwd=pensar._cwd_de_la_cli(),
        )
    except FileNotFoundError:
        print(f"[coding] no encontré `{pensar.BINARIO}` en el PATH", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"[coding] {etapa} tardó más de {mano.techo_segundos:.0f} s", file=sys.stderr)
        return None
    salida = terminado.stdout + terminado.stderr
    if pensar.PATRON_LIMITE_ALCANZADO.search(salida):
        raise LimiteDeMax(etapa)
    if terminado.returncode != 0:
        print(f"[coding] {etapa}: la CLI terminó en {terminado.returncode}", file=sys.stderr)
        return None
    try:
        datos = json.loads(terminado.stdout)
    except json.JSONDecodeError:
        print(f"[coding] {etapa}: no entendí la respuesta de la CLI", file=sys.stderr)
        return None
    texto = datos.get("result") if isinstance(datos, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        return None
    # Lo leído y escrito en caché también es entrada: sin eso la cifra del
    # panel mostraría 6 tokens donde Claude leyó miles.
    entrada, salida_tokens = pensar._tokens(datos.get("usage"))
    leida, escrita = pensar._tokens_cacheados(datos.get("usage"))
    return Respuesta(texto=texto.strip(), tokens_entrada=entrada + leida + escrita, tokens_salida=salida_tokens)


# — La corrida —

Estado = Literal["consultando", "spec", "builder", "revisor", "aprobado", "rechazado", "fallo"]


@dataclass
class Corrida:
    id: str
    tarea: str
    estado: Estado = "consultando"
    lecciones: list[str] = field(default_factory=list)
    spec: str | None = None
    cambio: str | None = None
    motivo: str | None = None
    leccion_guardada: str | None = None
    tokens: int = 0
    empezo: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    segundos: int | None = None


def _mensaje(tarea: str, experiencia_txt: str, *partes: tuple[str, str]) -> str:
    bloques = [f"## Tarea\n\n{tarea}", f"## Bóveda\n\n{experiencia_txt}"]
    bloques += [f"## {titulo}\n\n{cuerpo}" for titulo, cuerpo in partes]
    return "\n\n".join(bloques)


def _json_de(texto: str) -> dict[str, object] | None:
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin <= inicio:
        return None
    try:
        datos = json.loads(texto[inicio : fin + 1])
    except json.JSONDecodeError:
        return None
    return datos if isinstance(datos, dict) else None


def guardar_leccion(propuesta: object, tarea: str) -> str | None:
    """La lección del revisor entra por la puerta de `POST /experiencia`.
    Si viene incompleta (422), no se guarda: el modelo redacta, no decide."""
    if not isinstance(propuesta, dict):
        return None
    try:
        nueva = experiencia.LeccionNueva(
            titulo=str(propuesta.get("titulo") or "")[:80],
            tema=TEMA,
            resumen=str(propuesta.get("resumen") or "")[:240],
            clase=propuesta.get("clase"),  # type: ignore[arg-type]  # pydantic lo valida
            donde=str(propuesta.get("donde") or f"coding/{experiencia.slug(tarea)[:40]}"),
            secciones={str(k): str(v) for k, v in dict(propuesta.get("secciones") or {}).items()},
            fuente="remi",
        )
        return experiencia.crear_leccion(nueva).archivo
    except (HTTPException, ValueError) as error:
        print(f"[coding] el revisor trajo una lección incompleta: {error}", file=sys.stderr)
        return None


def correr(corrida: Corrida, llamar: Llamador = llamar_claude) -> Corrida:
    """tarea → bóveda → spec → builder → revisor → (lección). Cada paso deja
    el estado en `corrida`, para que el panel lo vea mientras avanza."""
    arranque = time.perf_counter()
    try:
        lecciones = lecciones_para(corrida.tarea)
        corrida.lecciones = [l.titulo for l in lecciones]
        boveda = bloque_de_experiencia(lecciones)

        corrida.estado = "spec"
        spec = llamar("spec", _mensaje(corrida.tarea, boveda))
        if spec is None:
            corrida.estado, corrida.motivo = "fallo", "El spec no salió."
            return corrida
        corrida.spec, corrida.tokens = spec.texto, corrida.tokens + spec.tokens_entrada + spec.tokens_salida

        corrida.estado = "builder"
        cambio = llamar("builder", _mensaje(corrida.tarea, boveda, ("Spec", spec.texto)))
        if cambio is None:
            corrida.estado, corrida.motivo = "fallo", "El builder no devolvió cambio."
            return corrida
        corrida.cambio, corrida.tokens = cambio.texto, corrida.tokens + cambio.tokens_entrada + cambio.tokens_salida

        corrida.estado = "revisor"
        revision = llamar(
            "revisor",
            _mensaje(corrida.tarea, boveda, ("Spec", spec.texto), ("Cambio", cambio.texto)),
        )
        veredicto = _json_de(revision.texto) if revision is not None else None
        if revision is None or veredicto is None:
            corrida.estado, corrida.motivo = "fallo", "El revisor no contestó claro."
            return corrida
        corrida.tokens += revision.tokens_entrada + revision.tokens_salida
        corrida.estado = "aprobado" if veredicto.get("veredicto") == "aprobado" else "rechazado"
        corrida.motivo = str(veredicto.get("motivo") or "")
        corrida.leccion_guardada = guardar_leccion(veredicto.get("leccion"), corrida.tarea)
        return corrida
    except LimiteDeMax:
        corrida.estado, corrida.motivo = "fallo", "Max llegó a su límite. Sigo cuando se renueve."
        return corrida
    finally:
        corrida.segundos = round(time.perf_counter() - arranque)


# — La API —
#
# Una corrida a la vez (una cosa a la vez). Vive en memoria: lo que dura
# es la lección en la bóveda, no el registro de la corrida.

_CORRIDAS: dict[str, Corrida] = {}
_CANDADO = threading.Lock()


def _en_curso() -> Corrida | None:
    return next((c for c in _CORRIDAS.values() if c.estado in ("consultando", "spec", "builder", "revisor")), None)


class LeccionVista(BaseModel):
    titulo: str
    tema: str
    clase: str
    resumen: str
    ultima_vez: str
    veces: int


class EstadoCoding(BaseModel):
    motor: str
    lecciones_en_boveda: int
    lecciones_de_coding: int
    corrida_en_curso: str | None


class TareaCoding(BaseModel):
    tarea: str


class CorridaVista(BaseModel):
    id: str
    tarea: str
    estado: str
    lecciones: list[str]
    spec: str | None
    cambio: str | None
    motivo: str | None
    leccion_guardada: str | None
    tokens: int
    empezo: str
    segundos: int | None


def _vista(l: experiencia.LeccionGuardada) -> LeccionVista:
    return LeccionVista(titulo=l.titulo, tema=l.tema, clase=l.clase, resumen=l.resumen, ultima_vez=l.ultima_vez, veces=l.veces)


def _corrida_vista(c: Corrida) -> CorridaVista:
    return CorridaVista(**{k: getattr(c, k) for k in CorridaVista.model_fields})


@router.get("/estado", response_model=EstadoCoding)
def estado() -> EstadoCoding:
    todas = experiencia.listar()
    en_curso = _en_curso()
    return EstadoCoding(
        motor=MOTOR,
        lecciones_en_boveda=len(todas),
        lecciones_de_coding=sum(1 for l in todas if _es_de_coding(l)),
        corrida_en_curso=en_curso.id if en_curso else None,
    )


@router.get("/lecciones", response_model=list[LeccionVista])
def lecciones(q: str | None = None) -> list[LeccionVista]:
    """Sin `q`: las últimas de coding. Con `q`: búsqueda en toda la bóveda."""
    encontradas = lecciones_para(q, k=10) if q and q.strip() else ultimas_de_coding()
    return [_vista(l) for l in encontradas]


@router.post("/corrida", response_model=CorridaVista, status_code=202)
def nueva_corrida(cuerpo: TareaCoding) -> CorridaVista:
    tarea = cuerpo.tarea.strip()
    if not tarea:
        raise HTTPException(status_code=422, detail="falta la tarea")
    with _CANDADO:
        if _en_curso() is not None:
            raise HTTPException(status_code=409, detail="ya hay una corrida en curso")
        corrida = Corrida(id=str(uuid4()), tarea=tarea)
        _CORRIDAS[corrida.id] = corrida
    threading.Thread(target=correr, args=(corrida,), daemon=True).start()
    return _corrida_vista(corrida)


@router.get("/corrida/{corrida_id}", response_model=CorridaVista)
def ver_corrida(corrida_id: str) -> CorridaVista:
    corrida = _CORRIDAS.get(corrida_id)
    if corrida is None:
        raise HTTPException(status_code=404, detail="no conozco esa corrida")
    return _corrida_vista(corrida)

"""T8 (Biblia v3.9, Parte VII «La experiencia es memoria»): lecciones con
evidencia, no transcripts. Una sola fuente — la bóveda, con commit;
SQLite (FTS5 + los vectores que ya hay) la indexa, y se reconstruye
entera desde la bóveda con `--reindexar`. El modelo solo redacta: nunca
decide qué es verdad ni dónde se guarda algo.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import boveda_git
import db
import episodios
import libros
import vectores

router = APIRouter(prefix="/experiencia", tags=["experiencia"])

Clase = Literal["error", "acierto"]
Fuente = Literal["claude-code", "claude-app", "remi", "bitacora", "manual"]

SECCIONES_ERROR = ("Síntoma", "Lo que creímos", "Causa real", "Cura", "Cómo verlo antes")
SECCIONES_ACIERTO = ("Qué funcionó", "Evidencia", "Cuándo usarlo")
CLASES = ("error", "acierto")
FUENTES = ("claude-code", "claude-app", "remi", "bitacora", "manual")


def carpeta() -> Path:
    """`remi-mente/experiencia/` — al lado de proyectos/, áreas/, oficios/
    y episodios/, no adentro de ninguna."""
    return episodios.carpeta_episodios().parent / "experiencia"


@dataclass(frozen=True)
class Leccion:
    titulo: str
    tema: str
    resumen: str
    clase: Clase
    donde: str  # "<repo>/<archivo>" — de dónde salió
    secciones: dict[str, str]
    fuente: Fuente
    veces: int = 1
    ultima_vez: date | None = None
    vueltas: bool = False


def secciones_de(clase: Clase) -> tuple[str, ...]:
    return SECCIONES_ERROR if clase == "error" else SECCIONES_ACIERTO


def validar(leccion: Leccion) -> list[str]:
    """Pura: la lista de lo que falta, [] si está completa. Nunca escribe
    — eso es `escribir()`, solo si esto viene vacío. Lo que no cumpla no
    entra (T8, punto 1)."""
    errores: list[str] = []
    if not leccion.titulo.strip():
        errores.append("falta el título")
    if leccion.clase not in CLASES:
        errores.append(f"clase debe ser error o acierto, no «{leccion.clase}»")
        return errores  # sin clase válida no hay con qué comparar secciones
    if not leccion.tema.strip():
        errores.append("falta el tema")
    if not leccion.resumen.strip():
        errores.append("falta el resumen")
    if not leccion.donde.strip():
        errores.append("falta dónde pasó (repo y archivo)")
    if leccion.fuente not in FUENTES:
        errores.append(f"fuente debe ser una de {FUENTES}, no «{leccion.fuente}»")
    esperadas = secciones_de(leccion.clase)
    for nombre in esperadas:
        if nombre == "Lo que creímos":
            continue  # puede ir vacía: no toda sesión tuvo una pista falsa
        if not leccion.secciones.get(nombre, "").strip():
            errores.append(f"falta la sección «{nombre}»")
    extra = set(leccion.secciones) - set(esperadas)
    if extra:
        errores.append(f"esas secciones no son de un «{leccion.clase}»: {', '.join(sorted(extra))}")
    if leccion.clase == "error" and leccion.vueltas and not leccion.secciones.get("Lo que creímos", "").strip():
        errores.append("vueltas: true exige «Lo que creímos» (la pista falsa que se siguió)")
    return errores


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes).strip()


def _sintoma_de(secciones: dict[str, str], clase: Clase) -> str:
    clave = "Síntoma" if clase == "error" else "Qué funcionó"
    return _normalizar(secciones.get(clave, ""))


def slug(texto: str) -> str:
    return episodios.slug(texto)


@dataclass(frozen=True)
class LeccionGuardada:
    ruta: Path
    titulo: str
    tema: str
    resumen: str
    clase: str
    donde: str
    veces: int
    ultima_vez: str
    vueltas: bool
    fuente: str
    secciones: dict[str, str]


def _parsear(ruta: Path) -> LeccionGuardada | None:
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None
    campos = libros._frontmatter(partes[1])
    titulo, tema, resumen = campos.get("titulo"), campos.get("tema"), campos.get("resumen")
    if not all(isinstance(c, str) and c for c in (titulo, tema, resumen)):
        return None
    secciones: dict[str, str] = {}
    actual: str | None = None
    buf: list[str] = []
    for linea in partes[2].splitlines():
        if linea.startswith("## "):
            if actual is not None:
                secciones[actual] = "\n".join(buf).strip()
            actual = linea[3:].strip()
            buf = []
        elif actual is not None:
            buf.append(linea)
    if actual is not None:
        secciones[actual] = "\n".join(buf).strip()
    assert isinstance(titulo, str) and isinstance(tema, str) and isinstance(resumen, str)
    return LeccionGuardada(
        ruta=ruta,
        titulo=titulo,
        tema=tema,
        resumen=resumen,
        clase=str(campos.get("clase") or ""),
        donde=str(campos.get("donde") or ""),
        veces=int(str(campos.get("veces") or 1)),
        ultima_vez=str(campos.get("ultima_vez") or ""),
        vueltas=str(campos.get("vueltas") or "").strip().lower() == "true",
        fuente=str(campos.get("fuente") or ""),
        secciones=secciones,
    )


def listar(tema: str | None = None) -> list[LeccionGuardada]:
    carp = carpeta()
    if not carp.is_dir():
        return []
    resultado = []
    for ruta in sorted(carp.glob("*.md")):
        leida = _parsear(ruta)
        if leida is None:
            continue
        if tema is not None and leida.tema != tema:
            continue
        resultado.append(leida)
    return resultado


def _existente(leccion: Leccion) -> LeccionGuardada | None:
    """Ya hay una lección del mismo libro con el mismo síntoma/acierto
    (texto normalizado) — nunca se crea otra (T8, punto 3)."""
    objetivo = _sintoma_de(leccion.secciones, leccion.clase)
    if not objetivo:
        return None
    for existente in listar(tema=leccion.tema):
        if existente.clase != leccion.clase:
            continue
        if _sintoma_de(existente.secciones, leccion.clase) == objetivo:
            return existente
    return None


def _cuerpo_de(leccion: Leccion) -> str:
    return "".join(f"## {nombre}\n\n{leccion.secciones.get(nombre, '')}\n\n" for nombre in secciones_de(leccion.clase))


def _frontmatter_de(leccion: Leccion, veces: int, ultima_vez: date) -> str:
    lineas = [
        "---",
        f'titulo: "{episodios._una_linea(leccion.titulo)}"',
        f"tema: {leccion.tema}",
        f'resumen: "{episodios._una_linea(leccion.resumen)}"',
        "tipo: leccion",
        f"clase: {leccion.clase}",
        f"donde: {leccion.donde}",
        f"veces: {veces}",
        f"ultima_vez: {ultima_vez.isoformat()}",
        f"vueltas: {'true' if leccion.vueltas else 'false'}",
        f"fuente: {leccion.fuente}",
        "---",
        "",
    ]
    return "\n".join(lineas)


def escribir(leccion: Leccion, ahora: datetime | None = None) -> tuple[Path, bool]:
    """Guarda la lección, con su commit en la bóveda. (ruta, es_nueva) —
    si ya había una igual, le suma `veces` y una línea «volvió a pasar»,
    nunca crea otra. Lanza ValueError con la lista de `validar()` si no
    está completa: no entra nada a medio hacer."""
    errores = validar(leccion)
    if errores:
        raise ValueError("; ".join(errores))
    ahora = ahora or datetime.now(timezone.utc)
    hoy = ahora.date()

    anterior = _existente(leccion)
    if anterior is not None:
        texto = anterior.ruta.read_text()
        nuevas_veces = anterior.veces + 1
        texto = re.sub(r"(?m)^veces:\s*\d+\s*$", f"veces: {nuevas_veces}", texto)
        texto = re.sub(r"(?m)^ultima_vez:.*$", f"ultima_vez: {hoy.isoformat()}", texto)
        if not texto.endswith("\n"):
            texto += "\n"
        texto += f"- volvió a pasar el {hoy.isoformat()}.\n"
        boveda_git.snapshot_antes(f"sumar una vuelta a la lección {anterior.ruta.name}")
        anterior.ruta.write_text(texto)
        boveda_git.snapshot_despues(f"experiencia: {anterior.ruta.name} veces={nuevas_veces}")
        if nuevas_veces == 2:
            _proponer_regla(anterior, ahora)
        return anterior.ruta, False

    carp = carpeta()
    carp.mkdir(parents=True, exist_ok=True)
    sintoma = _sintoma_de(leccion.secciones, leccion.clase) or slug(leccion.titulo)
    base = f"{hoy.isoformat()}-{slug(leccion.tema)}-{slug(sintoma)}"
    destino = episodios._ruta_libre(carp, base)
    boveda_git.snapshot_antes(f"escribir la lección {destino.name}")
    destino.write_text(_frontmatter_de(leccion, 1, hoy) + "\n" + _cuerpo_de(leccion))
    boveda_git.snapshot_despues(f"experiencia: {destino.name} ({leccion.clase}, {leccion.tema})")
    return destino, True


# — Detección sin IA de «vueltas» (T8, punto 2) —

UMBRAL_ROJOS_SEGUIDOS = 3
UMBRAL_EDICIONES_SIN_COMMIT = 5
UMBRAL_MINUTOS = 40


def hay_vueltas(
    *, rojos_seguidos: int = 0, ediciones_sin_commit: int = 0, minutos_hasta_el_verde: int = 0
) -> bool:
    """Cualquiera de las tres señales de la sesión real (T8.2): la misma
    prueba en rojo 3+ veces, el mismo archivo editado 5+ veces sin commit,
    o más de 40 min entre el primer rojo y el verde."""
    return (
        rojos_seguidos >= UMBRAL_ROJOS_SEGUIDOS
        or ediciones_sin_commit >= UMBRAL_EDICIONES_SIN_COMMIT
        or minutos_hasta_el_verde > UMBRAL_MINUTOS
    )


_PATRON_COMMIT_ARREGLO = re.compile(r"^(fix|arregl|corrig)", re.IGNORECASE)


def commit_es_arreglo(mensaje: str) -> bool:
    return bool(_PATRON_COMMIT_ARREGLO.match(mensaje.strip()))


# — Resultado de una sesión, sin IA (T8, punto 4) —

Resultado = Literal["limpio", "con-arreglo", "sin-commit"]


def resultado_de_sesion(
    *, hubo_commits: bool, pruebas: Literal["verde", "rojo", "sin-correr"], fix_en_48h: bool
) -> Resultado:
    """limpio: commits y pruebas verdes, y nada lo tocó después. con-arreglo:
    un commit fix/revert a las 48 h tocó los mismos archivos, o las pruebas
    quedaron en rojo. sin-commit: la sesión no dejó ningún commit."""
    if not hubo_commits:
        return "sin-commit"
    if pruebas == "rojo" or fix_en_48h:
        return "con-arreglo"
    return "limpio"


def revisar_resultados_pendientes(ahora: datetime | None = None) -> int:
    """T8.4, a las 48 h: un episodio con `resultado: sin-commit` o
    `limpio` pasa a `con-arreglo` si, para el mismo tema, llegó un commit
    fix/arregl/corrig o revert dentro de esas 48 h. Simplificación
    documentada: mira el tema, no si tocó los mismos archivos — un commit
    de arreglo de otra parte del mismo libro también cuenta como señal de
    que algo no quedó limpio. Marca cada episodio con `revisado_48h: true`
    para no volver a mirarlo cada noche. Devuelve cuántos tocó."""
    ahora = ahora or datetime.now(timezone.utc)
    carpeta_ep = episodios.carpeta_episodios()
    if not carpeta_ep.is_dir():
        return 0
    tocados = 0
    for ruta in sorted(carpeta_ep.glob("*.md")):
        texto = ruta.read_text()
        if not texto.startswith("---") or "revisado_48h: true" in texto:
            continue
        partes = texto.split("---", 2)
        if len(partes) < 3:
            continue
        campos = libros._frontmatter(partes[1])
        tema = campos.get("tema")
        resultado = str(campos.get("resultado") or "")
        if not isinstance(tema, str) or not tema or resultado not in ("sin-commit", "limpio"):
            continue
        try:
            fecha_ep = datetime.strptime(ruta.name[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ahora - fecha_ep < timedelta(hours=48):
            continue  # todavía no pasaron las 48 h

        conexion = db.conectar()
        try:
            filas = conexion.execute(
                "SELECT mensaje FROM trabajo_commits WHERE tema = ? AND fecha > ? AND fecha <= ?",
                (tema, fecha_ep.isoformat(), (fecha_ep + timedelta(hours=48)).isoformat()),
            ).fetchall()
        finally:
            conexion.close()
        hubo_arreglo = any(
            commit_es_arreglo(fila["mensaje"]) or "revert" in fila["mensaje"].lower() for fila in filas
        )
        nuevo_resultado = "con-arreglo" if hubo_arreglo else resultado
        nuevo_frontmatter = re.sub(
            r"(?m)^resultado:.*$", f"resultado: {nuevo_resultado}\nrevisado_48h: true", partes[1], count=1
        )
        boveda_git.snapshot_antes(f"revisar a las 48h el episodio {ruta.name}")
        ruta.write_text("---".join([partes[0], nuevo_frontmatter, partes[2]]))
        boveda_git.snapshot_despues(f"experiencia: {ruta.name} resultado={nuevo_resultado} (revisión 48h)")
        tocados += 1
    return tocados


# — T9.1: de lección a regla —

ESQUEMA_PROPUESTA_REGLA = """
CREATE TABLE IF NOT EXISTS propuesta_regla (
    campo TEXT PRIMARY KEY,
    oficio TEXT NOT NULL,
    regla TEXT NOT NULL
);
"""


def _preparar_propuesta_regla(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA_PROPUESTA_REGLA)


def guardar_propuesta_regla(conexion: sqlite3.Connection, campo: str, oficio: str, regla: str) -> None:
    _preparar_propuesta_regla(conexion)
    conexion.execute(
        "INSERT INTO propuesta_regla (campo, oficio, regla) VALUES (?, ?, ?) "
        "ON CONFLICT(campo) DO UPDATE SET oficio = excluded.oficio, regla = excluded.regla",
        (campo, oficio, regla),
    )
    conexion.commit()


def leer_propuesta_regla(conexion: sqlite3.Connection, campo: str) -> tuple[str, str] | None:
    _preparar_propuesta_regla(conexion)
    fila = conexion.execute(
        "SELECT oficio, regla FROM propuesta_regla WHERE campo = ?", (campo,)
    ).fetchone()
    return (fila["oficio"], fila["regla"]) if fila else None


def _proponer_regla(leccion: LeccionGuardada, ahora: datetime) -> None:
    """Cuando una lección llega a `veces: 2`: Remi propone una regla de
    una línea para el oficio que toca — nunca la escribe sola (T9.1). La
    pregunta vive en el sistema de T3 (Forma F); la respuesta la aplica
    `preguntas.responder()`."""
    import correcciones
    from modelos import Pregunta

    clave = "Cómo verlo antes" if leccion.clase == "error" else "Cuándo usarlo"
    regla = leccion.secciones.get(clave, "").strip() or leccion.resumen
    oficio = correcciones.oficio_destino(regla)
    campo = f"regla.{slug(leccion.titulo)}"

    conexion = db.conectar()
    try:
        if db.pregunta_de_tema_campo(conexion, leccion.tema, campo) is not None:
            return  # ya se propuso (o ya se respondió) esta misma regla
        guardar_propuesta_regla(conexion, campo, oficio, regla)
        db.crear_pregunta(
            conexion,
            Pregunta(
                id=uuid4(),
                tema=leccion.tema,
                campo=campo,
                voz=f"Esto ya pasó dos veces. ¿Lo dejo como regla en el oficio {oficio}?",
                estado="pendiente",
                creada_en=ahora,
                disponible_desde=ahora,
            ),
        )
    finally:
        conexion.close()


# — Búsqueda híbrida (T8.6): FTS5 (texto exacto) + los vectores que ya hay —

ESQUEMA_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS experiencia_fts USING fts5(
    ruta UNINDEXED, tipo UNINDEXED, tema UNINDEXED, titulo, resumen, cuerpo
);
"""


def _preparar_fts(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA_FTS)


def _tema_de(ruta: Path) -> str | None:
    try:
        texto = ruta.read_text()
    except OSError:
        return None
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None
    tema = libros._frontmatter(partes[1]).get("tema")
    return tema if isinstance(tema, str) and tema else None


def reindexar(conexion: sqlite3.Connection | None = None) -> int:
    """Reconstruye TODO el índice (FTS5 y vectores) desde la bóveda — nunca
    incremental a propósito: `--reindexar` siempre puede dejarlo igual que
    si se hiciera de cero. El nombre del modelo de embeddings ya entra en
    el hash de `vectores.py`: cambiar de modelo recalcula solo eso."""
    propia = conexion is None
    conexion = conexion or db.conectar()
    try:
        _preparar_fts(conexion)
        conexion.execute("DELETE FROM experiencia_fts")
        for nota in vectores.notas():
            cuerpo = nota.ruta.read_text() if nota.ruta.exists() else ""
            conexion.execute(
                "INSERT INTO experiencia_fts (ruta, tipo, tema, titulo, resumen, cuerpo) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(nota.ruta), nota.tipo, _tema_de(nota.ruta), nota.titulo, nota.texto, cuerpo),
            )
        conexion.commit()
        return vectores.actualizar_todos(conexion)
    finally:
        if propia:
            conexion.close()


@dataclass(frozen=True)
class ResultadoBusqueda:
    ruta: str
    tipo: str
    titulo: str


def _fts_buscar(conexion: sqlite3.Connection, q: str, tema: str | None, k: int) -> list[str]:
    _preparar_fts(conexion)
    condiciones = ["experiencia_fts MATCH ?"]
    parametros: list[str] = [q]
    if tema is not None:
        condiciones.append("tema = ?")
        parametros.append(tema)
    try:
        filas = conexion.execute(
            f"SELECT ruta FROM experiencia_fts WHERE {' AND '.join(condiciones)} "
            f"ORDER BY bm25(experiencia_fts) LIMIT ?",
            (*parametros, k),
        ).fetchall()
    except sqlite3.OperationalError:
        return []  # una consulta FTS5 mal formada (comillas sueltas, etc.) no rompe la búsqueda
    return [fila["ruta"] for fila in filas]


def _vectores_buscar(conexion: sqlite3.Connection, q: str, tema: str | None, k: int) -> list[str]:
    titulos = vectores.asociar(conexion, q, k=k)
    rutas = []
    for nota in vectores.notas():
        if nota.titulo in titulos and (tema is None or _tema_de(nota.ruta) == tema):
            rutas.append(str(nota.ruta))
    return rutas


def buscar(conexion: sqlite3.Connection, q: str, tema: str | None = None, k: int = 10) -> list[ResultadoBusqueda]:
    """Reciprocal rank fusion de las dos listas, sin pesos que afinar: la
    posición en cada lista pesa 1/(60+rango), y se suman."""
    por_fts = _fts_buscar(conexion, q, tema, k)
    por_vector = _vectores_buscar(conexion, q, tema, k)
    puntaje: dict[str, float] = {}
    for lista in (por_fts, por_vector):
        for rango, ruta in enumerate(lista, start=1):
            puntaje[ruta] = puntaje.get(ruta, 0.0) + 1.0 / (60 + rango)
    por_ruta = {str(nota.ruta): nota for nota in vectores.notas()}
    ordenadas = sorted(puntaje, key=lambda r: puntaje[r], reverse=True)[:k]
    resultado: list[ResultadoBusqueda] = []
    for ruta in ordenadas:
        nota = por_ruta.get(ruta)
        if nota is not None:
            resultado.append(ResultadoBusqueda(ruta=ruta, tipo=nota.tipo, titulo=nota.titulo))
    return resultado


# — T8.5: la puerta para cualquier mano —


class LeccionNueva(BaseModel):
    titulo: str
    tema: str
    resumen: str
    clase: Clase
    donde: str
    secciones: dict[str, str]
    fuente: Fuente = "manual"
    vueltas: bool = False


class LeccionEscrita(BaseModel):
    archivo: str
    es_nueva: bool


class ResultadoVisible(BaseModel):
    ruta: str
    tipo: str
    titulo: str


@router.post("", response_model=LeccionEscrita, status_code=201)
def crear_leccion(cuerpo: LeccionNueva) -> LeccionEscrita:
    """POST /experiencia (T8.5): la puerta para cualquier mano — Claude
    Code, Claude en la app, Remi o a mano. 422 si no está completa."""
    leccion = Leccion(
        titulo=cuerpo.titulo,
        tema=cuerpo.tema,
        resumen=cuerpo.resumen,
        clase=cuerpo.clase,
        donde=cuerpo.donde,
        secciones=cuerpo.secciones,
        fuente=cuerpo.fuente,
        vueltas=cuerpo.vueltas,
    )
    try:
        destino, es_nueva = escribir(leccion)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return LeccionEscrita(archivo=destino.name, es_nueva=es_nueva)


@router.get("", response_model=list[ResultadoVisible])
def buscar_experiencia(tema: str | None = None, q: str | None = None) -> list[ResultadoVisible]:
    """GET /experiencia?tema=&q= (T8.6). Sin `q`, lista las lecciones del
    tema (o todas); con `q`, búsqueda híbrida."""
    conexion = db.conectar()
    try:
        if q:
            encontrados = buscar(conexion, q, tema)
            return [ResultadoVisible(ruta=r.ruta, tipo=r.tipo, titulo=r.titulo) for r in encontrados]
        return [
            ResultadoVisible(ruta=str(leccion.ruta), tipo="leccion", titulo=leccion.titulo)
            for leccion in listar(tema)
        ]
    finally:
        conexion.close()


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--reindexar", action="store_true", help="reconstruye FTS5 y vectores desde la bóveda")
    argumentos = analizador.parse_args()
    if argumentos.reindexar:
        recalculadas = reindexar()
        print(f"experiencia: reindexado, {recalculadas} vector(es) recalculado(s)")
        return 0
    analizador.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""B2: «Al día» — Remi sabe en qué vas, sin que lo marques (PLAN-FINAL.md,
forma J). Función pura sobre eventos que otras piezas ya guardan solas:
commits y corridas de pruebas (trabajo.py, el gancho de git), sesiones de
Claude Code (trabajo_claude), cobros (entregas.py) y decisiones guardadas
por el MCP de memoria (`tipo: "decision"`). aldia.py no escribe nada de
eso — solo `marcar_visto` lleva el reloj de «desde cuándo contar»."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import caminos
import db
import entregas
import libros

VENTANA_ESTAMOS_EN = timedelta(hours=3)
VENTANA_MINIMA_MIENTRAS_NO_ESTABAS = timedelta(hours=2)
MAXIMO_MIENTRAS_NO_ESTABAS = 5

# B2.3: los hitos del SOP que cierran avisando a un cliente — el paso_remi
# que caminos.py ya les asigna es «Recuerda fechas y promesas; avisa el día
# antes.» (Pago antes de arrancar, Cobro y cierre, Mensualidad). Un hito
# con ese paso_remi es el único caso en que `sigue` trae `borrador`.
_PASO_REMI_DE_AVISO = "Recuerda fechas y promesas; avisa el día antes."


@dataclass(frozen=True)
class Evidencia:
    tipo: str  # "commit" | "pruebas" | "sesion" | "mensaje" | "cobro" | "decision"
    ref: str


@dataclass(frozen=True)
class _Evento:
    texto: str
    tema: str | None
    fecha: datetime
    evidencia: Evidencia


@dataclass(frozen=True)
class EstamosEn:
    tema: str
    fase_n: int
    paso: str


@dataclass(frozen=True)
class LoUltimo:
    texto: str
    hace_min: int
    evidencia: Evidencia


@dataclass(frozen=True)
class Sigue:
    texto: str
    borrador: str | None


@dataclass(frozen=True)
class MientrasNoEstabas:
    texto: str
    tema: str | None
    hora: datetime
    evidencia: Evidencia


@dataclass(frozen=True)
class AlDia:
    estamos_en: EstamosEn | None
    lo_ultimo: LoUltimo | None
    sigue: Sigue | None
    mientras_no_estabas: list[MientrasNoEstabas]


def _texto_commit(datos: dict[str, object]) -> str:
    mensaje = str(datos.get("mensaje") or "").strip().splitlines()[0] if datos.get("mensaje") else ""
    return f"Diste un commit: {mensaje[:60]}" if mensaje else "Diste un commit."


def _texto_pruebas(datos: dict[str, object]) -> str:
    if datos.get("verde") is False:
        return "Las pruebas quedaron rotas."
    return "Las pruebas quedaron en verde."


def _eventos_de_trabajo(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> list[_Evento]:
    filas = conexion.execute(
        "SELECT id, tipo, tema, datos, fecha FROM trabajo_eventos "
        "WHERE fecha >= ? AND fecha <= ? AND tipo IN ('commit', 'pruebas', 'sesion_fin') "
        "ORDER BY fecha",
        (desde.isoformat(), hasta.isoformat()),
    ).fetchall()
    eventos: list[_Evento] = []
    for fila in filas:
        try:
            datos = json.loads(fila["datos"])
        except json.JSONDecodeError:
            datos = {}
        fecha = datetime.fromisoformat(fila["fecha"])
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        if fila["tipo"] == "commit":
            texto, ev_tipo = _texto_commit(datos), "commit"
        elif fila["tipo"] == "pruebas":
            texto, ev_tipo = _texto_pruebas(datos), "pruebas"
        else:
            texto, ev_tipo = "Cerraste una sesión de Claude Code.", "sesion"
        eventos.append(_Evento(texto=texto, tema=fila["tema"], fecha=fecha, evidencia=Evidencia(ev_tipo, str(fila["id"]))))
    return eventos


def _eventos_de_cobros(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> list[_Evento]:
    temas_por_proyecto = {entregas._proyecto_id_de_tema(libro.tema): libro.tema for libro in libros.listar()}
    filas = conexion.execute(
        "SELECT id, cliente, proyecto_id, fecha, monto FROM entregas "
        "WHERE estado = 'pagada' AND fecha >= ? AND fecha <= ? ORDER BY fecha",
        (desde.isoformat(), hasta.isoformat()),
    ).fetchall()
    eventos: list[_Evento] = []
    for fila in filas:
        fecha = datetime.fromisoformat(fila["fecha"])
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        from uuid import UUID

        tema = temas_por_proyecto.get(UUID(fila["proyecto_id"]))
        monto = f" ({fila['monto']:.0f})" if fila["monto"] else ""
        eventos.append(
            _Evento(
                texto=f"Cobraste a {fila['cliente']}{monto}.",
                tema=tema,
                fecha=fecha,
                evidencia=Evidencia("cobro", str(fila["id"])),
            )
        )
    return eventos


def _eventos_de_decisiones(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> list[_Evento]:
    eventos: list[_Evento] = []
    for memoria in db.decisiones_desde(conexion, desde):
        fecha = memoria.fecha if memoria.fecha.tzinfo else memoria.fecha.replace(tzinfo=timezone.utc)
        if fecha > hasta:
            continue
        eventos.append(
            _Evento(
                texto=f"Decidiste: {memoria.resumen}",
                tema=memoria.tema,
                fecha=fecha,
                evidencia=Evidencia("decision", str(memoria.id)),
            )
        )
    return eventos


def eventos_entre(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> list[_Evento]:
    """Todos los eventos (commit, pruebas, sesión, cobro, decisión) en la
    ventana, del más viejo al más nuevo."""
    eventos = (
        _eventos_de_trabajo(conexion, desde, hasta)
        + _eventos_de_cobros(conexion, desde, hasta)
        + _eventos_de_decisiones(conexion, desde, hasta)
    )
    return sorted(eventos, key=lambda e: e.fecha)


def _tema_mas_activo(eventos: list[_Evento], ahora: datetime) -> str | None:
    recientes = [e for e in eventos if e.tema and ahora - e.fecha <= VENTANA_ESTAMOS_EN]
    if not recientes:
        return None
    return max(recientes, key=lambda e: e.fecha).tema


def calcular_estamos_en(conexion: sqlite3.Connection, eventos: list[_Evento], ahora: datetime) -> EstamosEn | None:
    tema = _tema_mas_activo(eventos, ahora)
    if tema is None:
        return None
    resultado = caminos.hitos_de_tema(conexion, tema)
    if resultado is None:
        return None
    hitos, siguiente = resultado
    if siguiente is None:
        return None
    fase_n = next((i for i, h in enumerate(hitos, start=1) if h.texto == siguiente.texto), len(hitos))
    return EstamosEn(tema=tema, fase_n=fase_n, paso=siguiente.texto)


def calcular_lo_ultimo(eventos: list[_Evento], ahora: datetime) -> LoUltimo | None:
    if not eventos:
        return None
    ultimo = eventos[-1]
    hace_min = max(0, int((ahora - ultimo.fecha).total_seconds() // 60))
    return LoUltimo(texto=ultimo.texto, hace_min=hace_min, evidencia=ultimo.evidencia)


def _libro_de_tema(tema: str) -> libros.Libro | None:
    return next((l for l in libros.listar() if l.tema == tema), None)


def sesion_abierta(conexion: sqlite3.Connection) -> tuple[str, datetime, str] | None:
    """B2.2: «terminal trabajando» — una sesión de Claude Code todavía
    abierta (sin `fin`) sobre un libro. (tema, inicio, session_id), la más
    reciente si hay varias. None si no hay ninguna sobre un libro."""
    fila = conexion.execute(
        "SELECT tema, inicio, session_id FROM trabajo_claude WHERE fin IS NULL AND tema IS NOT NULL "
        "ORDER BY inicio DESC LIMIT 1"
    ).fetchone()
    if fila is None:
        return None
    inicio = datetime.fromisoformat(fila["inicio"])
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return fila["tema"], inicio, fila["session_id"]


def avisa_hito(tipo_libro: str | None, texto_hito: str) -> bool:
    """B2.3: este hito del SOP cierra avisando a un cliente — los únicos
    dos con `paso_remi` «Recuerda fechas y promesas; avisa el día antes.»
    (Pago antes de arrancar, Cobro y cierre)."""
    return caminos.paso_remi_de(tipo_libro, texto_hito) == _PASO_REMI_DE_AVISO


def calcular_sigue(conexion: sqlite3.Connection, estamos_en: EstamosEn | None) -> Sigue | None:
    if estamos_en is None:
        return None
    libro = _libro_de_tema(estamos_en.tema)
    borrador = None
    if avisa_hito(libro.tipo if libro else None, estamos_en.paso):
        fila = conexion.execute(
            "SELECT texto FROM aldia_borrador WHERE tema = ? AND hito = ?", (estamos_en.tema, estamos_en.paso)
        ).fetchone()
        borrador = fila["texto"] if fila else None
    return Sigue(texto=estamos_en.paso, borrador=borrador)


def guardar_borrador(conexion: sqlite3.Connection, tema: str, hito: str, texto: str) -> None:
    conexion.execute(
        "INSERT INTO aldia_borrador (tema, hito, texto) VALUES (?, ?, ?) "
        "ON CONFLICT(tema, hito) DO UPDATE SET texto = excluded.texto",
        (tema, hito, texto),
    )
    conexion.commit()


def calcular_mientras_no_estabas(
    eventos: list[_Evento], desde_ultima_apertura: datetime, ahora: datetime
) -> list[MientrasNoEstabas]:
    """Vacío si la última apertura fue hace menos de 2 h (Ley 04: no hay
    nada que anunciar de algo tan reciente)."""
    if ahora - desde_ultima_apertura < VENTANA_MINIMA_MIENTRAS_NO_ESTABAS:
        return []
    recientes = [e for e in eventos if e.fecha >= desde_ultima_apertura]
    return [
        MientrasNoEstabas(texto=e.texto, tema=e.tema, hora=e.fecha, evidencia=e.evidencia)
        for e in recientes[-MAXIMO_MIENTRAS_NO_ESTABAS:]
    ]


MINUTOS_MISMA_APERTURA = 10


def marcar_visto(conexion: sqlite3.Connection, ahora: datetime, clave: str = "panel") -> datetime:
    """Devuelve CUÁNDO fue la apertura anterior (o `ahora`, la primera vez).

    GET /hoy/aldia puede pedirse muchas veces durante la misma visita (el
    panel sondeando mientras está abierto); si cada pedido adelantara el
    reloj, «mientras no estabas» nunca llegaría a acumular las 2 h porque
    cada GET lo reinicia. Dentro de los `MINUTOS_MISMA_APERTURA` desde el
    último toque, es la misma visita: ni se lee de nuevo el reloj viejo ni
    se mueve — se sigue devolviendo lo que ya se devolvió. Solo después de
    ese hueco se mueve, con el mismo patrón que trabajo._tomar_turno."""
    fila = conexion.execute("SELECT fecha, visto_desde FROM aldia_visto WHERE clave = ?", (clave,)).fetchone()
    if fila is None:
        conexion.execute(
            "INSERT INTO aldia_visto (clave, fecha, visto_desde) VALUES (?, ?, ?)",
            (clave, ahora.isoformat(), ahora.isoformat()),
        )
        conexion.commit()
        return ahora

    ultimo_toque = datetime.fromisoformat(fila["fecha"])
    if ultimo_toque.tzinfo is None:
        ultimo_toque = ultimo_toque.replace(tzinfo=timezone.utc)
    visto_desde = datetime.fromisoformat(fila["visto_desde"])
    if visto_desde.tzinfo is None:
        visto_desde = visto_desde.replace(tzinfo=timezone.utc)

    if ahora - ultimo_toque < timedelta(minutes=MINUTOS_MISMA_APERTURA):
        # Misma visita: no se mueve nada, pero sí se anota el toque más
        # reciente, para que una visita larga no se corte sola a los 10 min.
        conexion.execute("UPDATE aldia_visto SET fecha = ? WHERE clave = ?", (ahora.isoformat(), clave))
        conexion.commit()
        return visto_desde

    conexion.execute(
        "UPDATE aldia_visto SET fecha = ?, visto_desde = ? WHERE clave = ?",
        (ahora.isoformat(), ahora.isoformat(), clave),
    )
    conexion.commit()
    return visto_desde


def calcular(conexion: sqlite3.Connection, ahora: datetime, desde_ultima_apertura: datetime) -> AlDia:
    """La forma J entera. `desde_ultima_apertura` es lo que devuelve
    `marcar_visto` — quien llama decide cuándo tocar ese reloj."""
    eventos = eventos_entre(conexion, min(desde_ultima_apertura, ahora - VENTANA_ESTAMOS_EN), ahora)
    estamos_en = calcular_estamos_en(conexion, eventos, ahora)
    lo_ultimo = calcular_lo_ultimo(eventos, ahora)

    # B2.2: una sesión de Claude Code todavía abierta es lo que está
    # pasando AHORA — pero solo gana si no hay ya un evento cerrado más
    # nuevo que su inicio (un commit con pruebas en verde DURANTE la
    # sesión es más fresco que «sigo en esto desde que empezó», y es
    # justo lo que pide el «listo cuando» de B2).
    abierta = sesion_abierta(conexion)
    hay_evento_mas_nuevo = bool(eventos) and eventos[-1].fecha > (abierta[1] if abierta else ahora)
    if abierta is not None and not hay_evento_mas_nuevo:
        tema_abierto, inicio, session_id = abierta
        minutos = max(0, int((ahora - inicio).total_seconds() // 60))
        lo_ultimo = LoUltimo(
            texto=f"La terminal está en esto desde hace {minutos} min.",
            hace_min=minutos,
            evidencia=Evidencia("sesion", session_id),
        )
        resultado = caminos.hitos_de_tema(conexion, tema_abierto)
        if resultado is not None:
            hitos, siguiente = resultado
            if siguiente is not None:
                fase_n = next((i for i, h in enumerate(hitos, start=1) if h.texto == siguiente.texto), len(hitos))
                estamos_en = EstamosEn(tema=tema_abierto, fase_n=fase_n, paso=siguiente.texto)

    return AlDia(
        estamos_en=estamos_en,
        lo_ultimo=lo_ultimo,
        sigue=calcular_sigue(conexion, estamos_en),
        mientras_no_estabas=calcular_mientras_no_estabas(eventos, desde_ultima_apertura, ahora),
    )

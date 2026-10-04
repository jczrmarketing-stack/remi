"""B6: los números derivados de la ficha de cliente — gastado (agrupado),
tiempo total y por_hora. Sin IA, puro sobre lo que ya hay en la base.

Los comunes (membresías, herramientas) se reparten entre proyectos por
minutos trabajados ESTE MES — un proyecto que no se tocó este mes no
carga nada de los comunes."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import aldia
import caminos
import db
import entregas
import libros
import trabajo

BOGOTA = ZoneInfo("America/Bogota")


@dataclass(frozen=True)
class GastoAgrupado:
    concepto: str
    monto: float
    # B6.5: el id de la fila de gasto_proyecto, SOLO si una única fila
    # (propia, no un común repartido) forma este grupo — "corregir un
    # número a mano" edita esa fila. None si el concepto junta más de una
    # fila, o si es la parte de los comunes (no es una fila propia).
    id: str | None = None


def _inicio_de_mes(ahora: datetime) -> datetime:
    local = ahora.astimezone(BOGOTA)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def gastos_comunes_mes(conexion: sqlite3.Connection, ahora: datetime) -> float:
    return sum(g.monto for g in db.gastos_comunes_desde(conexion, _inicio_de_mes(ahora)))


def _minutos_mes_por_tema(conexion: sqlite3.Connection, temas: list[str], ahora: datetime) -> dict[str, int]:
    return {tema: trabajo.minutos_esta_mes(tema, ahora) for tema in temas}


def _parte_de_comunes(conexion: sqlite3.Connection, tema: str, todos_los_temas: list[str], ahora: datetime) -> float:
    total_comun = gastos_comunes_mes(conexion, ahora)
    if total_comun <= 0:
        return 0.0
    por_tema = _minutos_mes_por_tema(conexion, todos_los_temas, ahora)
    total_minutos = sum(por_tema.values())
    if total_minutos <= 0:
        return 0.0
    return total_comun * (por_tema.get(tema, 0) / total_minutos)


def gastado_de(
    conexion: sqlite3.Connection, tema: str, todos_los_temas: list[str], ahora: datetime
) -> tuple[float, list[GastoAgrupado]]:
    """`gastado` (total) y `gastos` (agrupados por concepto) — forma M."""
    montos: dict[str, float] = {}
    ids_por_concepto: dict[str, list[str]] = {}
    for g in db.gastos_de_tema(conexion, tema):
        montos[g.concepto] = montos.get(g.concepto, 0.0) + g.monto
        ids_por_concepto.setdefault(g.concepto, []).append(g.id)
    parte_comun = _parte_de_comunes(conexion, tema, todos_los_temas, ahora)
    if parte_comun > 0:
        montos["comunes"] = montos.get("comunes", 0.0) + parte_comun
    total = sum(montos.values())
    agrupados = [
        GastoAgrupado(
            concepto=c, monto=m,
            id=ids_por_concepto[c][0] if c in ids_por_concepto and len(ids_por_concepto[c]) == 1 else None,
        )
        for c, m in montos.items()
    ]
    return total, agrupados


def por_hora(cobrado: float, gastado: float, minutos_total: int) -> float | None:
    """(cobrado − gastado) ÷ horas. None sin minutos medidos — nunca
    inventa una tarifa por una fracción de hora irrisoria."""
    if minutos_total <= 0:
        return None
    horas = minutos_total / 60
    return (cobrado - gastado) / horas


@dataclass(frozen=True)
class Ficha:
    gastado: float
    gastos: list[GastoAgrupado]
    minutos_total: int
    por_hora: float | None


def ficha_de(conexion: sqlite3.Connection, tema: str, todos_los_temas: list[str], ahora: datetime | None = None) -> Ficha:
    """Los cuatro números de la ficha (tablero 5): cobrado, gastado,
    tiempo y por_hora — más minutos_estimados, de la fase actual."""
    momento = ahora or datetime.now(timezone.utc)
    gastado, gastos = gastado_de(conexion, tema, todos_los_temas, momento)
    minutos = trabajo.minutos_totales(tema, momento)
    proyecto_id = entregas._proyecto_id_de_tema(tema)
    cobrado = entregas.total_pagado_proyecto(conexion, proyecto_id)
    return Ficha(
        gastado=round(gastado, 2),
        gastos=gastos,
        minutos_total=minutos,
        por_hora=por_hora(cobrado, gastado, minutos),
    )


@dataclass(frozen=True)
class LineaDeEvidencia:
    texto: str
    origen: str
    hace_min: int


VENTANA_LO_QUE_PASO = timedelta(days=90)
MAXIMO_LO_QUE_PASO = 6


def lo_que_paso(conexion: sqlite3.Connection, tema: str, ahora: datetime | None = None) -> list[LineaDeEvidencia]:
    """B6.3: las últimas líneas de evidencia de este libro (cobro, hito,
    decisión, demora), la más nueva primero — reutiliza los mismos
    eventos de Al día (aldia.py), filtrados a este tema."""
    momento = ahora or datetime.now(timezone.utc)
    eventos = [e for e in aldia.eventos_entre(conexion, momento - VENTANA_LO_QUE_PASO, momento) if e.tema == tema]
    recientes = eventos[-MAXIMO_LO_QUE_PASO:]
    return [
        LineaDeEvidencia(
            texto=e.texto, origen=e.evidencia.tipo,
            hace_min=max(0, int((momento - e.fecha).total_seconds() // 60)),
        )
        for e in reversed(recientes)
    ]


@dataclass(frozen=True)
class Acordado:
    decisiones: list[str]
    entregas_futuras: list[str]


def lo_acordado(conexion: sqlite3.Connection, tema: str, ahora: datetime | None = None) -> Acordado:
    """B6.3: decisiones (`memoria.tipo = "decision"`) y entregas futuras
    de este libro."""
    momento = ahora or datetime.now(timezone.utc)
    decisiones = [m.resumen for m in db.decisiones_desde(conexion, momento - timedelta(days=365)) if m.tema == tema]
    proyecto_id = entregas._proyecto_id_de_tema(tema)
    futuras = [
        e for e in entregas.listar_entregas(conexion)
        if e.proyecto_id == proyecto_id and e.estado != "pagada"
    ]
    return Acordado(
        decisiones=decisiones,
        entregas_futuras=[
            f"{e.cliente}: {e.monto:.0f} el {e.fecha.date().isoformat()}" if e.monto is not None
            else f"{e.cliente}: {e.fecha.date().isoformat()}"
            for e in futuras
        ],
    )


_ESTADOS_DE_FASE_CERRADA = frozenset({"entregada", "cobrada", "cerrada", "hecha", "pagada"})


def atento_a(libro: libros.Libro, minutos_total: int) -> list[str]:
    """B6.4: una línea por regla — sin IA, nunca inventa. Horas contra
    estimado, hitos que faltan, y el alcance nuevo (cuando ya hay una
    fase anterior cerrada, el alcance vigente es esta)."""
    lineas: list[str] = []
    n = next(
        (i for i, f in enumerate(libro.fases, start=1) if f.estado.strip().lower() not in _ESTADOS_DE_FASE_CERRADA),
        None,
    )
    fase_actual = libro.fases[n - 1] if n else None
    # `minutos_total` es del LIBRO entero (no hay minutos por fase) — solo
    # se compara contra el estimado cuando hay una sola fase, donde total
    # y "de esta fase" son lo mismo. Con más de una fase comparar inventaría
    # datos (hallazgo de revisión, B6): mezclaría tiempo de otras fases.
    if (
        fase_actual is not None
        and len(libro.fases) == 1
        and fase_actual.minutos_estimados
        and minutos_total > fase_actual.minutos_estimados
    ):
        exceso = minutos_total - fase_actual.minutos_estimados
        lineas.append(f"{exceso} min más de lo estimado en {fase_actual.nombre}.")
    abiertos = [h for h in caminos.leer_hitos(libro.archivo) if not h.hecho]
    if abiertos:
        lineas.append(f"Quedan {len(abiertos)} paso(s) del camino.")
    if n is not None and n > 1 and fase_actual is not None:
        lineas.append(f"Alcance nuevo: {fase_actual.nombre}.")
    return lineas

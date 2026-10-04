"""B6: los números derivados de la ficha de cliente — gastado (agrupado),
tiempo total y por_hora. Sin IA, puro sobre lo que ya hay en la base.

Los comunes (membresías, herramientas) se reparten entre proyectos por
minutos trabajados ESTE MES — un proyecto que no se tocó este mes no
carga nada de los comunes."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import db
import entregas
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

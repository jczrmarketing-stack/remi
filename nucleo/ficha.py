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
    agrupados: dict[str, float] = {}
    for g in db.gastos_de_tema(conexion, tema):
        agrupados[g.concepto] = agrupados.get(g.concepto, 0.0) + g.monto
    parte_comun = _parte_de_comunes(conexion, tema, todos_los_temas, ahora)
    if parte_comun > 0:
        agrupados["comunes"] = agrupados.get("comunes", 0.0) + parte_comun
    total = sum(agrupados.values())
    return total, [GastoAgrupado(concepto=c, monto=m) for c, m in agrupados.items()]


def por_hora(cobrado: float, gastado: float, minutos_total: int) -> float | None:
    """(cobrado − gastado) ÷ horas. None sin minutos medidos — nunca
    inventa una tarifa por una fracción de hora irrisoria."""
    if minutos_total <= 0:
        return None
    horas = minutos_total / 60
    return (cobrado - gastado) / horas


def ficha_de(conexion: sqlite3.Connection, tema: str, todos_los_temas: list[str], ahora: datetime | None = None) -> dict[str, object]:
    """Los cuatro números de la ficha (tablero 5): cobrado, gastado,
    tiempo y por_hora — más minutos_estimados, de la fase actual."""
    momento = ahora or datetime.now(timezone.utc)
    gastado, gastos = gastado_de(conexion, tema, todos_los_temas, momento)
    minutos_total = trabajo.minutos_totales(tema, momento)
    proyecto_id = entregas._proyecto_id_de_tema(tema)
    cobrado = entregas.total_pagado_proyecto(conexion, proyecto_id)
    return {
        "gastado": round(gastado, 2),
        "gastos": gastos,
        "minutos_total": minutos_total,
        "por_hora": por_hora(cobrado, gastado, minutos_total),
    }

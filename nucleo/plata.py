"""La plata del mes (Panel · Metas): sin regaños, solo números.

GET /plata devuelve lo cobrado de la semana y del mes contra la meta de
`config/plata.json`, y la próxima entrega con monto pendiente.

El contrato Entrega no tiene un estado `cobrada` (solo `camino|entregada|
pagada`, contratos/contratos.json) — lo que el encargo llama «cobrada» es
`pagada`: la plata que ya entró. Decisión tomada acá, sin tocar el
contrato, porque cambiarlo es de otra sesión.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

import db

router = APIRouter(prefix="/plata", tags=["plata"])

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "plata.json"
SEMANAS_POR_MES = 4.33
BOGOTA = ZoneInfo("America/Bogota")


def _config() -> dict[str, object]:
    return json.loads(RUTA_CONFIG.read_text())


class Semana(BaseModel):
    cobrado: float
    meta_semanal: float


class Mes(BaseModel):
    cobrado: float
    meta: float
    faltan: float


class EntregaProxima(BaseModel):
    cliente: str
    fecha: datetime
    monto: float


class Plata(BaseModel):
    semana: Semana
    mes: Mes
    proximo: EntregaProxima | None


def _lunes(momento: datetime) -> datetime:
    local = momento.astimezone(BOGOTA)
    cero = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return (cero - timedelta(days=cero.weekday())).astimezone(timezone.utc)


def _primero_del_mes(momento: datetime) -> datetime:
    local = momento.astimezone(BOGOTA)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _cobrado_desde(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> float:
    filas = conexion.execute(
        "SELECT monto FROM entregas WHERE estado = 'pagada' AND monto IS NOT NULL "
        "AND fecha >= ? AND fecha <= ?",
        (desde.isoformat(), hasta.isoformat()),
    ).fetchall()
    return sum(fila["monto"] for fila in filas)


def _proxima_con_dinero(conexion: sqlite3.Connection, ahora: datetime) -> EntregaProxima | None:
    fila = conexion.execute(
        "SELECT cliente, fecha, monto FROM entregas WHERE estado != 'pagada' "
        "AND monto IS NOT NULL AND fecha >= ? ORDER BY fecha LIMIT 1",
        (ahora.isoformat(),),
    ).fetchone()
    if fila is None:
        return None
    return EntregaProxima(cliente=fila["cliente"], fecha=datetime.fromisoformat(fila["fecha"]), monto=fila["monto"])


def calcular(conexion: sqlite3.Connection, ahora: datetime) -> Plata:
    """Sin entregas cobradas: 0, nunca error — el chequeo es aritmética
    sobre listas, no una consulta que pueda fallar por falta de filas."""
    config = _config()
    meta_mensual = float(config["meta_mensual"])  # type: ignore[arg-type]
    meta_semanal = meta_mensual / SEMANAS_POR_MES

    cobrado_semana = _cobrado_desde(conexion, _lunes(ahora), ahora)
    cobrado_mes = _cobrado_desde(conexion, _primero_del_mes(ahora), ahora)

    return Plata(
        semana=Semana(cobrado=cobrado_semana, meta_semanal=meta_semanal),
        mes=Mes(cobrado=cobrado_mes, meta=meta_mensual, faltan=max(0.0, meta_mensual - cobrado_mes)),
        proximo=_proxima_con_dinero(conexion, ahora),
    )


@router.get("", response_model=Plata)
def ver_plata() -> Plata:
    conexion = db.conectar()
    try:
        return calcular(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()

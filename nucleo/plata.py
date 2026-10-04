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
import ficha

router = APIRouter(prefix="/plata", tags=["plata"])

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "plata.json"
SEMANAS_POR_MES = 4.33
BOGOTA = ZoneInfo("America/Bogota")


def _config() -> dict[str, object]:
    return json.loads(RUTA_CONFIG.read_text())


class Semana(BaseModel):
    cobrado: float
    meta_semanal: float


class EntregaCobrada(BaseModel):
    cliente: str
    fecha: datetime
    monto: float


class Mes(BaseModel):
    cobrado: float
    meta: float
    faltan: float
    # Una línea por entrega pagada del mes — «ingreso por línea» (Metas).
    entregas: list[EntregaCobrada]


class EntregaProxima(BaseModel):
    cliente: str
    fecha: datetime
    monto: float


class Meta(BaseModel):
    """Una meta con nombre y horizonte (config/plata.json → `metas`). La
    primera usa siempre `meta_mensual` como su número del mes: es el que se
    cambia desde Ajustes, y no puede haber dos."""

    nombre: str
    horizonte_meses: int | None
    monto_mes: float
    # False mientras duerme: la segunda meta no existe hasta que la primera
    # pase de `activa_desde_pct` en el mes (Biblia, Parte VII).
    activa: bool
    activa_desde_pct: float | None


class RevisionFria(BaseModel):
    """Cuándo se revisa la Bandeja en frío (ley 6). Solo se muestra: no
    dispara nada por reloj."""

    dia: str
    hora: str
    minutos: int | None


class Linea(BaseModel):
    id: str
    nombre: str
    temas: list[str]


class PorLinea(BaseModel):
    id: str
    nombre: str
    cobrado_mes: float
    minutos_mes: int


class Plata(BaseModel):
    semana: Semana
    mes: Mes
    proximo: EntregaProxima | None
    metas: list[Meta]
    revision_fria: RevisionFria | None
    # Forma C (T4): una entrada por línea de la config, en ese orden,
    # aunque esté en cero.
    por_linea: list[PorLinea]
    # B6: lo gastado en común este mes (membresías, herramientas) — antes
    # de repartirse entre proyectos por minutos trabajados.
    gastos_comunes_mes: float


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


def _entregas_pagadas_desde(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> list[EntregaCobrada]:
    filas = conexion.execute(
        "SELECT cliente, fecha, monto FROM entregas WHERE estado = 'pagada' AND monto IS NOT NULL "
        "AND fecha >= ? AND fecha <= ? ORDER BY fecha",
        (desde.isoformat(), hasta.isoformat()),
    ).fetchall()
    return [
        EntregaCobrada(cliente=fila["cliente"], fecha=datetime.fromisoformat(fila["fecha"]), monto=fila["monto"])
        for fila in filas
    ]


def _proxima_con_dinero(conexion: sqlite3.Connection, ahora: datetime) -> EntregaProxima | None:
    fila = conexion.execute(
        "SELECT cliente, fecha, monto FROM entregas WHERE estado != 'pagada' "
        "AND monto IS NOT NULL AND fecha >= ? ORDER BY fecha LIMIT 1",
        (ahora.isoformat(),),
    ).fetchone()
    if fila is None:
        return None
    return EntregaProxima(cliente=fila["cliente"], fecha=datetime.fromisoformat(fila["fecha"]), monto=fila["monto"])


PCT_PARA_DESPERTAR = 50.0


def metas_de(config: dict[str, object], meta_mensual: float, cobrado_mes: float) -> list[Meta]:
    """Las metas con nombre. Sin `metas` en la config hay una sola, sin
    nombre propio: la mensual de siempre. Una entrada mal escrita se salta;
    nunca rompe /plata."""
    crudas = config.get("metas")
    porcentaje = (cobrado_mes / meta_mensual * 100) if meta_mensual > 0 else 0.0
    metas: list[Meta] = []
    if isinstance(crudas, list):
        for cruda in crudas:
            if not isinstance(cruda, dict) or not isinstance(cruda.get("nombre"), str):
                continue
            horizonte = cruda.get("horizonte_meses")
            horizonte_meses = horizonte if isinstance(horizonte, int) else None
            if not metas:
                metas.append(
                    Meta(
                        nombre=cruda["nombre"],
                        horizonte_meses=horizonte_meses,
                        monto_mes=meta_mensual,
                        activa=True,
                        activa_desde_pct=None,
                    )
                )
                continue
            monto = cruda.get("monto_mes")
            if not isinstance(monto, (int, float)) or monto <= 0:
                continue
            desde = cruda.get("activa_desde_pct")
            desde_pct = float(desde) if isinstance(desde, (int, float)) else PCT_PARA_DESPERTAR
            metas.append(
                Meta(
                    nombre=cruda["nombre"],
                    horizonte_meses=horizonte_meses,
                    monto_mes=float(monto),
                    activa=porcentaje >= desde_pct,
                    activa_desde_pct=desde_pct,
                )
            )
    if not metas:
        metas.append(
            Meta(nombre="Meta mensual", horizonte_meses=None, monto_mes=meta_mensual, activa=True, activa_desde_pct=None)
        )
    return metas


def revision_fria_de(config: dict[str, object]) -> RevisionFria | None:
    cruda = config.get("revision_fria")
    if not isinstance(cruda, dict):
        return None
    dia, hora, minutos = cruda.get("dia"), cruda.get("hora"), cruda.get("minutos")
    if not isinstance(dia, str) or not isinstance(hora, str):
        return None
    return RevisionFria(dia=dia, hora=hora, minutos=minutos if isinstance(minutos, int) else None)


def lineas() -> list[Linea]:
    """Las líneas de ingreso de config/plata.json. [] si no hay ninguna."""
    crudas = _config().get("lineas")
    resultado: list[Linea] = []
    if isinstance(crudas, list):
        for cruda in crudas:
            if not isinstance(cruda, dict):
                continue
            id_linea, nombre, temas = cruda.get("id"), cruda.get("nombre"), cruda.get("temas")
            if isinstance(id_linea, str) and isinstance(nombre, str) and isinstance(temas, list):
                resultado.append(Linea(id=id_linea, nombre=nombre, temas=[t for t in temas if isinstance(t, str)]))
    return resultado


def linea_de_tema(tema: str | None) -> str | None:
    """La línea a la que suma un libro. None si ese libro no está en
    ninguna (Remi, Omniway): no todo lo que se hace es una línea de ingreso."""
    if not tema:
        return None
    for linea in lineas():
        if tema in linea.temas:
            return linea.id
    return None


def _cobrado_mes_de_linea(conexion: sqlite3.Connection, linea_id: str, desde: datetime, hasta: datetime) -> float:
    fila = conexion.execute(
        "SELECT COALESCE(SUM(monto), 0) AS total FROM entregas WHERE estado = 'pagada' "
        "AND linea = ? AND fecha >= ? AND fecha <= ?",
        (linea_id, desde.isoformat(), hasta.isoformat()),
    ).fetchone()
    return float(fila["total"])


def _minutos_mes_de_linea(conexion: sqlite3.Connection, temas: list[str], desde: datetime, hasta: datetime) -> int:
    """Sesiones cerradas del mes cuyo `app_contexto` es un tema de la
    línea, más las de `trabajo_claude` (Claude Code) de esos mismos temas."""
    if not temas:
        return 0
    marcadores = ",".join("?" * len(temas))
    fila_sesiones = conexion.execute(
        f"SELECT COALESCE(SUM(real_min), 0) AS total FROM sesiones "
        f"WHERE fin IS NOT NULL AND app_contexto IN ({marcadores}) AND inicio >= ? AND inicio <= ?",
        (*temas, desde.isoformat(), hasta.isoformat()),
    ).fetchone()
    filas_claude = conexion.execute(
        f"SELECT inicio, fin FROM trabajo_claude "
        f"WHERE fin IS NOT NULL AND tema IN ({marcadores}) AND inicio >= ? AND inicio <= ?",
        (*temas, desde.isoformat(), hasta.isoformat()),
    ).fetchall()
    minutos_claude = sum(
        round((datetime.fromisoformat(fila["fin"]) - datetime.fromisoformat(fila["inicio"])).total_seconds() / 60)
        for fila in filas_claude
    )
    return int(fila_sesiones["total"]) + minutos_claude


def _por_linea(conexion: sqlite3.Connection, desde: datetime, hasta: datetime) -> list[PorLinea]:
    return [
        PorLinea(
            id=linea.id,
            nombre=linea.nombre,
            cobrado_mes=_cobrado_mes_de_linea(conexion, linea.id, desde, hasta),
            minutos_mes=_minutos_mes_de_linea(conexion, linea.temas, desde, hasta),
        )
        for linea in lineas()
    ]


def cobrado_mes(conexion: sqlite3.Connection, ahora: datetime) -> float:
    """R2 (forma R): lo ya cobrado este mes — el «tienes» de la cuenta
    hacia atrás, nunca un estimado."""
    return _cobrado_desde(conexion, _primero_del_mes(ahora), ahora)


def calcular(conexion: sqlite3.Connection, ahora: datetime) -> Plata:
    """Sin entregas cobradas: 0, nunca error — el chequeo es aritmética
    sobre listas, no una consulta que pueda fallar por falta de filas."""
    config = _config()
    meta_mensual = float(config["meta_mensual"])  # type: ignore[arg-type]
    meta_semanal = meta_mensual / SEMANAS_POR_MES

    cobrado_semana = _cobrado_desde(conexion, _lunes(ahora), ahora)
    primero_del_mes = _primero_del_mes(ahora)
    cobrado_mes = _cobrado_desde(conexion, primero_del_mes, ahora)

    return Plata(
        semana=Semana(cobrado=cobrado_semana, meta_semanal=meta_semanal),
        mes=Mes(
            cobrado=cobrado_mes,
            meta=meta_mensual,
            faltan=max(0.0, meta_mensual - cobrado_mes),
            entregas=_entregas_pagadas_desde(conexion, primero_del_mes, ahora),
        ),
        proximo=_proxima_con_dinero(conexion, ahora),
        metas=metas_de(config, meta_mensual, cobrado_mes),
        revision_fria=revision_fria_de(config),
        por_linea=_por_linea(conexion, primero_del_mes, ahora),
        gastos_comunes_mes=ficha.gastos_comunes_mes(conexion, ahora),
    )


@router.get("", response_model=Plata)
def ver_plata() -> Plata:
    conexion = db.conectar()
    try:
        return calcular(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()

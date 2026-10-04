"""R2 (forma S, PLAN-FINAL.md): el Reloj — estimación basada en evidencia
(EBS de Joel Spolsky). Nunca pide un número a ciegas sin ofrecer el dato
histórico (ley 1): `estimar` siembra una simulación con las velocidades
reales (estimado ÷ real) de tareas ya hechas del mismo `tipo`, y devuelve
bandas p50/p80/p95 — no un número suelto.

Sin `creada_en` en el contrato de Tarea todavía, no se puede acotar a
«últimos 6 meses»: se usa siempre todo el historial disponible (CAMBIO DE
FORMA, anotado en la bitácora de cierre de R2).
"""
from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from fastapi import APIRouter
from pydantic import BaseModel

import db

router = APIRouter(prefix="/reloj", tags=["reloj"])

MINIMO_HISTORIAL_PROPIO = 6
MUESTRAS = 2000


def _velocidades(conexion: sqlite3.Connection, tipo: str | None) -> list[float]:
    """estimado_min / real_min de cada tarea hecha con los dos datos. Una
    velocidad < 1 significa que se tardó más de lo estimado."""
    if tipo is None:
        filas = conexion.execute(
            "SELECT estimado_min, real_min FROM tareas "
            "WHERE estado = 'hecha' AND estimado_min IS NOT NULL AND real_min IS NOT NULL AND real_min > 0"
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT estimado_min, real_min FROM tareas "
            "WHERE tipo = ? AND estado = 'hecha' AND estimado_min IS NOT NULL AND real_min IS NOT NULL AND real_min > 0",
            (tipo,),
        ).fetchall()
    return [fila["estimado_min"] / fila["real_min"] for fila in filas]


def _velocidades_para(conexion: sqlite3.Connection, tipo: str) -> tuple[list[float], int]:
    """Las del tipo si hay al menos `MINIMO_HISTORIAL_PROPIO`; si no,
    historial amplio (todas las tareas hechas, de cualquier tipo) — nunca
    cero datos solo porque ese tipo es nuevo."""
    propias = _velocidades(conexion, tipo)
    if len(propias) >= MINIMO_HISTORIAL_PROPIO:
        return propias, len(propias)
    amplias = _velocidades(conexion, None)
    return amplias, len(propias)


@dataclass(frozen=True)
class EstimacionReloj:
    p50: int
    p80: int
    p95: int
    n: int
    tipo: str


def estimar(conexion: sqlite3.Connection, tipo: str, minutos: int, semilla: int = 0) -> EstimacionReloj:
    """`minutos` es lo que Juan Camilo dice que se tarda; la simulación lo
    corrige con la velocidad real de ese tipo de tarea (o el historial
    amplio si el tipo es nuevo)."""
    velocidades, n_propias = _velocidades_para(conexion, tipo)
    if not velocidades:
        return EstimacionReloj(p50=minutos, p80=minutos, p95=minutos, n=0, tipo=tipo)

    rng = random.Random(semilla)
    muestras = sorted(minutos / rng.choice(velocidades) for _ in range(MUESTRAS))

    def _percentil(p: float) -> int:
        indice = min(len(muestras) - 1, int(p * len(muestras)))
        return round(muestras[indice])

    return EstimacionReloj(p50=_percentil(0.5), p80=_percentil(0.8), p95=_percentil(0.95), n=n_propias, tipo=tipo)


def excede_90_min(minutos: int) -> bool:
    """Ningún paso de Hoy pasa de ~90 min — regla 1 de R2.1. Función pura;
    quién lo parte (pregunta o encargo) lo decide quien llama."""
    return minutos > 90


@dataclass(frozen=True)
class Latido:
    pieza: str
    ultimo_dato: str | None
    callado_dias: int | None


class EstimacionVista(BaseModel):
    p50: int
    p80: int
    p95: int
    n: int
    tipo: str


@router.get("/estimar", response_model=EstimacionVista)
def ver_estimacion(tipo: str, min: int) -> EstimacionVista:
    conexion = db.conectar()
    try:
        estimacion = estimar(conexion, tipo, min)
        return EstimacionVista(
            p50=estimacion.p50, p80=estimacion.p80, p95=estimacion.p95, n=estimacion.n, tipo=estimacion.tipo
        )
    finally:
        conexion.close()

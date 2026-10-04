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
from datetime import datetime, timezone

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
    ultimo_dato: datetime | None
    callado_dias: int | None


DIAS_CALLADO_PARA_AVISO = 2


def _ultimo_dato_reloj(conexion: sqlite3.Connection) -> datetime | None:
    """El dato del Reloj nace cuando una sesión cierra sobre una tarea
    `hecha` con estimado y real — ahí es cuando `estimar` tiene algo
    nuevo para masticar."""
    fila = conexion.execute(
        "SELECT MAX(s.fin) AS ultimo FROM sesiones s JOIN tareas t ON t.id = s.tarea_id "
        "WHERE t.estado = 'hecha' AND t.estimado_min IS NOT NULL AND t.real_min IS NOT NULL AND s.fin IS NOT NULL"
    ).fetchone()
    return fila["ultimo"] if fila and fila["ultimo"] else None


def _ultimo_dato_pronosticos(conexion: sqlite3.Connection) -> datetime | None:
    fila = conexion.execute("SELECT MAX(creada_en) AS ultimo FROM pronostico").fetchone()
    return fila["ultimo"] if fila and fila["ultimo"] else None


def _ultimo_dato_cuenta(conexion: sqlite3.Connection) -> datetime | None:
    fila = conexion.execute("SELECT MAX(fecha) AS ultimo FROM propuesta").fetchone()
    return fila["ultimo"] if fila and fila["ultimo"] else None


def calcular_latido(conexion: sqlite3.Connection, ahora: datetime) -> list[Latido]:
    """R5.2: si el reloj, los pronósticos o la cuenta no reciben datos en
    `DIAS_CALLADO_PARA_AVISO` días, acá es donde se nota — `callado_dias`
    es `None` si esa pieza nunca tuvo un dato (no hay desde cuándo
    contar), no un número inventado."""
    piezas = {"reloj": _ultimo_dato_reloj, "pronosticos": _ultimo_dato_pronosticos, "cuenta": _ultimo_dato_cuenta}
    resultado = []
    for nombre, obtener in piezas.items():
        crudo = obtener(conexion)
        ultimo = datetime.fromisoformat(crudo) if isinstance(crudo, str) else crudo
        if ultimo is not None and ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=timezone.utc)
        callado_dias = (ahora - ultimo).days if ultimo is not None else None
        resultado.append(Latido(pieza=nombre, ultimo_dato=ultimo, callado_dias=callado_dias))
    return resultado


def piezas_caladas(latidos: list[Latido]) -> list[Latido]:
    """Las que merecen el aviso callado (R5.2): 2 días o más sin dato."""
    return [l for l in latidos if l.callado_dias is not None and l.callado_dias >= DIAS_CALLADO_PARA_AVISO]


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


class LatidoVista(BaseModel):
    pieza: str
    ultimo_dato: datetime | None
    callado_dias: int | None

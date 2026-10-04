"""R4.4 (PLAN-FINAL.md): simulación de seis meses, sembrada con `numpy`
(misma semilla → mismas bandas, siempre). Nunca decide qué es verdad:
toma una media y una desviación mensual YA calculadas en código (de
`cuenta`/`reloj`/medido real) y las corre hacia adelante — bandas
probable (p50) / posible (p80) / techo (p95), cuántas de 10 corridas
chicas llegan a un umbral, cuántas se van a ruina, y Kelly solo como
TOPE del tamaño (nunca decide si se hace una apuesta, solo cuánto como
máximo) — con la probabilidad ya recalibrada por `calibracion.py`,
jamás la cruda de un modelo."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MESES = 6
CORRIDAS_BANDAS = 10_000
CORRIDAS_FRECUENCIA = 10


@dataclass(frozen=True)
class Bandas:
    probable: float
    posible: float
    techo: float


@dataclass(frozen=True)
class Frecuencia:
    de_10: int
    umbral: float


@dataclass(frozen=True)
class ResultadoSimulacion:
    bandas: Bandas
    frecuencia: Frecuencia
    ruina_de_10: int


def simular(media_mensual: float, desviacion_mensual: float, umbral: float, semilla: int = 0) -> ResultadoSimulacion:
    """La plata no es negativa de verdad: cada mes simulado se recorta en
    0 antes de sumar (una mala racha no se compensa sola con un mes
    negativo que no puede pasar)."""
    rng = np.random.default_rng(semilla)
    meses_grande = np.maximum(rng.normal(media_mensual, desviacion_mensual, size=(CORRIDAS_BANDAS, MESES)), 0.0)
    totales_grande = meses_grande.sum(axis=1)
    p50, p80, p95 = np.percentile(totales_grande, [50, 80, 95])
    bandas = Bandas(probable=round(float(p50), 2), posible=round(float(p80), 2), techo=round(float(p95), 2))

    rng_chica = np.random.default_rng(semilla)
    meses_chica = np.maximum(rng_chica.normal(media_mensual, desviacion_mensual, size=(CORRIDAS_FRECUENCIA, MESES)), 0.0)
    totales_chica = meses_chica.sum(axis=1)
    de_10 = int((totales_chica >= umbral).sum())
    ruina_de_10 = int((totales_chica <= 0.0).sum())

    return ResultadoSimulacion(bandas=bandas, frecuencia=Frecuencia(de_10=de_10, umbral=umbral), ruina_de_10=ruina_de_10)


def kelly_tope(probabilidad: float, ganancia_neta: float, perdida_neta: float) -> float:
    """Kelly SOLO como tope del tamaño — nunca decide si se hace. 0 si la
    apuesta no tiene borde matemático (ganancia o pérdida inválidas, o la
    probabilidad no alcanza para un borde positivo)."""
    if perdida_neta <= 0 or ganancia_neta <= 0 or not (0.0 <= probabilidad <= 1.0):
        return 0.0
    b = ganancia_neta / perdida_neta
    fraccion = probabilidad - (1 - probabilidad) / b
    return max(0.0, min(1.0, fraccion))

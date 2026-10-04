"""R4.5 (forma P, PLAN-FINAL.md): pronósticos y calibración.

Todo número que Remi muestra queda guardado acá con su regla de sí/no
(`regla_si_no`) — nunca una cifra suelta sin cómo se comprueba después.

El recalibrador adapta la matemática de Metaculus/forecasting-tools
(`calibration_adjustment/logistic_recalibration_adjuster.py`, MIT — aviso
completo en `LICENCIAS-TERCEROS.md`): un ajuste afín en log-odds (estilo
Platt),

    mu(p) = sigmoid((logit(p) - BIA) / CON)

con `BIA` (sesgo hacia sí/no) y `CON` (sobre/subconfianza) ajustados por
regresión logística de una variable sobre `(logit(p), resultado)`. Se
reescribió el fit acá (Newton-Raphson, solo `numpy`) en vez de sumar
`pandas`/`scikit-learn` como dependencias por un ajuste de dos
parámetros — la matemática del ajuste es la misma que la original.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from modelos import Pronostico

router = APIRouter(tags=["calibracion"])

MINIMO_RESUELTOS_PARA_RECALIBRAR = 10
MINIMO_RESUELTOS_PARA_GRAFICA = 20
_EPS_LOGIT = 1e-6
_EPS_CLIP = 1e-4
_MAX_ITERACIONES = 50
_TOLERANCIA = 1e-8


def _logit_seguro(p: np.ndarray) -> np.ndarray:
    recortado = np.clip(p, _EPS_LOGIT, 1.0 - _EPS_LOGIT)
    return np.log(recortado / (1.0 - recortado))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class Recalibrador:
    bia: float
    con: float

    def ajustar(self, p: float) -> float:
        z = _logit_seguro(np.array([p]))[0]
        ajustado = float(_sigmoid((z - self.bia) / self.con))
        return float(np.clip(ajustado, _EPS_CLIP, 1.0 - _EPS_CLIP))


def entrenar_recalibrador(predicciones: list[float], resultados: list[bool]) -> Recalibrador | None:
    """None si no hay los 10 resueltos mínimos, o si todos resolvieron
    igual (la regresión logística no tiene nada que separar) — nunca un
    número inventado."""
    if len(predicciones) < MINIMO_RESUELTOS_PARA_RECALIBRAR:
        return None
    y = np.array([1.0 if r else 0.0 for r in resultados])
    if len(set(y.tolist())) < 2:
        return None

    z = _logit_seguro(np.array(predicciones))
    x = np.column_stack([np.ones_like(z), z])  # [intercepto, pendiente]
    theta = np.zeros(2)
    for _ in range(_MAX_ITERACIONES):
        mu = _sigmoid(x @ theta)
        gradiente = x.T @ (y - mu)
        w = mu * (1 - mu)
        w = np.clip(w, 1e-9, None)
        hessiano = (x * w[:, None]).T @ x
        try:
            paso = np.linalg.solve(hessiano, gradiente)
        except np.linalg.LinAlgError:
            return None
        theta = theta + paso
        if np.max(np.abs(paso)) < _TOLERANCIA:
            break

    alpha, beta = float(theta[0]), float(theta[1])
    if not np.isfinite(alpha) or not np.isfinite(beta) or beta <= 0:
        return None
    con = 1.0 / beta
    bia = -alpha / beta
    if not np.isfinite(con) or not np.isfinite(bia) or con <= 0:
        return None
    return Recalibrador(bia=bia, con=con)


class CuerpoPronostico(BaseModel):
    que: str
    p: float
    vence: datetime
    regla_si_no: str
    tipo: Literal["mundo", "conducta"]
    origen: str


@router.post("/pronosticos", status_code=201)
def crear_pronostico(cuerpo: CuerpoPronostico) -> dict:
    conexion = db.conectar()
    try:
        pronostico = Pronostico(
            id=uuid4(), que=cuerpo.que, p=cuerpo.p, vence=cuerpo.vence, regla_si_no=cuerpo.regla_si_no,
            tipo=cuerpo.tipo, origen=cuerpo.origen, resultado=None, creada_en=datetime.now(timezone.utc),
        )
        db.crear_pronostico(conexion, pronostico)
        return {"id": str(pronostico.id)}
    finally:
        conexion.close()


class CuerpoResolver(BaseModel):
    resultado: bool | None


@router.post("/pronosticos/{pronostico_id}/resolver")
def resolver_pronostico(pronostico_id: str, cuerpo: CuerpoResolver) -> dict:
    conexion = db.conectar()
    try:
        if db.leer_pronostico(conexion, pronostico_id) is None:
            raise HTTPException(status_code=404, detail="no existe ese pronóstico")
        db.resolver_pronostico(conexion, pronostico_id, cuerpo.resultado)
        return {"id": pronostico_id, "resultado": cuerpo.resultado}
    finally:
        conexion.close()


class PorTipo(BaseModel):
    resueltos: int
    sesgo_si: float | None
    sobreconfianza: float | None


class VistaCalibracion(BaseModel):
    resueltos: int
    sesgo_si: float | None
    sobreconfianza: float | None
    muestra_grafica: bool
    por_tipo: dict[str, PorTipo]


def _stats_de(pronosticos: list[Pronostico]) -> tuple[int, float | None, float | None]:
    resueltos = [p for p in pronosticos if p.resultado is not None]
    predicciones = [p.p for p in resueltos]
    resultados = [bool(p.resultado) for p in resueltos]
    recalibrador = entrenar_recalibrador(predicciones, resultados)
    sesgo_si = recalibrador.bia if recalibrador else None
    sobreconfianza = recalibrador.con if recalibrador else None
    return len(resueltos), sesgo_si, sobreconfianza


@router.get("/calibracion", response_model=VistaCalibracion)
def ver_calibracion() -> VistaCalibracion:
    conexion = db.conectar()
    try:
        todos = db.listar_pronosticos(conexion)
        resueltos, sesgo_si, sobreconfianza = _stats_de(todos)
        por_tipo: dict[str, PorTipo] = {}
        for tipo in sorted({p.tipo for p in todos}):
            del_tipo = [p for p in todos if p.tipo == tipo]
            n, bia, con = _stats_de(del_tipo)
            por_tipo[tipo] = PorTipo(resueltos=n, sesgo_si=bia, sobreconfianza=con)
        return VistaCalibracion(
            resueltos=resueltos, sesgo_si=sesgo_si, sobreconfianza=sobreconfianza,
            muestra_grafica=resueltos >= MINIMO_RESUELTOS_PARA_GRAFICA, por_tipo=por_tipo,
        )
    finally:
        conexion.close()

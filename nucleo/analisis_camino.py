"""R3 (forma Q, PLAN-FINAL.md): el análisis de un camino. El código nunca
decide qué es verdad: `verificar_fuentes` es la única puerta por la que
una fuente pasa a `verificada = true`, y solo lo hace si tiene fragmento
Y un `confirmador` (modelo barato, inyectado — nunca de pago en pytest)
dice que ese fragmento respalda lo que se cita. Sin fragmento, o si el
confirmador dice que no, queda como «supuesto» (`verificada = false`),
nunca se inventa.

El investigador real (STORM + la herramienta de búsqueda de Claude, R3.2)
NO está wireado todavía — es el BLOQUEADO que queda anotado en la
bitácora de cierre de R3: diseñar ese prompt y confirmar cómo se habilita
la búsqueda en `claude -p` es trabajo de una sesión dedicada, no algo que
se improvisa dentro de esta. Lo que sí está completo y probado es el
pipeline: estado, fuentes, verificación — listo para que `investigador`
se reemplace por la llamada real sin tocar nada de esto.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from modelos import AnalisisCamino, Fuente

router = APIRouter(prefix="/rumbo/caminos", tags=["rumbo"])


@dataclass(frozen=True)
class FuenteCruda:
    url: str
    fecha: datetime
    fragmento: str
    tipo: str | None = None


@dataclass(frozen=True)
class ResultadoInvestigacion:
    mercado: str | None
    competidores: str | None
    juego: str | None
    a_favor: str | None
    en_contra: str | None
    dominio: str | None
    base_texto: str | None
    palancas: str | None
    objeciones: str | None
    prueba: str | None
    fuentes: list[FuenteCruda]


class Investigador(Protocol):
    def __call__(self, idea_texto: str) -> ResultadoInvestigacion: ...


Confirmador = Callable[[str, str], bool]
"""(fragmento, lo_citado) -> si el fragmento de verdad respalda la cifra."""


def verificar_fuentes(crudas: list[FuenteCruda], confirmador: Confirmador, lo_citado: str) -> list[tuple[FuenteCruda, bool]]:
    """Una fuente sin fragmento nunca se verifica — ni se le pregunta al
    confirmador (regla: no hay verificación sin evidencia literal)."""
    resultado = []
    for cruda in crudas:
        if not cruda.fragmento.strip():
            resultado.append((cruda, False))
            continue
        resultado.append((cruda, confirmador(cruda.fragmento, lo_citado)))
    return resultado


def ejecutar_investigacion(
    conexion: sqlite3.Connection,
    analisis_id: str,
    idea_texto: str,
    investigador: Investigador,
    confirmador: Confirmador,
) -> AnalisisCamino:
    """Corre el análisis completo y lo cierra — `listo` si el investigador
    no lanza, `fallo` si lanza (nunca deja un análisis a medias sin
    estado). Quien llama decide si esto corre en el momento o en segundo
    plano; esta función es sincrónica y pura en sus efectos (solo toca
    `analisis_id`)."""
    try:
        resultado = investigador(idea_texto)
    except Exception as error:  # noqa: BLE001 — se guarda el fallo, no se propaga a medias
        db.cerrar_analisis(conexion, analisis_id, "fallo", {"mercado": f"falló: {error}"})
        analisis = db.leer_analisis(conexion, analisis_id)
        assert analisis is not None
        return analisis

    for cruda, verificada in verificar_fuentes(resultado.fuentes, confirmador, resultado.base_texto or ""):
        db.crear_fuente(
            conexion,
            Fuente(
                id=uuid4(), analisis_id=UUID(analisis_id), url=cruda.url, fecha=cruda.fecha,
                fragmento=cruda.fragmento, verificada=verificada, tipo=cruda.tipo,
            ),
        )

    db.cerrar_analisis(
        conexion, analisis_id, "listo",
        {
            "mercado": resultado.mercado, "competidores": resultado.competidores, "juego": resultado.juego,
            "a_favor": resultado.a_favor, "en_contra": resultado.en_contra, "dominio": resultado.dominio,
            "base_texto": resultado.base_texto, "palancas": resultado.palancas,
            "objeciones": resultado.objeciones, "prueba": resultado.prueba,
        },
    )
    analisis = db.leer_analisis(conexion, analisis_id)
    assert analisis is not None
    return analisis


class CuerpoAnalisis(BaseModel):
    idea_id: str


@router.post("", status_code=202)
def pedir_analisis(cuerpo: CuerpoAnalisis) -> dict:
    """202: el análisis real (R3.2, investigación con fuentes) no corre
    acá todavía — el investigador real está BLOQUEADO (ver el docstring
    del módulo). Esto deja la fila `investigando` para que no se pierda
    el pedido; se completa a mano con `ejecutar_investigacion` hasta que
    haya un investigador de verdad."""
    conexion = db.conectar()
    try:
        analisis = db.crear_analisis(conexion, cuerpo.idea_id, datetime.now(timezone.utc))
        return {"id": str(analisis.id)}
    finally:
        conexion.close()


class FuenteVista(BaseModel):
    id: str
    url: str
    fecha: datetime
    fragmento: str
    verificada: bool
    tipo: str | None


class VistaAnalisis(BaseModel):
    estado: str
    mercado: str | None
    competidores: str | None
    juego: str | None
    a_favor: str | None
    en_contra: str | None
    dominio: str | None
    base: dict | None
    palancas: str | None
    objeciones: str | None
    prueba: str | None
    fuentes: list[FuenteVista]


@router.get("/{analisis_id}", response_model=VistaAnalisis)
def ver_analisis(analisis_id: str) -> VistaAnalisis:
    conexion = db.conectar()
    try:
        analisis = db.leer_analisis(conexion, analisis_id)
        if analisis is None:
            raise HTTPException(status_code=404, detail="no existe ese análisis")
        fuentes = db.fuentes_de_analisis(conexion, analisis_id)
        return VistaAnalisis(
            estado=analisis.estado,
            mercado=analisis.mercado, competidores=analisis.competidores, juego=analisis.juego,
            a_favor=analisis.a_favor, en_contra=analisis.en_contra, dominio=analisis.dominio,
            base=({"texto": analisis.base_texto, "fuente_id": analisis.base_fuente_id} if analisis.base_texto else None),
            palancas=analisis.palancas, objeciones=analisis.objeciones, prueba=analisis.prueba,
            fuentes=[
                FuenteVista(id=str(f.id), url=f.url, fecha=f.fecha, fragmento=f.fragmento, verificada=f.verificada, tipo=f.tipo)
                for f in fuentes
            ],
        )
    finally:
        conexion.close()

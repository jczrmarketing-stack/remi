"""GET /semana (Forma D, T4.2): las cinco preguntas del panel «Semana»
contestadas con datos reales — de lunes (Bogotá) a ahora.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

import bandeja
import db
import plata

router = APIRouter(tags=["semana"])

MAXIMO_APLAZADOS = 5


class Cerrado(BaseModel):
    titulo: str
    tema: str | None
    real_min: int


class Aplazado(BaseModel):
    titulo: str
    tema: str | None


class IdeaDestacada(BaseModel):
    id: str
    texto: str
    tema: str | None


class Semana(BaseModel):
    desde: datetime
    # Lo más nuevo primero.
    cerrado: list[Cerrado]
    # Corta a propósito (ley 3): nunca «llevas N aplazadas».
    aplazado: list[Aplazado]
    ideas_frias: int
    destacada: IdeaDestacada | None


def _cerrado_de_la_semana(conexion: sqlite3.Connection, desde: datetime) -> list[Cerrado]:
    filas = conexion.execute(
        "SELECT t.titulo AS titulo, s.app_contexto AS tema, s.real_min AS real_min "
        "FROM sesiones s JOIN tareas t ON t.id = s.tarea_id "
        "WHERE s.fin IS NOT NULL AND s.inicio >= ? AND t.estado != 'archivada' ORDER BY s.fin DESC",
        (desde.isoformat(),),
    ).fetchall()
    return [Cerrado(titulo=f["titulo"], tema=f["tema"], real_min=f["real_min"]) for f in filas]


def _aplazado_de_la_semana(conexion: sqlite3.Connection, hoy_iso: str) -> list[Aplazado]:
    """Lo que tenía fecha, sigue abierto y su día ya pasó — nunca un
    contador, una lista corta (máximo 5, lo más vencido primero)."""
    filas = conexion.execute(
        "SELECT titulo, hora FROM tareas "
        "WHERE estado NOT IN ('hecha', 'archivada') AND fecha_limite IS NOT NULL "
        "AND substr(fecha_limite, 1, 10) < ? ORDER BY fecha_limite LIMIT ?",
        (hoy_iso, MAXIMO_APLAZADOS),
    ).fetchall()
    # Las tareas no guardan `tema` (contrato): None siempre, hasta que
    # `proyecto_id` exista de verdad.
    return [Aplazado(titulo=f["titulo"], tema=None) for f in filas]


def _ideas_frias(conexion: sqlite3.Connection, ahora: datetime) -> int:
    return sum(1 for _idea, fria in bandeja.listar_abiertas(conexion, ahora) if fria)


def _destacada(conexion: sqlite3.Connection) -> IdeaDestacada | None:
    destacada_id = bandeja.idea_destacada_id(conexion)
    if destacada_id is None:
        return None
    idea = bandeja.leer_idea(conexion, destacada_id)
    if idea is None:
        return None
    return IdeaDestacada(id=str(idea.id), texto=idea.texto, tema=idea.tema)


def calcular(conexion: sqlite3.Connection, ahora: datetime) -> Semana:
    desde = plata._lunes(ahora)
    hoy_iso = ahora.astimezone(plata.BOGOTA).date().isoformat()
    return Semana(
        desde=desde,
        cerrado=_cerrado_de_la_semana(conexion, desde),
        aplazado=_aplazado_de_la_semana(conexion, hoy_iso),
        ideas_frias=_ideas_frias(conexion, ahora),
        destacada=_destacada(conexion),
    )


@router.get("/semana", response_model=Semana)
def ver_semana() -> Semana:
    conexion = db.conectar()
    try:
        return calcular(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()

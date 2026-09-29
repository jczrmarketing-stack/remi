"""Generado desde contratos/contratos.json por generar_modelos.py.

No editar a mano: corre `uv run python generar_modelos.py` de nuevo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Tarea(BaseModel):
    id: UUID
    titulo: str
    proyecto_id: UUID | None
    estado: Literal["hoy", "camino", "hecha"]
    paso_minimo: str
    estimado_min: int | None
    real_min: int | None
    compartible: bool = False


class Idea(BaseModel):
    id: UUID
    texto: str
    origen: Literal["voz", "texto"]
    creada_en: datetime
    enfria_hasta: datetime
    estado: Literal["enfriando", "lista", "proyecto", "soltada"]
    problema_vision: int | None = Field(ge=1, le=6, default=None)


class Sesion(BaseModel):
    id: UUID
    tarea_id: UUID
    inicio: datetime
    fin: datetime | None
    real_min: int
    app_contexto: str | None


class Nudge(BaseModel):
    id: UUID
    tipo: Literal["cuerpo", "ritual", "encoger"]
    voz: str
    salida_amable: bool = True
    respuesta: Literal["listo", "ahora_no"] | None


class Entrega(BaseModel):
    id: UUID
    cliente: str
    proyecto_id: UUID
    fecha: datetime
    monto: float | None
    estado: Literal["camino", "entregada", "pagada"]
    compartible: bool = True

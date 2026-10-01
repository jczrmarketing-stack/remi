"""Generado desde contratos/contratos.json por generar_modelos.py.

No editar a mano: corre `uv run python generar_modelos.py` de nuevo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Tarea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    titulo: str
    proyecto_id: UUID | None
    estado: Literal["hoy", "camino", "hecha", "archivada"]
    paso_minimo: str
    estimado_min: int | None
    real_min: int | None
    hora: str | None
    fecha_limite: datetime | None
    compartible: bool = False


class Idea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    texto: str
    origen: Literal["voz", "texto"]
    creada_en: datetime
    enfria_hasta: datetime
    estado: Literal["enfriando", "lista", "proyecto", "soltada", "archivada"]
    problema_vision: int | None = Field(ge=1, le=6, default=None)
    tema: str | None


class Sesion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tarea_id: UUID
    inicio: datetime
    fin: datetime | None
    real_min: int
    app_contexto: str | None


class Nudge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tipo: Literal["cuerpo", "ritual", "encoger", "rumbo"]
    voz: str
    salida_amable: bool = True
    respuesta: Literal["listo", "ahora_no"] | None


class Memoria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    titulo: str = Field(min_length=1, max_length=80)
    resumen: str = Field(min_length=1, max_length=240)
    tema: str
    fecha: datetime
    cuerpo: str
    fuente: Literal["conversacion", "manual", "ollama"]
    claves: str | None
    nivel: int | None = Field(ge=0, le=3, default=None)


class Entrega(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    cliente: str
    proyecto_id: UUID
    fecha: datetime
    monto: float | None
    estado: Literal["camino", "entregada", "pagada"]
    linea: str | None
    compartible: bool = True

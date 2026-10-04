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
    tipo: str | None
    compartible: bool = False


class Idea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    texto: str
    origen: Literal["voz", "texto", "rumbo"]
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
    tipo: Literal["decision"] | None


class Pregunta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tema: str
    campo: str
    voz: str
    estado: Literal["pendiente", "respondida", "despues"]
    creada_en: datetime
    disponible_desde: datetime


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


class Vision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    texto: str
    creada_en: datetime


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    monto_min: float | None
    monto_max: float | None
    meses_seguidos: int | None
    limites: str | None
    confirmada: bool = False
    creada_en: datetime


class Escalon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    n: int
    texto: str
    criterio: str
    estado: Literal["conquistado", "ahora", "sigue", "luego", "norte"]


class Partida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tipo: Literal["recurso", "habilidad", "cuesta", "preferencia"]
    texto: str
    valor: str
    origen: Literal["medido", "dicho", "pregunta"]
    dominio: Literal["cirujano", "sabe", "aprendiz"] | None
    calculada_en: datetime


class Propuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    cliente: str
    monto: float
    fecha: datetime
    estado: Literal["pendiente", "cerrada", "perdida"]


class Apuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    camino: str
    inicio: datetime
    fin: datetime
    tope_horas: float
    tope_plata: float
    resultado: Literal["sigue", "pausa", "extender"] | None


class AnalisisCamino(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    idea_id: UUID
    estado: Literal["investigando", "listo", "fallo"]
    mercado: str | None
    competidores: str | None
    juego: str | None
    a_favor: str | None
    en_contra: str | None
    dominio: str | None
    base_texto: str | None
    base_fuente_id: UUID | None
    palancas: str | None
    objeciones: str | None
    prueba: str | None
    creada_en: datetime


class Fuente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    analisis_id: UUID
    url: str
    fecha: datetime
    fragmento: str
    verificada: bool = False
    tipo: str | None


class Pronostico(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    que: str
    p: float
    vence: datetime
    regla_si_no: str
    tipo: Literal["mundo", "conducta"]
    origen: str
    resultado: bool | None
    creada_en: datetime

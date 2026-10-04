"""B10.1 (PLAN-FINAL.md): Google Calendar. Las citas entran como `Tarea`
con hora; los bloques de Hoy compartibles pueden salir como eventos.

**ESPERA PERMISO**: el OAuth real (Ajustes → Conexiones) necesita que
Juan Camilo cree el proyecto en Google Cloud y autorice la app — sin eso
no hay token con que llamar a la API real. Lo que sí está completo y
probado es la conversión (evento ↔ Tarea), que no necesita el OAuth para
probarse: se le pasan eventos ya traídos (un doble en pytest, la
respuesta real de la API en producción, una vez que el OAuth exista).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

import db
from modelos import Tarea

router = APIRouter(prefix="/calendario", tags=["calendario"])

BOGOTA = ZoneInfo("America/Bogota")


@dataclass(frozen=True)
class EventoInvalido:
    razon: str


def evento_a_tarea(evento: dict[str, object]) -> Tarea | EventoInvalido:
    """Un evento de la API de Google Calendar (`events.list`), con o sin
    hora (`start.dateTime` vs `start.date`). Nunca adivina: un evento sin
    título o sin fecha de inicio queda `EventoInvalido`, no una Tarea a
    medias."""
    titulo = evento.get("summary")
    if not isinstance(titulo, str) or not titulo.strip():
        return EventoInvalido(razon="sin título")

    inicio = evento.get("start")
    if not isinstance(inicio, dict):
        return EventoInvalido(razon="sin fecha de inicio")

    hora: str | None = None
    fecha_limite: datetime | None = None
    if isinstance(inicio.get("dateTime"), str):
        momento = datetime.fromisoformat(str(inicio["dateTime"]))
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        local = momento.astimezone(BOGOTA)
        hora = local.strftime("%H:%M")
        fecha_limite = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    elif isinstance(inicio.get("date"), str):
        fecha_limite = datetime.combine(date.fromisoformat(str(inicio["date"])), datetime.min.time(), tzinfo=timezone.utc)
    else:
        return EventoInvalido(razon="sin fecha de inicio")

    return Tarea(
        id=uuid4(), titulo=titulo.strip(), proyecto_id=None, estado="camino", paso_minimo="Ver la cita",
        estimado_min=None, real_min=None, hora=hora, fecha_limite=fecha_limite, tipo=None, compartible=False,
    )


def tarea_a_evento(tarea: Tarea) -> dict[str, object] | None:
    """Solo las compartibles salen al calendario (regla de privacidad por
    arquitectura, contratos/contratos.json): `None` para cualquier otra,
    nunca se manda por error."""
    if not tarea.compartible or tarea.fecha_limite is None:
        return None
    inicio: dict[str, object]
    if tarea.hora:
        horas, minutos = (int(parte) for parte in tarea.hora.split(":"))
        momento = tarea.fecha_limite.replace(hour=horas, minute=minutos)
        inicio = {"dateTime": momento.isoformat()}
    else:
        inicio = {"date": tarea.fecha_limite.date().isoformat()}
    return {"summary": tarea.titulo, "start": inicio}


def sincronizar_citas(conexion: sqlite3.Connection, eventos: list[dict[str, object]]) -> list[Tarea]:
    """Cada evento válido se guarda como una `Tarea` nueva — sin
    deduplicar todavía por id de evento de Google (limitación anotada en
    la bitácora de cierre de B10: hace falta guardar el id del evento
    para no duplicar en una segunda sincronización, y eso es parte del
    mismo ESPERA PERMISO: no se prueba de verdad sin el OAuth corriendo)."""
    creadas = []
    for evento in eventos:
        resultado = evento_a_tarea(evento)
        if isinstance(resultado, EventoInvalido):
            continue
        db.crear_tarea(conexion, resultado)
        creadas.append(resultado)
    return creadas


class CuerpoImportar(BaseModel):
    eventos: list[dict[str, object]]


@router.post("/importar", status_code=201)
def importar_citas(cuerpo: CuerpoImportar) -> dict:
    conexion = db.conectar()
    try:
        creadas = sincronizar_citas(conexion, cuerpo.eventos)
        return {"creadas": len(creadas)}
    finally:
        conexion.close()


@router.get("/estado")
def estado_conexion() -> dict:
    """ESPERA PERMISO: sin OAuth real todavía, siempre `conectado: false`
    — nunca se inventa una conexión que no existe."""
    return {"conectado": False}

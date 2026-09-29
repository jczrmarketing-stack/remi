"""FastAPI local — solo 127.0.0.1:4400. No escucha en la red."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

import db
from modelos import Sesion, Tarea

app = FastAPI(title="Remi — núcleo")

MAX_PALABRAS_VOZ = 20


def frase_remi(paso_minimo: str) -> str:
    """Voz de Remi: display-it, ≤20 palabras, sin exclamaciones, un paso pequeño (Ley 3, 4)."""
    frase = f"Hoy solo esto: {paso_minimo}."
    palabras = frase.split()
    if len(palabras) > MAX_PALABRAS_VOZ:
        frase = " ".join(palabras[: MAX_PALABRAS_VOZ - 1]) + "…"
    return frase


class MensajeEntrante(BaseModel):
    texto: str


class RespuestaMensaje(BaseModel):
    tarea: Tarea
    sesion: Sesion
    voz: str


class TareaConHistorial(BaseModel):
    tarea: Tarea
    sesiones: list[Sesion]


@app.post("/mensaje", response_model=RespuestaMensaje)
def recibir_mensaje(mensaje: MensajeEntrante) -> RespuestaMensaje:
    tarea = Tarea(
        id=uuid4(),
        titulo=mensaje.texto,
        proyecto_id=None,
        estado="hoy",
        paso_minimo=mensaje.texto,
        estimado_min=None,
        real_min=None,
        compartible=False,
    )
    sesion = Sesion(
        id=uuid4(),
        tarea_id=tarea.id,
        inicio=datetime.now(timezone.utc),
        fin=None,
        real_min=0,
        app_contexto=None,
    )

    conexion = db.conectar()
    try:
        db.crear_tarea(conexion, tarea)
        db.crear_sesion(conexion, sesion)
    finally:
        conexion.close()

    return RespuestaMensaje(tarea=tarea, sesion=sesion, voz=frase_remi(tarea.paso_minimo))


@app.get("/hoy", response_model=list[TareaConHistorial])
def listar_hoy() -> list[TareaConHistorial]:
    conexion = db.conectar()
    try:
        tareas = db.listar_tareas_hoy(conexion)
        return [
            TareaConHistorial(
                tarea=tarea, sesiones=db.listar_sesiones_tarea(conexion, tarea.id)
            )
            for tarea in tareas
        ]
    finally:
        conexion.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=4400)

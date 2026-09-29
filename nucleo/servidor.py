"""FastAPI local. El bind en 127.0.0.1 no protege del origen: por acá no pueden
salir pacientes, finanzas ni salud — eso lo hace la regla de compartible=true
en los espejos, no este servidor."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from modelos import Sesion, Tarea

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "nucleo.json"
CONFIG = json.loads(RUTA_CONFIG.read_text())
HOST = CONFIG["host"]
PUERTO = CONFIG["puerto"]

app = FastAPI(title="Remi — núcleo")

# Orígenes reales del webview de la ventanita (Tauri 2, macOS): el devUrl de
# tauri.conf.json en desarrollo, y el esquema tauri:// en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

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


class EstadoNuevo(BaseModel):
    estado: Literal["hoy", "camino", "hecha"]


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
        # Invariante defensiva: nunca dos sesiones abiertas en paralelo para
        # la misma tarea. Hoy /mensaje siempre crea una tarea nueva (id
        # recién generado), así que esto es un no-op — pero si /mensaje
        # llega a referenciar una tarea existente, ya queda a salvo.
        abierta = db.sesion_abierta_de_tarea(conexion, tarea.id)
        if abierta is not None:
            db.cerrar_sesion(conexion, abierta)
        db.crear_sesion(conexion, sesion)
    finally:
        conexion.close()

    return RespuestaMensaje(tarea=tarea, sesion=sesion, voz=frase_remi(tarea.paso_minimo))


@app.post("/sesion/{sesion_id}/cerrar", response_model=Sesion)
def cerrar_sesion(sesion_id: UUID) -> Sesion:
    conexion = db.conectar()
    try:
        sesion = db.cerrar_sesion(conexion, sesion_id)
        if sesion is None:
            raise HTTPException(status_code=404, detail="no hay sesión abierta con ese id")
        return sesion
    finally:
        conexion.close()


@app.post("/tarea/{tarea_id}/estado", response_model=Tarea)
def actualizar_estado(tarea_id: UUID, cuerpo: EstadoNuevo) -> Tarea:
    conexion = db.conectar()
    try:
        tarea = db.actualizar_estado_tarea(conexion, tarea_id, cuerpo.estado)
        if tarea is None:
            raise HTTPException(status_code=404, detail="no existe esa tarea")
        if cuerpo.estado == "hecha":
            abierta = db.sesion_abierta_de_tarea(conexion, tarea_id)
            if abierta is not None:
                db.cerrar_sesion(conexion, abierta)
        return tarea
    finally:
        conexion.close()


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

    uvicorn.run(app, host=HOST, port=PUERTO)

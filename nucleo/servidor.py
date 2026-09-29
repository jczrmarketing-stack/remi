"""FastAPI local — solo 127.0.0.1:4400. No escucha en la red."""
from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

import db
from modelos import Tarea

app = FastAPI(title="Remi — núcleo")


class MensajeEntrante(BaseModel):
    texto: str


@app.post("/mensaje", response_model=Tarea)
def recibir_mensaje(mensaje: MensajeEntrante) -> Tarea:
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
    conexion = db.conectar()
    try:
        db.guardar_tarea(conexion, tarea)
    finally:
        conexion.close()
    return tarea


@app.get("/hoy", response_model=list[Tarea])
def listar_hoy() -> list[Tarea]:
    conexion = db.conectar()
    try:
        return db.listar_tareas_por_estado(conexion, "hoy")
    finally:
        conexion.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=4400)

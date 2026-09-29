"""FastAPI local. El bind en 127.0.0.1 no protege del origen: por acá no pueden
salir pacientes, finanzas ni salud — eso lo hace la regla de compartible=true
en los espejos, no este servidor."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

import db
import pensar
import tts
from modelos import Memoria, Sesion, Tarea

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

# paso_minimo no se decide al crear la tarea (ahí no puede haber fricción):
# nace con esto, universal, nunca vacío, con algo real a lo que la ley 3
# pueda encoger desde el día uno. El verdadero se fija después —
# POST /tarea/{id}/paso-minimo, o más adelante el nudge "encoger".
PASO_MINIMO_INICIAL = "Cinco minutos en esto y paramos."


def recortar_voz(frase: str) -> str:
    """La voz de Remi nunca pasa de 20 palabras, venga de donde venga."""
    palabras = frase.split()
    if len(palabras) > MAX_PALABRAS_VOZ:
        frase = " ".join(palabras[: MAX_PALABRAS_VOZ - 1]) + "…"
    return frase


def frase_remi(titulo: str) -> str:
    """Voz de Remi: display-it, ≤20 palabras, sin exclamaciones, un paso pequeño (Ley 3, 4)."""
    return recortar_voz(f"Hoy solo esto: {titulo}.")


class MensajeEntrante(BaseModel):
    texto: str
    # Opt-in por mensaje: solo con think=true se gasta un token (ver pensar.py).
    think: bool = False


class TokensClaude(BaseModel):
    entrada: int
    salida: int
    modelo: str


class RespuestaMensaje(BaseModel):
    tarea: Tarea
    sesion: Sesion
    voz: str
    # Solo cuando pensó con Claude. Dato de operación: la ventanita lo manda
    # a su consola, nunca a la pantalla.
    tokens: TokensClaude | None = None


class TareaConHistorial(BaseModel):
    tarea: Tarea
    sesiones: list[Sesion]
    ultima_vez_min: int | None


class EstadoNuevo(BaseModel):
    estado: Literal["hoy", "camino", "hecha"]


class Historial(BaseModel):
    sesiones: list[Sesion]
    total_min: int


class PasoMinimoNuevo(BaseModel):
    paso_minimo: str


class PedidoVoz(BaseModel):
    text: str
    # None o "auto": la elige el texto (español salvo que sea claro inglés).
    voice: str | None = None
    # El estirado de 1×/1.5×/2× lo hace el reproductor de la ventanita, que
    # conserva el tono; acá se genera a 1.0.
    speed: float = Field(default=tts.VELOCIDAD_GENERACION, gt=0.25, lt=4.0)


class VozDisponible(BaseModel):
    id: str
    lang: str
    label: str


class EntradaDeIndice(BaseModel):
    """Lo que Remi tiene presente. Sin `cuerpo`, a propósito: para eso está
    GET /memoria/{id}."""

    id: UUID
    titulo: str
    resumen: str
    tema: str
    fecha: datetime


class MemoriaNueva(BaseModel):
    # Los largos los pone el contrato (Memoria), no este archivo: acá
    # llegan crudos y Pydantic los valida al construir la memoria.
    titulo: str
    resumen: str
    cuerpo: str
    tema: str
    fuente: Literal["conversacion", "manual", "ollama"] = "manual"


class MemoriaEditada(BaseModel):
    titulo: str | None = None
    resumen: str | None = None
    tema: str | None = None
    cuerpo: str | None = None


# Los largos los pone el contrato (Memoria). Cuando algo no entra, Pydantic
# levanta ValidationError al construirla: acá se traduce a un 422 con voz
# de Remi, en vez de dejarlo salir como un 500.
NO_ENTRA = "Así no entra: el título va hasta 80 caracteres y el resumen hasta 240, y ninguno vacío."


@app.post("/mensaje", response_model=RespuestaMensaje)
def recibir_mensaje(mensaje: MensajeEntrante) -> RespuestaMensaje:
    # Si pidió pensar, el paso mínimo lo ordena Claude y es lo que Remi
    # dice. Si no pidió (o Claude no pudo), todo sigue como siempre, sin IA.
    pensado = pensar.pensar(mensaje.texto) if mensaje.think else None
    paso_minimo = recortar_voz(pensado.paso_minimo) if pensado else PASO_MINIMO_INICIAL
    voz = paso_minimo if pensado else frase_remi(mensaje.texto)
    tokens = (
        TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo)
        if pensado
        else None
    )

    tarea = Tarea(
        id=uuid4(),
        titulo=mensaje.texto,
        proyecto_id=None,
        estado="hoy",
        paso_minimo=paso_minimo,
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

    return RespuestaMensaje(tarea=tarea, sesion=sesion, voz=voz, tokens=tokens)


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


@app.post("/tarea/{tarea_id}/paso-minimo", response_model=Tarea)
def actualizar_paso_minimo(tarea_id: UUID, cuerpo: PasoMinimoNuevo) -> Tarea:
    conexion = db.conectar()
    try:
        tarea = db.actualizar_paso_minimo(conexion, tarea_id, cuerpo.paso_minimo)
        if tarea is None:
            raise HTTPException(status_code=404, detail="no existe esa tarea")
        return tarea
    finally:
        conexion.close()


@app.get("/tts/voices", response_model=list[VozDisponible])
def listar_voces() -> list[VozDisponible]:
    return [VozDisponible(id=voz.id, lang=voz.lang, label=voz.label) for voz in tts.VOCES]


@app.post(
    "/tts",
    responses={200: {"content": {"audio/wav": {}}}},
    response_class=Response,
)
def decir(pedido: PedidoVoz) -> Response:
    """El wav de lo que Remi dice. Si el motor falla, 503 sin cuerpo: la
    ventanita cae a la voz del sistema en silencio. Remi jamás dice un
    error en voz alta (ley 3)."""
    texto = pedido.text.strip()
    if not texto:
        return Response(status_code=204)

    voz_id = tts.resolver_voz(pedido.voice, texto)
    if voz_id is None:
        # Una voz que no existe es un error de programación, no algo que
        # haya que contarle a nadie en voz alta.
        raise HTTPException(status_code=400, detail="no conozco esa voz")

    audio = tts.sintetizar(texto, voz_id, pedido.speed)
    if audio is None:
        return Response(status_code=503)

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"X-Remi-Voz": voz_id},
    )


# — El estante: las mismas operaciones que ve el MCP, por HTTP —


@app.get("/memoria", response_model=list[EntradaDeIndice])
def listar_memoria() -> list[EntradaDeIndice]:
    """El índice: lo más reciente primero, nunca el cuerpo."""
    conexion = db.conectar()
    try:
        return [
            EntradaDeIndice(
                id=entrada.id,
                titulo=entrada.titulo,
                resumen=entrada.resumen,
                tema=entrada.tema,
                fecha=entrada.fecha,
            )
            for entrada in db.indice_memoria(conexion)
        ]
    finally:
        conexion.close()


@app.get("/memoria/{memoria_id}", response_model=Memoria)
def leer_una_memoria(memoria_id: UUID) -> Memoria:
    conexion = db.conectar()
    try:
        memoria = db.leer_memoria(conexion, memoria_id)
        if memoria is None:
            raise HTTPException(status_code=404, detail="no tengo nada con ese id")
        return memoria
    finally:
        conexion.close()


@app.post("/memoria", response_model=Memoria, status_code=201)
def guardar_una_memoria(cuerpo: MemoriaNueva) -> Memoria:
    try:
        memoria = Memoria(
            id=uuid4(),
            titulo=cuerpo.titulo,
            resumen=cuerpo.resumen,
            tema=cuerpo.tema,
            fecha=datetime.now(timezone.utc),
            cuerpo=cuerpo.cuerpo,
            fuente=cuerpo.fuente,
        )
    except ValidationError:
        raise HTTPException(status_code=422, detail=NO_ENTRA) from None
    conexion = db.conectar()
    try:
        db.guardar_memoria(conexion, memoria)
    finally:
        conexion.close()
    return memoria


@app.patch("/memoria/{memoria_id}", response_model=Memoria)
def editar_una_memoria(memoria_id: UUID, cambios: MemoriaEditada) -> Memoria:
    conexion = db.conectar()
    try:
        try:
            memoria = db.editar_memoria(
                conexion,
                memoria_id,
                titulo=cambios.titulo,
                resumen=cambios.resumen,
                tema=cambios.tema,
                cuerpo=cambios.cuerpo,
            )
        except ValidationError:
            raise HTTPException(status_code=422, detail=NO_ENTRA) from None
        if memoria is None:
            raise HTTPException(status_code=404, detail="no tengo nada con ese id")
        return memoria
    finally:
        conexion.close()


@app.delete("/memoria/{memoria_id}", status_code=204)
def borrar_una_memoria(memoria_id: UUID) -> Response:
    conexion = db.conectar()
    try:
        if not db.borrar_memoria(conexion, memoria_id):
            raise HTTPException(status_code=404, detail="no tengo nada con ese id")
    finally:
        conexion.close()
    return Response(status_code=204)


@app.get("/hoy", response_model=list[TareaConHistorial])
def listar_hoy() -> list[TareaConHistorial]:
    conexion = db.conectar()
    try:
        tareas = db.listar_tareas_hoy(conexion)
        return [
            TareaConHistorial(
                tarea=tarea,
                sesiones=db.listar_sesiones_tarea(conexion, tarea.id),
                # Ley 1: nunca pedir un estimado a ciegas — este es el dato
                # histórico que Remi ofrece al planear.
                ultima_vez_min=db.ultima_sesion_cerrada_min(conexion, tarea.id),
            )
            for tarea in tareas
        ]
    finally:
        conexion.close()


@app.get("/tarea/{tarea_id}/historial", response_model=Historial)
def historial_tarea(tarea_id: UUID) -> Historial:
    conexion = db.conectar()
    try:
        sesiones = db.listar_sesiones_cerradas_tarea(conexion, tarea_id)
        return Historial(sesiones=sesiones, total_min=sum(s.real_min for s in sesiones))
    finally:
        conexion.close()


if __name__ == "__main__":
    import threading

    import uvicorn

    # Cargar el modelo de voz tarda ~18 s la primera vez: si esperáramos a
    # la primera frase, Remi se quedaría muda hasta que termine. Se carga
    # en un hilo al arrancar y para cuando haga falta ya está listo. No se
    # hace al importar: las pruebas no tienen por qué cargar 300 MB.
    threading.Thread(target=tts.precalentar, daemon=True).start()

    uvicorn.run(app, host=HOST, port=PUERTO)

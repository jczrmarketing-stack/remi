"""FastAPI local. El bind en 127.0.0.1 no protege del origen: por acá no pueden
salir pacientes, finanzas ni salud — eso lo hace la regla de compartible=true
en los espejos, no este servidor."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

import clasificar
import db
import episodios
import pensar
import sembrar_conocimiento
import tts
from modelos import Idea, Memoria, Sesion, Tarea

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "nucleo.json"
CONFIG = json.loads(RUTA_CONFIG.read_text())
HOST = CONFIG["host"]
PUERTO = CONFIG["puerto"]

@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
    """Cargar el modelo de voz tarda ~18 s la primera vez: si esperáramos a
    la primera frase, Remi contestaría con la voz del sistema mientras
    tanto. Va en un hilo al arrancar el servidor, no en `__main__`, porque
    launchd levanta `uvicorn servidor:app` y ahí `__main__` nunca corre.
    Importar el módulo sigue sin cargar nada: esto es del ciclo de vida de
    la app, no del import (REMI_TTS_PRECALENTAR=0 lo apaga)."""
    if os.environ.get("REMI_TTS_PRECALENTAR", "1") != "0":
        threading.Thread(target=tts.precalentar, daemon=True).start()
    # Las fichas de proyecto al estante, al arrancar: así el índice tiene
    # una línea por proyecto. Si falla, el núcleo arranca igual.
    if os.environ.get("REMI_SEMBRAR_CONOCIMIENTO", "1") != "0":
        try:
            sembrar_conocimiento.sembrar()
        except Exception as error:  # nunca tumbar el arranque por esto
            print(f"[conocimiento] no pude sembrar ({type(error).__name__}: {error})", file=sys.stderr)
    yield


app = FastAPI(title="Remi — núcleo", lifespan=ciclo_de_vida)

# Orígenes reales del webview de la ventanita (Tauri 2, macOS): el devUrl de
# tauri.conf.json en desarrollo, y el esquema tauri:// en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

MAX_PALABRAS_VOZ = 20
# Lo que se DICE en voz alta, cuando la respuesta la escribió el modelo: el
# carácter define el largo, pero hablado un párrafo entero cansa. Lo escrito
# en pantalla va completo.
MAX_FRASES_HABLADAS = 3

# Ley 6: lo suelto enfría dos días antes de poder volverse proyecto.
HORAS_DE_ENFRIAMIENTO = 48

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


def sin_markdown(texto: str) -> str:
    """Lo que se dice en voz alta no puede traer símbolos: Kokoro leería
    «asterisco asterisco». Negritas, títulos, listas, citas, enlaces y
    código quedan como texto plano."""
    import re

    texto = re.sub(r"^\s{0,3}#{1,6}\s+", "", texto, flags=re.M)
    texto = re.sub(r"^\s{0,3}>\s?", "", texto, flags=re.M)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"`([^`]+)`", r"\1", texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"__(.+?)__", r"\1", texto)
    texto = re.sub(r"(^|[\s(])\*(?!\s)([^*\n]+?)\*(?=[\s).,;:!?]|$)", r"\1\2", texto, flags=re.M)
    texto = re.sub(r"^\s*[-*+]\s+", "", texto, flags=re.M)
    texto = texto.replace("**", "")
    # Las líneas de una lista, dichas, son frases: que terminen en punto.
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    return " ".join(l if l[-1] in ".!?…:" else l + "." for l in lineas)


def para_hablar(texto: str) -> str:
    """Las primeras MAX_FRASES_HABLADAS frases de `texto`, sin markdown."""
    import re

    texto = sin_markdown(texto)
    frases = re.split(r"(?<=[.!?…])\s+", texto.strip())
    if len(frases) <= MAX_FRASES_HABLADAS:
        return texto.strip()
    return " ".join(frases[:MAX_FRASES_HABLADAS])


def frase_remi(titulo: str) -> str:
    """Voz de Remi: display-it, ≤20 palabras, sin exclamaciones, un paso pequeño (Ley 3, 4)."""
    return recortar_voz(f"Hoy solo esto: {titulo}.")


def formatear_duracion(minutos: int) -> str:
    """Mismo formato que el «hace N min» de la ventanita (tiempo.ts): por
    debajo de una hora, «40 min»; por encima, «1 h 40»."""
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto:02d}" if resto else f"{horas} h"


class MensajeEntrante(BaseModel):
    texto: str
    # Opt-in por mensaje: solo con think=true se gasta un token (ver pensar.py).
    think: bool = False
    # Con qué motor pensar, elegido a conciencia en la ventanita. None = el
    # del .env.
    motor: Literal["claude", "venice", "ollama"] | None = None
    # Rápido (Haiku), equilibrio (Sonnet, por defecto) o inteligente (Opus
    # con razonamiento). Solo aplica al motor claude.
    # «prompt» no es un cerebro sino un formato: arma un encargo para Claude
    # Code con Sonnet (equilibrio) y no clasifica ni guarda nada.
    modo: Literal["rapido", "equilibrio", "inteligente", "prompt"] = "equilibrio"
    # Cuánto piensa el modelo elegido antes de contestar. None = lo suyo
    # (Opus medio, Haiku y Sonnet bajo). Solo aplica al motor claude.
    nivel: Literal["bajo", "medio", "alto", "extra"] | None = None
    # Con Ollama, cuál de los modelos de `ollama list`. None = el de siempre.
    modelo_ollama: str | None = None
    # Cómo entró: por voz o escrito. Lo guarda la Idea (contrato).
    origen: Literal["voz", "texto"] = "texto"


class TokensClaude(BaseModel):
    entrada: int
    salida: int
    modelo: str


class RespuestaMensaje(BaseModel):
    # Lo decide el clasificador, nunca el modelo: pensar solo reformula la
    # voz. Una idea no crea tarea ni sesión, y un cierre no crea nada.
    # «encargo» es el modo Prompt, que no pasa por el clasificador.
    tipo: clasificar.TipoMensaje | Literal["encargo"]
    tarea: Tarea | None = None
    sesion: Sesion | None = None
    # Lo que se ve en la pantalla, completo.
    texto: str = ""
    # Lo que se dice en voz alta: igual a `texto`, salvo que el mensaje haya
    # entrado por voz y lo haya escrito el modelo — ahí, hasta 3 frases.
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


class MotorDePensar(BaseModel):
    id: str
    label: str
    disponible: bool
    detalle: str


@app.get("/pensar/motores", response_model=list[MotorDePensar])
def listar_motores() -> list[MotorDePensar]:
    """Lo que el dropdown de la ventanita puede elegir, y qué le falta a cada uno."""
    return [
        MotorDePensar(id=m.id, label=m.label, disponible=m.disponible, detalle=m.detalle)
        for m in pensar.motores_disponibles()
    ]


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
    """Lo que decís no siempre es una tarea. El clasificador (sin IA) decide
    si enfría en la Bandeja, si abre un bloque o si cierra el que estaba."""
    arranque = time.perf_counter()
    if mensaje.modo == "prompt":
        respuesta = _armar_encargo(mensaje)
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=encargo ms={ms:.0f} pensó={'sí' if respuesta.tokens else 'no'}", file=sys.stderr, flush=True)
        return respuesta
    tipo = clasificar.clasificar(mensaje.texto)
    # «buscá…» se contesta (con la web), no se guarda en la Bandeja.
    if clasificar.pide_busqueda(mensaje.texto):
        tipo = "pregunta"

    if tipo == "idea":
        respuesta = _guardar_idea(mensaje)
    elif tipo == "pregunta":
        respuesta = _contestar(mensaje)
    elif tipo == "hecha":
        respuesta = _cerrar_lo_abierto()
    else:
        respuesta = _abrir_bloque(mensaje)

    # Una línea por mensaje, para poder cruzarla con el log de la ventanita:
    # qué tipo salió, cuánto tardó y si se gastó un token.
    ms = (time.perf_counter() - arranque) * 1000
    penso = "sí" if respuesta.tokens else ("pedido" if mensaje.think else "no")
    print(
        f"[mensaje] tipo={tipo} ms={ms:.0f} pensó={penso} "
        f"palabras={len(mensaje.texto.split())}",
        file=sys.stderr,
        flush=True,
    )
    return respuesta


def _guardar_idea(mensaje: MensajeEntrante) -> RespuestaMensaje:
    """Ley 6: enfría 48 h en la Bandeja. No crea tarea ni sesión — si cada
    cosa suelta abriera un bloque, la ley 1 mediría cualquier cosa."""
    ahora = datetime.now(timezone.utc)
    idea = Idea(
        id=uuid4(),
        texto=mensaje.texto,
        origen=mensaje.origen,
        creada_en=ahora,
        enfria_hasta=ahora + timedelta(hours=HORAS_DE_ENFRIAMIENTO),
        estado="enfriando",
        problema_vision=None,
    )
    conexion = db.conectar()
    try:
        db.crear_idea(conexion, idea)
    finally:
        conexion.close()

    # El tipo ya está decidido (idea, y se guardó): pensar solo cambia lo que
    # Remi CONTESTA. En diálogo, «Guardada. La miramos en dos días.» a todo
    # lo que digas no es una conversación.
    pensado = pensar.pensar(mensaje.texto, mensaje.motor, mensaje.modo, nivel=mensaje.nivel, modelo_ollama=mensaje.modelo_ollama) if mensaje.think else None
    if pensado is None:
        return _respuesta_fija("idea", "Guardada. La miramos en dos días.")
    return RespuestaMensaje(
        tipo="idea",
        texto=pensado.paso_minimo,
        voz=_voz_de(pensado.paso_minimo, mensaje),
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
    )


def _armar_encargo(mensaje: MensajeEntrante) -> RespuestaMensaje:
    """Modo Prompt: lo dicho vuelve ordenado como un encargo de UNA tarea
    para Claude Code. No se clasifica ni se guarda en la Bandeja: es un
    texto para copiar. Lo arma Sonnet con nucleo/prompts/encargo.md y los
    libros del proyecto que toque."""
    if not mensaje.think:
        return RespuestaMensaje(
            tipo="encargo", texto="Sin pensar no puedo armar el encargo.", voz="Sin pensar no puedo armar el encargo."
        )
    pensado = pensar.pensar(mensaje.texto, mensaje.motor, "equilibrio", pensar.sistema_encargo())
    if pensado is None:
        return RespuestaMensaje(
            tipo="encargo", texto="No pude armar el encargo. Probá de nuevo.", voz="No pude armar el encargo."
        )
    return RespuestaMensaje(
        tipo="encargo",
        texto=pensado.paso_minimo,
        # Un encargo no se lee en voz alta: se copia.
        voz="Listo, lo tenés para copiar.",
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
    )


def _contestar(mensaje: MensajeEntrante) -> RespuestaMensaje:
    """Una pregunta se contesta y no deja nada: ni idea en la Bandeja, ni
    tarea, ni sesión. Sin modelo no hay con qué contestar, y se dice."""
    buscar = clasificar.pide_busqueda(mensaje.texto)
    pensado = (
        pensar.pensar(mensaje.texto, mensaje.motor, mensaje.modo, nivel=mensaje.nivel, buscar=buscar, modelo_ollama=mensaje.modelo_ollama)
        if mensaje.think
        else None
    )
    if pensado is None:
        return _respuesta_fija("pregunta", "Sin pensar no puedo contestarte eso. No guardé nada.")
    return RespuestaMensaje(
        tipo="pregunta",
        texto=pensado.paso_minimo,
        voz=_voz_de(pensado.paso_minimo, mensaje),
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
    )


def _voz_de(respuesta: str, mensaje: MensajeEntrante) -> str:
    """Si va a sonar (entró por voz), hasta 3 frases; si no, entera. Sin
    markdown en los dos casos: por texto también se puede leer en voz alta
    con el botón."""
    return para_hablar(respuesta) if mensaje.origen == "voz" else sin_markdown(respuesta)


def _respuesta_fija(tipo: clasificar.TipoMensaje, frase: str, **campos: object) -> RespuestaMensaje:
    """Las frases de Remi sin modelo: se ven y se dicen igual."""
    return RespuestaMensaje(tipo=tipo, texto=frase, voz=frase, **campos)  # type: ignore[arg-type]


def _cerrar_lo_abierto() -> RespuestaMensaje:
    """Cierra el bloque abierto más reciente y marca su tarea `hecha`. Es
    idempotente: cerrar dos veces no altera nada, y sin nada abierto lo dice
    sin regañar (ley 3)."""
    conexion = db.conectar()
    try:
        abierta = db.sesion_abierta_mas_reciente(conexion)
        if abierta is None:
            return _respuesta_fija("hecha", "No había nada abierto.")

        sesion = db.cerrar_sesion(conexion, abierta)
        if sesion is None:
            return _respuesta_fija("hecha", "No había nada abierto.")

        tarea = db.actualizar_estado_tarea(conexion, sesion.tarea_id, "hecha")
        return _respuesta_fija(
            "hecha", f"Cerrada. {formatear_duracion(sesion.real_min)}.", tarea=tarea, sesion=sesion
        )
    finally:
        conexion.close()


def _abrir_bloque(mensaje: MensajeEntrante) -> RespuestaMensaje:
    # Si pensó, lo que Remi contesta es lo que escribió el modelo. El
    # paso_minimo de la tarea nace universal igual: la respuesta de una
    # conversación no es un paso mínimo. Sin modelo, la frase de siempre.
    pensado = pensar.pensar(mensaje.texto, mensaje.motor, mensaje.modo, nivel=mensaje.nivel, modelo_ollama=mensaje.modelo_ollama) if mensaje.think else None
    paso_minimo = PASO_MINIMO_INICIAL
    texto = pensado.paso_minimo if pensado else frase_remi(mensaje.texto)
    voz = _voz_de(texto, mensaje) if pensado else texto
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
        # la misma tarea. Hoy esto siempre crea una tarea nueva (id recién
        # generado), así que es un no-op — pero si llega a referenciar una
        # tarea existente, ya queda a salvo.
        abierta = db.sesion_abierta_de_tarea(conexion, tarea.id)
        if abierta is not None:
            db.cerrar_sesion(conexion, abierta)
        db.crear_sesion(conexion, sesion)
    finally:
        conexion.close()

    return RespuestaMensaje(tipo="hoy", tarea=tarea, sesion=sesion, texto=texto, voz=voz, tokens=tokens)


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


# — El chat de la ventanita (3c) —


class TurnoVisible(BaseModel):
    rol: Literal["juan", "remi"]
    texto: str
    fecha: datetime


@app.get("/conversacion", response_model=list[TurnoVisible])
def conversacion_actual() -> list[TurnoVisible]:
    """Los turnos de la conversación vigente (la de la última hora), para
    que la ventanita muestre el chat al abrirse."""
    conexion = db.conectar()
    try:
        vigente = db.conversacion_vigente(conexion, datetime.now(timezone.utc))
        if vigente is None:
            return []
        return [
            TurnoVisible(rol="juan" if t.rol == "juan" else "remi", texto=t.texto, fecha=t.fecha)
            for t in db.turnos_de(conexion, vigente.id)
        ]
    finally:
        conexion.close()


@app.get("/pensar/ollama", response_model=list[str])
def modelos_ollama() -> list[str]:
    """Los modelos que tiene Ollama de verdad (`ollama list`)."""
    return pensar.modelos_de_ollama()


class PedidoEpisodio(BaseModel):
    texto: str = Field(min_length=episodios.LARGO_MINIMO)


class EpisodioGuardado(BaseModel):
    titulo: str
    tema: str
    resumen: str
    archivo: str
    resumido_por: str


@app.post("/episodio", response_model=EpisodioGuardado, status_code=201)
def guardar_episodio(pedido: PedidoEpisodio) -> EpisodioGuardado:
    """Una charla pegada, resumida y guardada en la bóveda y en memoria."""
    episodio = episodios.guardar(pedido.texto, datetime.now(timezone.utc))
    return EpisodioGuardado(
        titulo=episodio.titulo,
        tema=episodio.tema,
        resumen=episodio.resumen,
        archivo=episodio.ruta.name,
        resumido_por=episodio.resumido_por,
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
            claves=None,
            nivel=None,
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


class UltimaVez(BaseModel):
    # None mientras no se haya cerrado ningún bloque: la ley 1 no inventa.
    minutos: int | None


@app.get("/ultima-vez", response_model=UltimaVez)
def ultima_vez() -> UltimaVez:
    """Cuánto tardó el último bloque que se cerró. Lo usa el reposo de la
    ventanita: con algo medido para mostrar, vale más que «hace N min»."""
    conexion = db.conectar()
    try:
        sesion = db.ultima_sesion_cerrada(conexion)
        return UltimaVez(minutos=sesion.real_min if sesion else None)
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
    import uvicorn

    uvicorn.run(app, host=HOST, port=PUERTO)

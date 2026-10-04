"""FastAPI local. El bind en 127.0.0.1 no protege del origen: por acá no pueden
salir pacientes, finanzas ni salud — eso lo hace la regla de compartible=true
en los espejos, no este servidor."""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

import agenda
import aldia
import avisos
import bandeja
import boveda_git
import caminos
import cierre
import clasificar
import cobros
import gastos
import conexiones
import correcciones
import db
import entregas
import episodios
import estado_libro
import experiencia
import ficha
import gasto
import hilos
import iniciativa
import libros
import mensaje_cliente
import notion
import pensar
import plata
import precarga
import rumbo
import preguntas
import semana
import sembrar_conocimiento
import telegram
import temas
import trabajo
import tts
from modelos import Entrega, Idea, Memoria, Nudge, Pregunta, Sesion, Tarea

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "nucleo.json"
CONFIG = json.loads(RUTA_CONFIG.read_text())
HOST = CONFIG["host"]
PUERTO = CONFIG["puerto"]

# F4.2b (plan de cierre): el 2/10/2026 un núcleo de prueba con la base en una
# copia (REMI_DB_PATH) escribió episodios y Estados en la bóveda REAL — la
# base estaba aislada, la bóveda no. Un núcleo con la base fuera de la de
# siempre es un núcleo de prueba, y entonces la bóveda tiene que estar
# aislada también: si no, no arranca.
BOVEDA_REAL = (Path(__file__).resolve().parent.parent / "conocimiento").resolve()
MENSAJE_PRUEBA_CONTRA_BOVEDA_REAL = "núcleo de prueba apuntando a la bóveda real"


def _dentro_de_la_boveda_real(valor: str | None, boveda_real: Path) -> bool:
    if not valor:
        return True  # sin la variable, se usa la bóveda real
    ruta = Path(valor).expanduser().resolve()
    return ruta == boveda_real or boveda_real in ruta.parents


def problema_de_aislamiento(entorno: dict[str, str], boveda_real: Path = BOVEDA_REAL) -> str | None:
    """None si está bien; si no, el mensaje de por qué el núcleo no arranca."""
    base = entorno.get("REMI_DB_PATH")
    if not base or Path(base).expanduser().resolve() == db.RUTA_DB_POR_DEFECTO.resolve():
        return None  # el núcleo de verdad, con su base de siempre
    malas = [
        nombre
        for nombre in ("REMI_CONOCIMIENTO", "REMI_BOVEDA")
        if _dentro_de_la_boveda_real(entorno.get(nombre), boveda_real)
    ]
    if not malas:
        return None
    return (
        f"{MENSAJE_PRUEBA_CONTRA_BOVEDA_REAL}: REMI_DB_PATH={base} es una base de prueba, "
        f"pero {' y '.join(malas)} {'no está puesta o apunta' if len(malas) == 1 else 'no están puestas o apuntan'} "
        f"a {boveda_real}. Pon una copia temporal de la bóveda en REMI_CONOCIMIENTO "
        "(…/proyectos) y REMI_BOVEDA (su carpeta de arriba)."
    )


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
    """Cargar el modelo de voz tarda ~18 s la primera vez: si esperáramos a
    la primera frase, Remi contestaría con la voz del sistema mientras
    tanto. Va en un hilo al arrancar el servidor, no en `__main__`, porque
    launchd levanta `uvicorn servidor:app` y ahí `__main__` nunca corre.
    Importar el módulo sigue sin cargar nada: esto es del ciclo de vida de
    la app, no del import (REMI_TTS_PRECALENTAR=0 lo apaga)."""
    problema = problema_de_aislamiento(dict(os.environ))
    if problema is not None:
        print(f"[núcleo] NO ARRANCO: {problema}", file=sys.stderr, flush=True)
        raise RuntimeError(problema)
    if os.environ.get("REMI_TTS_PRECALENTAR", "1") != "0":
        threading.Thread(target=tts.precalentar, daemon=True).start()
    # Las fichas de proyecto al estante, al arrancar: así el índice tiene
    # una línea por proyecto. Si falla, el núcleo arranca igual.
    if os.environ.get("REMI_SEMBRAR_CONOCIMIENTO", "1") != "0":
        try:
            sembrar_conocimiento.sembrar()
        except Exception as error:  # nunca tumbar el arranque por esto
            print(f"[conocimiento] no pude sembrar ({type(error).__name__}: {error})", file=sys.stderr)
        try:
            sembrar_conocimiento.sembrar_oficios()
        except Exception as error:  # nunca tumbar el arranque por esto
            print(f"[oficios] no pude sembrar ({type(error).__name__}: {error})", file=sys.stderr)
        try:
            sembrar_conocimiento.sembrar_referencias()
        except Exception as error:  # nunca tumbar el arranque por esto
            print(f"[referencia] no pude sembrar ({type(error).__name__}: {error})", file=sys.stderr)
    telegram.arrancar_hilo()
    yield


app = FastAPI(title="Remi — núcleo", lifespan=ciclo_de_vida)

# Orígenes reales del webview de la ventanita (Tauri 2, macOS): el devUrl de
# tauri.conf.json en desarrollo, y el esquema tauri:// en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420", "http://localhost:4402", "http://127.0.0.1:4402"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(entregas.router)
app.include_router(entregas.router_cobros)
app.include_router(experiencia.router)
app.include_router(notion.router)
app.include_router(plata.router)
app.include_router(rumbo.router)
app.include_router(semana.router)
app.include_router(telegram.router)

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


def hoy_en_bogota(ahora: datetime | None = None) -> date:
    """El día de Juan Camilo: «hoy» y «mañana» se cortan a medianoche de
    Bogotá, no de UTC (el mismo corte que usan plata.py e iniciativa.py)."""
    return (ahora or datetime.now(timezone.utc)).astimezone(plata.BOGOTA).date()


def _dia_de(fecha: datetime) -> date:
    """El día al que apunta una fecha guardada: las fechas de tareas y
    entregas se guardan a las 00:00 UTC del día que nombran (ver
    entregas.parsear_entrega), así que el día es el de su parte de fecha."""
    return fecha.date()


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
    motor: Literal["claude", "venice", "groq", "openrouter", "ollama"] | None = None
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
    # Con Venice, GLM Flash o Grok 4.7. None = el del .env. Otro id se ignora.
    modelo_venice: str | None = None
    # Cómo entró: por voz o escrito. Lo guarda la Idea (contrato).
    origen: Literal["voz", "texto"] = "texto"
    # Por dónde llegó (3-oct): una pregunta «en el aire» solo la contesta un
    # mensaje del mismo canal por el que salió.
    canal: Literal["ventanita", "telegram"] = "ventanita"


class TokensClaude(BaseModel):
    entrada: int
    salida: int
    modelo: str


class RespuestaMensaje(BaseModel):
    # Lo decide el clasificador, nunca el modelo: pensar solo reformula la
    # voz. Una idea no crea tarea ni sesión, y un cierre no crea nada.
    # «encargo» es el modo Prompt, que no pasa por el clasificador.
    # Forma G (T2): «agenda» (una fecha/hora reconocida sin abrir bloque),
    # «cobro» (un pago que llegó hablado) y «entrega» (una entrega futura
    # que llegó hablada) — ninguno de los tres abre bloque ni lleva
    # `sesion`; la ventanita solo muestra la voz.
    # «pregunta_respondida» (T3, fase Q): la respuesta a una pregunta de
    # Remi que estaba «en el aire» — fuera de Forma G, solo lo lee la
    # ventanita (el panel no llama a /mensaje).
    tipo: clasificar.TipoMensaje | Literal[
        "encargo", "cliente", "correccion", "agenda", "cobro", "entrega", "pregunta_respondida",
        "leccion", "conversacion_nueva", "hito_cerrado", "gasto",
    ]
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
    # El motor que de verdad contestó ("claude", "venice", "deepseek",
    # "ollama", o el proveedor de la trastienda/respaldo de charla): a
    # diferencia de `tokens`, esto SÍ es para la pantalla — el chip de la
    # ventanita. None si no pensó.
    motor_usado: str | None = None


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


class EventoEntrante(BaseModel):
    # B2.1: "pruebas" es una corrida de la suite (verde o roja) — entra como
    # cualquier otro evento, sin un side-effect propio (trabajo.recibir ya
    # inserta en trabajo_eventos para cualquier tipo).
    tipo: Literal["commit", "sesion_inicio", "sesion_fin", "pruebas"]
    ruta: str
    datos: dict[str, object] = Field(default_factory=dict)


class RespuestaEvento(BaseModel):
    proyecto: str | None
    anotado: bool
    # Solo al abrir una sesión: dónde quedó, decisiones, próximo paso.
    contexto: str | None = None


@app.post("/evento", response_model=RespuestaEvento)
def recibir_evento(evento: EventoEntrante) -> RespuestaEvento:
    """Un commit o una sesión, desde un hook. Si la carpeta no tiene libro,
    queda en la Bandeja como proyecto sin ficha. No depende de una palabra clave."""
    hecho = trabajo.recibir(evento.tipo, evento.ruta, evento.datos)
    contexto = hecho.get("contexto")
    return RespuestaEvento(
        proyecto=hecho["proyecto"],  # type: ignore[arg-type]
        anotado=bool(hecho["anotado"]),
        contexto=contexto if isinstance(contexto, str) and contexto.strip() else None,
    )


class DondeQuede(BaseModel):
    lineas: list[str]


@app.get("/donde-quede", response_model=DondeQuede)
def abrir_donde_quede() -> DondeQuede:
    """Al abrir la ventanita, si hay un proyecto activo. Si no, silencio."""
    return DondeQuede(lineas=trabajo.lineas_donde_quede())


# V3 (2/10/2026): quien quiera oír la respuesta a medida que sale pasa un
# emisor; recibe cada frase completa en cuanto el motor la termina.
Emisor = Callable[[str], None]


@app.post("/mensaje", response_model=RespuestaMensaje)
def recibir_mensaje(mensaje: MensajeEntrante) -> RespuestaMensaje:
    """Lo que decís no siempre es una tarea. El clasificador (sin IA) decide
    si enfría en la Bandeja, si abre un bloque o si cierra el que estaba."""
    return _atender(mensaje, None)


@app.post("/mensaje/stream")
def recibir_mensaje_en_vivo(mensaje: MensajeEntrante) -> StreamingResponse:
    """La misma respuesta que POST /mensaje, pero en NDJSON y a medida que
    el motor la escribe: una línea `{"frase": …, "voz": …}` por oración
    completa (`voz` es la frase lista para decirse, solo en las primeras
    MAX_FRASES_HABLADAS, como para_hablar; después, null) y al final
    `{"fin": …}` con la respuesta entera, igual que la de /mensaje. Si algo
    revienta a mitad, la conexión se cierra sin `fin`: la ventanita vuelve
    a pedir /mensaje normal, sin decir nada."""
    cola: queue.Queue[str | None] = queue.Queue()

    def correr() -> None:
        dichas = 0

        def emisor(frase: str) -> None:
            nonlocal dichas
            voz = sin_markdown(frase) if dichas < MAX_FRASES_HABLADAS else None
            dichas += 1
            cola.put(json.dumps({"frase": frase, "voz": voz}, ensure_ascii=False) + "\n")

        try:
            respuesta = _atender(mensaje, emisor)
            cola.put(json.dumps({"fin": respuesta.model_dump(mode="json")}, ensure_ascii=False) + "\n")
        except Exception as error:  # noqa: BLE001 — se cierra sin `fin` y la ventanita cae a /mensaje
            print(
                f"[mensaje/stream] falló a mitad ({type(error).__name__}: {error}): la ventanita cae a /mensaje",
                file=sys.stderr,
                flush=True,
            )
        finally:
            cola.put(None)

    threading.Thread(target=correr, daemon=True).start()

    def lineas() -> Iterator[str]:
        while True:
            linea = cola.get()
            if linea is None:
                return
            yield linea

    return StreamingResponse(lineas(), media_type="application/x-ndjson")


def _pensado(mensaje: MensajeEntrante, emisor: Emisor | None, **extra: Any) -> pensar.Pensado | None:
    """pensar() con lo que pide el mensaje. Con emisor, en frases y en vivo."""
    comunes: dict[str, Any] = dict(nivel=mensaje.nivel, modelo_ollama=mensaje.modelo_ollama, modelo_venice=mensaje.modelo_venice)
    if emisor is None:
        return pensar.pensar(mensaje.texto, mensaje.motor, mensaje.modo, **comunes, **extra)
    frases = pensar.pensar_en_frases(mensaje.texto, mensaje.motor, mensaje.modo, **comunes, **extra, en_vivo=True)
    try:
        while True:
            emisor(next(frases))
    except StopIteration as fin:
        pensado: pensar.Pensado | None = fin.value
        return pensado


def _atender(mensaje: MensajeEntrante, emisor: Emisor | None) -> RespuestaMensaje:
    arranque = time.perf_counter()
    if mensaje.modo == "prompt":
        respuesta = _armar_encargo(mensaje)
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=encargo ms={ms:.0f} pensó={'sí' if respuesta.tokens else 'no'}", file=sys.stderr, flush=True)
        return respuesta
    if clasificar.pide_conversacion_nueva(mensaje.texto):
        # Sin IA: la vigente se cierra (deja su episodio) y la siguiente frase
        # abre otra. Remi lo dice solo cuando lo hizo.
        conexion = db.conectar()
        try:
            db.cerrar_conversacion_vigente(conexion, datetime.now(timezone.utc))
        finally:
            conexion.close()
        voz = "Listo, conversación nueva. ¿Qué hay?"
        print("[mensaje] tipo=conversacion_nueva", file=sys.stderr, flush=True)
        return RespuestaMensaje(tipo="conversacion_nueva", texto=voz, voz=voz)
    ahora_correccion = datetime.now(timezone.utc)
    aplicada = correcciones.revisar_confirmacion(mensaje.texto, ahora_correccion)
    if aplicada is not None:
        oficio, regla = aplicada
        respuesta = RespuestaMensaje(
            tipo="correccion",
            texto=f"Guardado en el oficio «{oficio}»: {regla}",
            voz="Guardado, gracias.",
        )
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=correccion ms={ms:.0f} accion=guardada oficio={oficio}", file=sys.stderr, flush=True)
        return respuesta
    propuesta = correcciones.proponer(mensaje.texto, ahora_correccion)
    if propuesta is not None:
        oficio, regla = propuesta
        respuesta = RespuestaMensaje(
            tipo="correccion",
            texto=f"¿Guardo esto en el oficio «{oficio}»?\n«{regla}»",
            voz="¿Guardo esta regla?",
        )
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=correccion ms={ms:.0f} accion=propuesta oficio={oficio}", file=sys.stderr, flush=True)
        return respuesta
    if clasificar.es_texto_de_cliente(mensaje.texto):
        # No pasa por el clasificador de tareas/ideas: es una lectura para
        # decidir, no algo que Juan Camilo pidió hacer (Biblia Parte VI).
        respuesta = _leer_cliente(mensaje)
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=cliente ms={ms:.0f} pensó={'sí' if respuesta.tokens else 'no'}", file=sys.stderr, flush=True)
        return respuesta
    respuesta_leccion = _anotar_leccion_hablada(mensaje)
    if respuesta_leccion is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=leccion ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_leccion
    respuesta_pregunta = _responder_pregunta_en_el_aire(mensaje)
    if respuesta_pregunta is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=pregunta_respondida ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_pregunta
    # T2: plata y agenda por voz. Van antes del clasificador de
    # tareas/ideas porque son formas más específicas; ninguna abre bloque.
    respuesta_entrega = _crear_entrega_hablada(mensaje)
    if respuesta_entrega is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=entrega ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_entrega
    respuesta_cobro = _registrar_cobro(mensaje)
    if respuesta_cobro is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=cobro ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_cobro
    respuesta_gasto = _registrar_gasto_hablado(mensaje)
    if respuesta_gasto is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=gasto ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_gasto
    respuesta_hito = _cerrar_por_mensaje(mensaje)
    if respuesta_hito is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=hito_cerrado ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_hito
    respuesta_agenda = _crear_agenda_hablada(mensaje)
    if respuesta_agenda is not None:
        ms = (time.perf_counter() - arranque) * 1000
        print(f"[mensaje] tipo=agenda ms={ms:.0f}", file=sys.stderr, flush=True)
        return respuesta_agenda
    tipo = clasificar.clasificar(mensaje.texto)
    # «buscá…» se contesta (con la web), no se guarda en la Bandeja.
    if (
        clasificar.pide_busqueda(mensaje.texto)
        or trabajo.es_donde_quede(mensaje.texto)
        or trabajo.es_cuanto(mensaje.texto)
        or trabajo.es_que_falta(mensaje.texto)
    ):
        tipo = "pregunta"

    # T11.1: «Gracias.» no abre idea, ni nada de cortesía o de menos de
    # tres palabras. Mientras se charla con Remi (conversación vigente),
    # tampoco — lo suelto de una charla no es lo mismo que una idea suelta
    # de la Bandeja; la única puerta ahí es «anotá esto: …».
    contenido_explicito = clasificar.contenido_anota_esto(mensaje.texto)
    if tipo == "idea" and contenido_explicito is None:
        if clasificar.es_cortesia_o_muy_corta(mensaje.texto) or _hay_conversacion_vigente():
            tipo = "pregunta"

    # B7: el hilo del tema al que se vuelve, antes de que esta charla deje
    # su propio rastro para EL SIGUIENTE salto.
    conexion_hilo = db.conectar()
    try:
        hilo_pendiente = hilos.rastrear(conexion_hilo, mensaje.texto, datetime.now(timezone.utc))
    finally:
        conexion_hilo.close()

    if tipo == "idea":
        respuesta = _guardar_idea(mensaje, texto_idea=contenido_explicito, emisor=emisor)
    elif tipo == "pregunta":
        respuesta = _contestar(mensaje, emisor)
    elif tipo == "hecha":
        respuesta = _cerrar_lo_abierto()
    else:
        respuesta = _abrir_bloque(mensaje)

    if hilo_pendiente is not None:
        tema_de_vuelta = temas.tema_de_texto(mensaje.texto)
        if tema_de_vuelta is not None:
            anuncio = hilos.voz_del_hilo(tema_de_vuelta, hilo_pendiente)
            respuesta = respuesta.model_copy(update={
                "texto": f"{anuncio}. {respuesta.texto}",
                "voz": f"{anuncio}. {respuesta.voz}" if respuesta.voz else anuncio,
            })

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


def _anotar_leccion_hablada(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """T8.7: «anota esta lección: …» en la charla hace lo mismo que
    `anotar_leccion` del MCP. Solo la clase «error» por este camino —
    un acierto se anota con el MCP o `POST /experiencia` directamente."""
    contenido = clasificar.contenido_anotar_leccion(mensaje.texto)
    if contenido is None:
        return None
    tema = temas.tema_de_texto(contenido)
    libro = next((l for l in libros.listar() if l.tema == tema), None) if tema else None
    titulo_libro = libro.titulo if libro else (tema or "general")
    secciones = cierre.redactar_error(contenido, titulo_libro)
    if secciones is None:
        texto = "No saqué nada claro de ahí. Cuéntame el síntoma, la causa y la cura."
        return RespuestaMensaje(tipo="leccion", texto=texto, voz=texto)
    leccion = experiencia.Leccion(
        titulo=episodios._recortar(f"{titulo_libro}: {episodios._una_linea(secciones['Síntoma'])}", 80),
        tema=tema or "general",
        resumen=episodios._recortar(episodios._una_linea(secciones["Causa real"]), 240),
        clase="error",
        donde=tema or "general",
        secciones=secciones,
        fuente="remi",
    )
    try:
        _destino, es_nueva = experiencia.escribir(leccion)
    except ValueError:
        texto = "No pude anotarla: faltó algo clave en lo que contaste."
        return RespuestaMensaje(tipo="leccion", texto=texto, voz=texto)
    texto = "Anotada." if es_nueva else "Ya tenía una lección igual — le sumé una vuelta más."
    return RespuestaMensaje(tipo="leccion", texto=texto, voz=texto)


def _responder_pregunta_en_el_aire(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """T3.5: si hay una pregunta de Remi «en el aire», el mensaje siguiente
    que no sea arranque, cierre ni pregunta es la respuesta (el patrón de
    correcciones.py). None si no hay ninguna en el aire, o si este mensaje
    sí es arranque/cierre/pregunta — ahí se deja pendiente y sigue su
    camino normal."""
    conexion = db.conectar()
    try:
        pregunta = preguntas.en_el_aire(conexion, datetime.now(timezone.utc), mensaje.canal)
        if pregunta is None or preguntas.es_arranque_cierre_o_pregunta(mensaje.texto):
            return None
        entendida = preguntas.responder(conexion, pregunta, mensaje.texto)
        if not entendida:
            return RespuestaMensaje(tipo="pregunta_respondida", texto=f"No te entendí. {pregunta.voz}", voz=f"No te entendí. {pregunta.voz}")
        db.actualizar_estado_pregunta(conexion, pregunta.id, "respondida")
        preguntas.borrar_en_el_aire(conexion)
        # Qué guardó y dónde (3-oct): un «Anotado, gracias.» a secas escondía
        # que una frase cualquiera había quedado como el cliente de BeaM.
        libro = next((l for l in libros.listar() if l.tema == pregunta.tema), None)
        donde = libro.titulo.split(" —")[0] if libro else pregunta.tema
        voz = f"Anotado en {donde}: «{recortar_voz(mensaje.texto.strip())}»."
        return RespuestaMensaje(tipo="pregunta_respondida", texto=voz, voz=voz)
    finally:
        conexion.close()


def _crear_entrega_hablada(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """T2.3: «entrega para Alfonso el 18 de octubre por 5.000» — reglas
    (entregas.parsear_entrega), nunca IA. None si el texto no tiene esa
    forma: sigue el camino normal (Bandeja, bloque, etc)."""
    if entregas.parsear_entrega(mensaje.texto) is None:
        return None
    tema = temas.tema_de_texto(mensaje.texto)
    entrega = entregas.crear_desde_texto(entregas.CrearEntregaDesdeTexto(texto=mensaje.texto, tema=tema))
    voz = f"Anotada: entrega de {entrega.cliente} por {entrega.monto:.0f} el {entrega.fecha.strftime('%d/%m')}."
    return RespuestaMensaje(tipo="entrega", texto=voz, voz=voz)


def _cerrar_por_mensaje(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """B3.1: «ya le mandé el avance a Alfonso» cierra el hito de ESE
    cliente cuyo cierra_con es "mensaje". None si no nombra a un cliente
    conocido o ese libro no tiene un hito abierto de esa clase: sigue el
    camino normal (cae como idea, como cualquier frase suelta)."""
    libro = mensaje_cliente.libro_nombrado(mensaje.texto)
    if libro is None:
        return None
    conexion = db.conectar()
    try:
        n = caminos.cerrar_primer_hito_con(conexion, libro.tema, "mensaje")
        if n is None:
            return None
        db.marcar_hito_cerrado(conexion, libro.tema, n, "mensaje", mensaje.texto[:200], datetime.now(timezone.utc))
    finally:
        conexion.close()
    voz = f"Listo, cerré ese paso de {libro.cliente or libro.titulo}."
    return RespuestaMensaje(tipo="hito_cerrado", texto=voz, voz=voz)


def _registrar_gasto_hablado(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """B6.1: «gasté 40 en el servidor de UpVisuals», «pagué 20 del
    dominio», «la membresía de Claude: 100 al mes». Sin proyecto Y sin
    ser un común claro, no adivina: una Pregunta en el panel."""
    parseada = gastos.parsear(mensaje.texto)
    if parseada is None:
        return None
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        if not parseada.claro:
            # Un nonce al final (no al dedupe por tema+campo): dos gastos
            # hablados iguales ("gasté 15 en el almuerzo" dos veces) son dos
            # transacciones reales, cada una con su propia pregunta — sin
            # esto, la segunda se perdía en silencio (hallazgo de revisión,
            # B6): la pregunta ya existía por la primera y nunca se creaba
            # la segunda, así que ese segundo gasto no quedaba anotado
            # en ningún lado.
            campo = f"gasto::{parseada.monto}::{parseada.concepto}::{ahora.timestamp()}"
            db.crear_pregunta(
                conexion,
                Pregunta(
                    id=uuid4(),
                    tema="_gastos",
                    campo=campo,
                    voz=f"{parseada.concepto} ({parseada.monto:.0f}): ¿de algún proyecto, o común?",
                    estado="pendiente",
                    creada_en=ahora,
                    disponible_desde=ahora,
                ),
            )
            voz = "No sé de qué proyecto es ese gasto. Te pregunto en el panel."
            return RespuestaMensaje(tipo="idea", texto=voz, voz=voz)
        db.crear_gasto(conexion, parseada.tema, parseada.concepto, parseada.monto, ahora)
    finally:
        conexion.close()
    donde = f"de {parseada.tema}" if parseada.tema else "común"
    voz = f"Anotado: {parseada.monto:.0f} en {parseada.concepto} ({donde})."
    return RespuestaMensaje(tipo="gasto", texto=voz, voz=voz)


def _registrar_cobro(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """T2.4: «Alfonso pagó 1.000», «me pagaron 1.500 de UpVisuals». Si no
    se reconoce de quién, no crea nada — queda para que lo pregunte Remi
    (T3), y el mensaje sigue su camino normal (cae como idea)."""
    parseada = cobros.parsear(mensaje.texto)
    if parseada is None or parseada.tema is None:
        return None
    libro = next((l for l in libros.listar() if l.tema == parseada.tema), None)
    if libro is None:
        return None
    proyecto_id = entregas._proyecto_id_de_tema(parseada.tema)
    entrega = Entrega(
        id=uuid4(),
        cliente=libro.cliente or libro.titulo,
        proyecto_id=proyecto_id,
        fecha=datetime.now(timezone.utc),
        monto=parseada.monto,
        estado="pagada",
        linea=plata.linea_de_tema(parseada.tema),
        compartible=True,
    )
    conexion = db.conectar()
    try:
        entregas.crear_entrega(conexion, entrega)
        total = entregas.total_pagado_proyecto(conexion, proyecto_id)
        # B3.1: el cobro mismo es la evidencia de los hitos "Pago antes de
        # arrancar" y "Cobro y cierre" — pero solo si ya no queda otra
        # entrega pendiente de ese proyecto: en cuotas, un primer abono no
        # cierra "el trabajo empieza cuando el pago está completo" (SOP).
        if entregas.entrega_del_proyecto(conexion, proyecto_id) is None:
            n = caminos.cerrar_primer_hito_con(conexion, parseada.tema, "cobro")
            if n is not None:
                db.marcar_hito_cerrado(conexion, parseada.tema, n, "cobro", str(entrega.id), entrega.fecha)
    finally:
        conexion.close()
    n_objetivo = _fase_actual_n(libro.fases)
    fase_objetivo = libro.fases[n_objetivo - 1] if n_objetivo else None
    if fase_objetivo is not None and fase_objetivo.monto:
        voz = f"Anotado: {parseada.monto:.0f} de {entrega.cliente}. Van {total:.0f} de {fase_objetivo.monto:.0f}."
    else:
        voz = f"Anotado: {parseada.monto:.0f} de {entrega.cliente}."
    return RespuestaMensaje(tipo="cobro", texto=voz, voz=voz)


def _crear_agenda_hablada(mensaje: MensajeEntrante) -> RespuestaMensaje | None:
    """T2.5: «mañana llamo al banco», «a las 3 reunión», «vence el 15 de
    octubre…». Crea la tarea como POST /tarea: nunca abre bloque."""
    parseada = agenda.parsear(mensaje.texto, hoy_en_bogota())
    if parseada is None:
        return None
    tarea = planear_tarea(
        TareaPlaneada(titulo=parseada.titulo, hora=parseada.hora, fecha_limite=parseada.fecha_limite)
    )
    voz = f"Anotado: «{tarea.titulo}»" + (f" el {tarea.fecha_limite.strftime('%d/%m')}." if tarea.fecha_limite else ".")
    return RespuestaMensaje(tipo="agenda", tarea=tarea, texto=voz, voz=voz)


def _hay_conversacion_vigente() -> bool:
    """T11.1: si ya se está charlando con Remi, lo suelto no es una idea —
    solo «anota esto: …» lo es."""
    conexion = db.conectar()
    try:
        return db.hay_charla_reciente(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()


def _guardar_idea(
    mensaje: MensajeEntrante, texto_idea: str | None = None, emisor: Emisor | None = None
) -> RespuestaMensaje:
    """Ley 6: enfría 48 h en la Bandeja. No crea tarea ni sesión — si cada
    cosa suelta abriera un bloque, la ley 1 mediría cualquier cosa.

    `texto_idea` es lo que va a la Bandeja cuando no es la frase entera
    (T11.1: «anotá esto: comprar fideos» guarda «comprar fideos», no el
    pedido completo)."""
    texto = texto_idea or mensaje.texto
    ahora = datetime.now(timezone.utc)
    idea = Idea(
        id=uuid4(),
        texto=texto,
        origen=mensaje.origen,
        creada_en=ahora,
        enfria_hasta=ahora + timedelta(hours=HORAS_DE_ENFRIAMIENTO),
        estado="enfriando",
        problema_vision=None,
        # Sin IA: el libro que la frase nombra, o None (una idea suelta).
        tema=temas.tema_de_texto(texto),
    )
    conexion = db.conectar()
    try:
        db.crear_idea(conexion, idea)
    finally:
        conexion.close()

    # El tipo ya está decidido (idea, y se guardó): pensar solo cambia lo que
    # Remi CONTESTA. En diálogo, «Guardada. La miramos en dos días.» a todo
    # lo que digas no es una conversación.
    pensado = _pensado(mensaje, emisor) if mensaje.think else None
    if pensado is None:
        return _respuesta_fija("idea", "Guardada. La miramos en dos días.")
    return RespuestaMensaje(
        tipo="idea",
        texto=pensado.paso_minimo,
        voz=_voz_de(pensado.paso_minimo, mensaje),
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
        motor_usado=pensado.motor_usado,
    )


def _encabezado_de_hito() -> str | None:
    """B3.2: `hito: <tema>#<n>` — nunca lo decide el modelo (inventar el
    número cerraría el hito que no es). Lo calcula el código sobre el
    libro del proyecto activo: solo si tiene un hito abierto y ese hito se
    cierra con evidencia de código (cierra_con == "encargo"). El gancho
    SessionEnd lo lee del primer turno del transcript."""
    tema = trabajo.tema_activo()
    if tema is None:
        return None
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        return None
    conexion = db.conectar()
    try:
        resultado = caminos.hitos_de_tema(conexion, tema)
    finally:
        conexion.close()
    if resultado is None:
        return None
    hitos, siguiente = resultado
    if siguiente is None or caminos.cierra_con_de(libro.tipo, siguiente.texto) != "encargo":
        return None
    n = next((i for i, h in enumerate(hitos, start=1) if h.texto == siguiente.texto), None)
    return f"hito: {tema}#{n}" if n is not None else None


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
            tipo="encargo", texto="No pude armar el encargo. Prueba de nuevo.", voz="No pude armar el encargo."
        )
    encabezado = _encabezado_de_hito()
    texto = f"{encabezado}\n\n{pensado.paso_minimo}" if encabezado else pensado.paso_minimo
    return RespuestaMensaje(
        tipo="encargo",
        texto=texto,
        # Un encargo no se lee en voz alta: se copia.
        voz="Listo, lo tienes para copiar.",
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
        motor_usado=pensado.motor_usado,
    )


def _leer_cliente(mensaje: MensajeEntrante) -> RespuestaMensaje:
    """«Me escribió un cliente» (Biblia Parte VI): lectura, riesgos,
    respuesta recomendada y límites — nunca se guarda en la Bandeja, nunca
    abre un bloque, y Remi no manda nada a ningún lado: es una propuesta
    para que Juan Camilo lea y decida."""
    if not mensaje.think:
        return RespuestaMensaje(
            tipo="cliente", texto="Sin pensar no puedo leer esto.", voz="Sin pensar no puedo leer esto."
        )
    pensado = pensar.pensar(mensaje.texto, mensaje.motor, "equilibrio", pensar.sistema_cliente())
    if pensado is None:
        return RespuestaMensaje(
            tipo="cliente", texto="No pude leer el mensaje. Prueba de nuevo.", voz="No pude leerlo."
        )
    return RespuestaMensaje(
        tipo="cliente",
        texto=pensado.paso_minimo,
        # Igual que un encargo: esto se lee y se copia, no se dice en voz.
        voz="Tienes la lectura lista. La mandas tú.",
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
        motor_usado=pensado.motor_usado,
    )


def _contestar(mensaje: MensajeEntrante, emisor: Emisor | None = None) -> RespuestaMensaje:
    """Una pregunta se contesta y no deja nada: ni idea en la Bandeja, ni
    tarea, ni sesión. Sin modelo no hay con qué contestar, y se dice.
    «¿Dónde quedé?» no gasta un token: sale del Estado del libro."""
    donde = trabajo.donde_quede(mensaje.texto)
    if donde is not None:
        return RespuestaMensaje(tipo="pregunta", texto=donde, voz=_voz_de(donde, mensaje))
    cuanto = trabajo.cuanto_le_meti(mensaje.texto)
    if cuanto is not None:
        return RespuestaMensaje(tipo="pregunta", texto=cuanto, voz=_voz_de(cuanto, mensaje))
    # «¿qué te falta?» ya no se contesta con «Tengo N preguntas pendientes»
    # (3-oct, Juan Camilo: eso no le interesa en el chat): va al modelo como
    # cualquier mensaje. Sigue sin crear una idea (clasificación de arriba).
    buscar = clasificar.pide_busqueda(mensaje.texto)
    pensado = _pensado(mensaje, emisor, buscar=buscar) if mensaje.think else None
    if pensado is None:
        return _respuesta_fija("pregunta", "Sin pensar no puedo contestarte eso. No guardé nada.")
    return RespuestaMensaje(
        tipo="pregunta",
        texto=pensado.paso_minimo,
        voz=_voz_de(pensado.paso_minimo, mensaje),
        tokens=TokensClaude(entrada=pensado.tokens_entrada, salida=pensado.tokens_salida, modelo=pensado.modelo),
        motor_usado=pensado.motor_usado,
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
    pensado = pensar.pensar(mensaje.texto, mensaje.motor, mensaje.modo, nivel=mensaje.nivel, modelo_ollama=mensaje.modelo_ollama, modelo_venice=mensaje.modelo_venice) if mensaje.think else None
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
        hora=None,
        fecha_limite=None,
        compartible=False,
    )
    sesion = Sesion(
        id=uuid4(),
        tarea_id=tarea.id,
        inicio=datetime.now(timezone.utc),
        fin=None,
        real_min=0,
        app_contexto=trabajo.tema_activo(),
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
        # T3.5: al abrir un bloque de un proyecto con algo pendiente, Remi
        # pregunta — una sola, gastando del presupuesto de silencio de
        # iniciativa.py (nunca un Nudge nuevo).
        pregunta = preguntas.preguntar_en_voz(conexion, sesion.app_contexto, datetime.now(timezone.utc))
    finally:
        conexion.close()

    if pregunta is not None:
        texto = f"{texto} {pregunta.voz}".strip()
        voz = f"{voz} {pregunta.voz}".strip()

    return RespuestaMensaje(
        tipo="hoy",
        tarea=tarea,
        sesion=sesion,
        texto=texto,
        voz=voz,
        tokens=tokens,
        motor_usado=pensado.motor_usado if pensado else None,
    )


class BloqueNuevo(BaseModel):
    titulo: str = Field(min_length=1)
    # El libro al que pertenece: queda en `sesion.app_contexto`, que es de
    # donde el panel saca el proyecto, la fase y el hito del bloque.
    tema: str | None = None


class BloqueAbierto(BaseModel):
    tarea: Tarea
    sesion: Sesion


@app.post("/bloque", response_model=BloqueAbierto, status_code=201)
def abrir_bloque_del_panel(cuerpo: BloqueNuevo) -> BloqueAbierto:
    """Abre un bloque desde un botón del panel («Empezar con eso», «Seguir
    con…»). Sin clasificador ni modelo: un botón no hay que interpretarlo.

    Una cosa a la vez: con otro bloque abierto responde 409 y no abre nada.
    Si ya existe una tarea sin cerrar con ese mismo título, el bloque se
    abre sobre ella — así «la última vez» (ley 1) junta todas las veces que
    se trabajó en lo mismo."""
    titulo = cuerpo.titulo.strip()
    if not titulo:
        raise HTTPException(status_code=422, detail="falta el título")
    conexion = db.conectar()
    try:
        abierta = db.sesion_abierta_mas_reciente(conexion)
        tarea = db.tarea_abierta_por_titulo(conexion, titulo)
        if abierta is not None:
            sesiones = db.listar_sesiones_tarea(conexion, tarea.id) if tarea is not None else []
            misma = next((s for s in sesiones if s.id == abierta), None)
            if tarea is not None and misma is not None:
                # Ya estaba abierto ese mismo: tocar el botón dos veces no duplica.
                return BloqueAbierto(tarea=tarea, sesion=misma)
            raise HTTPException(status_code=409, detail="ya hay un bloque abierto")
        if tarea is None:
            tarea = Tarea(
                id=uuid4(),
                titulo=titulo,
                proyecto_id=None,
                estado="hoy",
                paso_minimo=PASO_MINIMO_INICIAL,
                estimado_min=None,
                real_min=None,
                hora=None,
                fecha_limite=None,
                compartible=False,
            )
            db.crear_tarea(conexion, tarea)
        elif tarea.estado != "hoy":
            actualizada = db.actualizar_estado_tarea(conexion, tarea.id, "hoy")
            assert actualizada is not None
            tarea = actualizada
        sesion = Sesion(
            id=uuid4(),
            tarea_id=tarea.id,
            inicio=datetime.now(timezone.utc),
            fin=None,
            real_min=0,
            app_contexto=cuerpo.tema or trabajo.tema_activo(),
        )
        db.crear_sesion(conexion, sesion)
        return BloqueAbierto(tarea=tarea, sesion=sesion)
    finally:
        conexion.close()


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


# «HH:MM» de 24 horas, hora de Bogotá. El panel la muestra como «3:00 p».
PATRON_HORA = r"^([01]\d|2[0-3]):[0-5]\d$"


class TareaPlaneada(BaseModel):
    """Algo que se anota para después, sin abrir un bloque: no hay sesión
    ni reloj hasta que se arranque de verdad (ley 1: solo se mide lo que
    se hizo)."""

    titulo: str = Field(min_length=1)
    hora: str | None = Field(default=None, pattern=PATRON_HORA)
    # El día (YYYY-MM-DD). Se guarda como las fechas de Entrega: 00:00 UTC.
    fecha_limite: date | None = None


class AgendaNueva(BaseModel):
    hora: str | None = Field(default=None, pattern=PATRON_HORA)
    fecha_limite: date | None = None


def _a_medianoche_utc(dia: date | None) -> datetime | None:
    return datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc) if dia else None


@app.post("/tarea", response_model=Tarea, status_code=201)
def planear_tarea(cuerpo: TareaPlaneada) -> Tarea:
    """Anota una tarea con su hora y su día, sin abrir bloque. Con fecha
    futura nace en `camino` y aparece sola en Hoy cuando llega el día; sin
    fecha, o con la de hoy, nace en `hoy`."""
    hoy = hoy_en_bogota()
    tarea = Tarea(
        id=uuid4(),
        titulo=cuerpo.titulo.strip(),
        proyecto_id=None,
        estado="camino" if cuerpo.fecha_limite is not None and cuerpo.fecha_limite > hoy else "hoy",
        paso_minimo=PASO_MINIMO_INICIAL,
        estimado_min=None,
        real_min=None,
        hora=cuerpo.hora,
        fecha_limite=_a_medianoche_utc(cuerpo.fecha_limite),
        compartible=False,
    )
    conexion = db.conectar()
    try:
        db.crear_tarea(conexion, tarea)
    finally:
        conexion.close()
    return tarea


@app.post("/tarea/{tarea_id}/agenda", response_model=Tarea)
def fijar_agenda(tarea_id: UUID, cuerpo: AgendaNueva) -> Tarea:
    """Fija la hora y el día de una tarea que ya existe. Lo que venga en
    null se quita: mandar los dos en null la deja sin agenda."""
    conexion = db.conectar()
    try:
        tarea = db.actualizar_agenda_tarea(conexion, tarea_id, cuerpo.hora, _a_medianoche_utc(cuerpo.fecha_limite))
        if tarea is None:
            raise HTTPException(status_code=404, detail="no existe esa tarea")
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


# — Salud (3e · 4): lo que mira el vigía cada minuto —


class Salud(BaseModel):
    ok: bool
    db: bool


@app.get("/salud", response_model=Salud)
def salud(response: Response) -> Salud:
    """Responde rápido y sin IA. No alcanza con que el proceso conteste: la
    base tiene que abrir. Si no abre, 503 y el vigía lo cuenta como caída."""
    try:
        conexion = db.conectar()
        try:
            conexion.execute("SELECT 1").fetchone()
        finally:
            conexion.close()
    except Exception as error:  # noqa: BLE001 — cualquier falla de la base es «no sano»
        print(f"[salud] la base no abre ({type(error).__name__})", file=sys.stderr, flush=True)
        response.status_code = 503
        return Salud(ok=False, db=False)
    return Salud(ok=True, db=True)


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


class ConversacionDeAntes(BaseModel):
    id: str
    titulo: str
    tema: str | None
    inicio: datetime
    ultimo: datetime
    turnos: int


@app.get("/conversaciones", response_model=list[ConversacionDeAntes])
def conversaciones_de_antes() -> list[ConversacionDeAntes]:
    """El cajón del historial: una sola corriente, la más reciente primero."""
    conexion = db.conectar()
    try:
        return [ConversacionDeAntes(**vars(c)) for c in db.listar_conversaciones(conexion)]
    finally:
        conexion.close()


@app.post("/conversaciones/nueva", status_code=204)
def conversacion_nueva() -> Response:
    """Empezar de cero: la vigente se cierra y el próximo turno abre otra."""
    conexion = db.conectar()
    try:
        db.cerrar_conversacion_vigente(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()
    return Response(status_code=204)


@app.get("/conversaciones/{conversacion_id}", response_model=list[TurnoVisible])
def conversacion_por_id(conversacion_id: str) -> list[TurnoVisible]:
    conexion = db.conectar()
    try:
        if not db.existe_conversacion(conexion, conversacion_id):
            raise HTTPException(status_code=404, detail="Esa conversación no existe.")
        return [
            TurnoVisible(rol="juan" if t.rol == "juan" else "remi", texto=t.texto, fecha=t.fecha)
            for t in db.turnos_de(conexion, conversacion_id)
        ]
    finally:
        conexion.close()


@app.post("/conversaciones/{conversacion_id}/retomar", response_model=list[TurnoVisible])
def retomar_conversacion(conversacion_id: str) -> list[TurnoVisible]:
    """Volver a una de antes: pasa a ser la vigente y se devuelven sus turnos."""
    conexion = db.conectar()
    try:
        if not db.existe_conversacion(conexion, conversacion_id):
            raise HTTPException(status_code=404, detail="Esa conversación no existe.")
        db.retomar_conversacion(conexion, conversacion_id, datetime.now(timezone.utc))
        return [
            TurnoVisible(rol="juan" if t.rol == "juan" else "remi", texto=t.texto, fecha=t.fecha)
            for t in db.turnos_de(conexion, conversacion_id)
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
            tipo=None,
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


# No hay DELETE /memoria/{id}: la Biblia es dura acá («cero acciones destructivas:
# Remi no borra notas, filas ni archivos») y este endpoint, sin UI que lo llame,
# era la única puerta para borrar una fila real. Si algún día hace falta
# retirar una nota, que sea archivarla o marcarla fusionado_en, nunca DELETE
# (revisión R2.38, 3-oct).


@app.get("/hoy", response_model=list[TareaConHistorial])
def listar_hoy() -> list[TareaConHistorial]:
    conexion = db.conectar()
    try:
        tareas = db.listar_tareas_hoy(conexion, hoy_en_bogota())
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


class Vencimiento(BaseModel):
    titulo: str
    fecha: datetime
    monto: float | None
    origen: Literal["tarea", "entrega"]
    # Solo habla de tiempo (ley 3): el día llegó. El panel lo pinta en
    # `alerta`; nunca cuenta cuántos días pasaron.
    vence_hoy: bool


class AgendaDeHoy(BaseModel):
    # Lo de mañana que conviene saber hoy («Mañana asoma: …»).
    manana: list[Tarea]
    # Lo que tiene fecha y sigue abierto: tareas y entregas, lo más cercano
    # primero.
    vence: list[Vencimiento]


MAXIMO_VENCIMIENTOS = 5


class EvidenciaVista(BaseModel):
    tipo: str
    ref: str


class EstamosEnVista(BaseModel):
    tema: str
    fase_n: int
    paso: str


class LoUltimoVista(BaseModel):
    texto: str
    hace_min: int
    evidencia: EvidenciaVista


class SigueVista(BaseModel):
    texto: str
    borrador: str | None


class MientrasNoEstabasVista(BaseModel):
    texto: str
    tema: str | None
    hora: datetime
    evidencia: EvidenciaVista


class AlDiaVista(BaseModel):
    estamos_en: EstamosEnVista | None
    lo_ultimo: LoUltimoVista | None
    sigue: SigueVista | None
    mientras_no_estabas: list[MientrasNoEstabasVista]


def _evidencia_vista(e: aldia.Evidencia) -> EvidenciaVista:
    return EvidenciaVista(tipo=e.tipo, ref=e.ref)


@app.get("/hoy/aldia", response_model=AlDiaVista)
def al_dia() -> AlDiaVista:
    """B2: forma J. Remi no espera que Juan Camilo marque nada — lee los
    eventos que otras piezas ya guardan solas (commits, pruebas, sesiones
    de Claude Code, cobros, decisiones) y arma en qué va."""
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        anterior = aldia.marcar_visto(conexion, ahora)
        forma = aldia.calcular(conexion, ahora, anterior)
        libro_activo = next((l for l in libros.listar() if forma.estamos_en and l.tema == forma.estamos_en.tema), None)
        if (
            forma.sigue is not None
            and forma.sigue.borrador is None
            and forma.estamos_en is not None
            and aldia.avisa_hito(libro_activo.tipo if libro_activo else None, forma.sigue.texto)
        ):
            # Los hechos van explícitos en el pedido: lo que precarga mete
            # en el system prompt (pensar.sistema_cliente()) es del proyecto
            # que esté activo AHORA en la ventanita, que puede no ser este
            # mismo tema. Sin esto, el modelo podía mezclar o inventar una
            # cifra — acá se le da la que hay, o se le dice que no hay.
            entrega = (
                entregas.entrega_del_proyecto(conexion, entregas._proyecto_id_de_tema(forma.estamos_en.tema))
                if libro_activo is not None
                else None
            )
            monto = f"{entrega.monto:.0f}" if entrega is not None and entrega.monto is not None else "sin monto registrado"
            pedido = (
                f"Cliente: {(libro_activo.cliente if libro_activo else None) or forma.estamos_en.tema}. "
                f"Proyecto: {forma.estamos_en.tema}. Paso: «{forma.sigue.texto}». Monto pendiente: {monto}. "
                "Redacta el mensaje breve para este cliente sobre este paso, usando solo estos datos. "
                "Si falta un dato (monto, fecha), no lo inventes: redacta sin esa cifra."
            )
            pensado = pensar.pensar(pedido, None, "equilibrio", pensar.sistema_cliente())
            if pensado is not None:
                aldia.guardar_borrador(conexion, forma.estamos_en.tema, forma.sigue.texto, pensado.paso_minimo)
                forma = replace(forma, sigue=replace(forma.sigue, borrador=pensado.paso_minimo))
    finally:
        conexion.close()
    return AlDiaVista(
        estamos_en=EstamosEnVista(**forma.estamos_en.__dict__) if forma.estamos_en else None,
        lo_ultimo=(
            LoUltimoVista(texto=forma.lo_ultimo.texto, hace_min=forma.lo_ultimo.hace_min, evidencia=_evidencia_vista(forma.lo_ultimo.evidencia))
            if forma.lo_ultimo
            else None
        ),
        sigue=SigueVista(texto=forma.sigue.texto, borrador=forma.sigue.borrador) if forma.sigue else None,
        mientras_no_estabas=[
            MientrasNoEstabasVista(texto=e.texto, tema=e.tema, hora=e.hora, evidencia=_evidencia_vista(e.evidencia))
            for e in forma.mientras_no_estabas
        ],
    )


@app.get("/hoy/agenda", response_model=AgendaDeHoy)
def agenda_de_hoy() -> AgendaDeHoy:
    """Lo que la base sabe de fechas, para la pantalla Hoy. Va aparte de
    GET /hoy para no cambiarle la forma a esa respuesta (la ventanita la
    lee como lista)."""
    hoy = hoy_en_bogota()
    manana = hoy + timedelta(days=1)
    conexion = db.conectar()
    try:
        con_fecha = db.listar_tareas_con_fecha(conexion)
        pendientes = [e for e in entregas.listar_entregas(conexion) if e.estado != "pagada"]
    finally:
        conexion.close()
    vence = [
        Vencimiento(
            titulo=t.titulo, fecha=t.fecha_limite, monto=None, origen="tarea", vence_hoy=_dia_de(t.fecha_limite) <= hoy
        )
        for t in con_fecha
        if t.fecha_limite is not None
    ] + [
        Vencimiento(
            titulo=f"Entrega {e.cliente}", fecha=e.fecha, monto=e.monto, origen="entrega", vence_hoy=_dia_de(e.fecha) <= hoy
        )
        for e in pendientes
    ]
    vence.sort(key=lambda v: v.fecha)
    return AgendaDeHoy(
        manana=[t for t in con_fecha if t.fecha_limite is not None and _dia_de(t.fecha_limite) == manana],
        vence=vence[:MAXIMO_VENCIMIENTOS],
    )


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


# — La Bandeja (Fase 3): revisar en frío lo que enfrió 48 h (ley 6) —


class IdeaBandeja(BaseModel):
    idea: Idea
    fria: bool
    # Forma E (T4): una sola a la vez.
    destacada: bool


class RevisionIdea(BaseModel):
    decision: Literal["soltar", "mantener", "tarea"]


class RevisionHecha(BaseModel):
    idea: Idea
    tarea: Tarea | None = None


# — Forma F (T3, fase Q): Remi pregunta lo que le falta —


class RespuestaPregunta(BaseModel):
    texto: str


class RespuestaAplicada(BaseModel):
    pregunta: Pregunta
    voz: str


@app.get("/preguntas", response_model=list[Pregunta])
def listar_preguntas(tema: str | None = None) -> list[Pregunta]:
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        preguntas.sincronizar(conexion, ahora)
        return db.listar_preguntas_pendientes(conexion, ahora, tema, preguntas.MAXIMO_VISIBLES)
    finally:
        conexion.close()


@app.post("/preguntas/{pregunta_id}/respuesta", response_model=RespuestaAplicada)
def responder_pregunta(pregunta_id: UUID, cuerpo: RespuestaPregunta) -> RespuestaAplicada:
    conexion = db.conectar()
    try:
        pregunta = db.leer_pregunta(conexion, pregunta_id)
        if pregunta is None:
            raise HTTPException(status_code=404, detail="no tengo esa pregunta")
        entendida = preguntas.responder(conexion, pregunta, cuerpo.texto)
        if not entendida:
            return RespuestaAplicada(
                pregunta=pregunta,
                voz=f"No te entendí. {pregunta.voz}",
            )
        actualizada = db.actualizar_estado_pregunta(conexion, pregunta_id, "respondida")
        assert actualizada is not None
        return RespuestaAplicada(pregunta=actualizada, voz="Anotado, gracias.")
    finally:
        conexion.close()


@app.post("/preguntas/{pregunta_id}/despues", response_model=Pregunta)
def posponer_pregunta(pregunta_id: UUID) -> Pregunta:
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        actualizada = db.actualizar_estado_pregunta(
            conexion, pregunta_id, "despues", ahora + timedelta(hours=preguntas.HORAS_DESPUES)
        )
        if actualizada is None:
            raise HTTPException(status_code=404, detail="no tengo esa pregunta")
        return actualizada
    finally:
        conexion.close()


@app.get("/bandeja", response_model=list[IdeaBandeja])
def listar_bandeja() -> list[IdeaBandeja]:
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        destacada_id = bandeja.idea_destacada_id(conexion)
        return [
            IdeaBandeja(idea=_con_tema(idea), fria=fria, destacada=idea.id == destacada_id)
            for idea, fria in bandeja.listar_abiertas(conexion, ahora)
        ]
    finally:
        conexion.close()


class DestacadaNueva(BaseModel):
    destacada: bool


@app.post("/idea/{idea_id}/destacar", response_model=IdeaBandeja)
def destacar_idea(idea_id: UUID, cuerpo: DestacadaNueva) -> IdeaBandeja:
    """Destacar una idea le quita la marca a la anterior — una sola a la
    vez (Forma E)."""
    conexion = db.conectar()
    try:
        idea = bandeja.leer_idea(conexion, idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="no tengo esa idea")
        if cuerpo.destacada:
            bandeja.destacar(conexion, idea_id)
        else:
            bandeja.quitar_destacada(conexion, idea_id)
        ahora = datetime.now(timezone.utc)
        return IdeaBandeja(idea=_con_tema(idea), fria=bandeja.esta_fria(idea, ahora), destacada=cuerpo.destacada)
    finally:
        conexion.close()


def _con_tema(idea: Idea) -> Idea:
    """Las ideas de antes de la v3.7 no tienen tema guardado: se les lee
    con la misma regla, sin escribirles nada (ninguna fila vieja cambia)."""
    if idea.tema is not None:
        return idea
    return idea.model_copy(update={"tema": temas.tema_de_texto(idea.texto)})


class TemaNuevo(BaseModel):
    # None la deja suelta.
    tema: str | None


@app.post("/idea/{idea_id}/tema", response_model=Idea)
def fijar_tema_de_idea(idea_id: UUID, cuerpo: TemaNuevo) -> Idea:
    """Corrige a mano el libro de una idea, cuando la regla no acertó."""
    conexion = db.conectar()
    try:
        idea = db.actualizar_tema_idea(conexion, idea_id, cuerpo.tema.strip() if cuerpo.tema and cuerpo.tema.strip() else None)
        if idea is None:
            raise HTTPException(status_code=404, detail="no tengo esa idea")
        return idea
    finally:
        conexion.close()


@app.post("/idea/{idea_id}/revision", response_model=RevisionHecha)
def revisar_idea(idea_id: UUID, cuerpo: RevisionIdea) -> RevisionHecha:
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        try:
            hecha = bandeja.revisar(conexion, idea_id, cuerpo.decision, ahora)
        except bandeja.IdeaNoEncontrada:
            raise HTTPException(status_code=404, detail="no tengo esa idea") from None
        except bandeja.IdeaNoFria:
            raise HTTPException(status_code=409, detail="todavía no pasaron las 48 h") from None
        return RevisionHecha(idea=hecha.idea, tarea=hecha.tarea)
    finally:
        conexion.close()


# — Nudges (Fase 3): lo que la ventanita ya llama —


class RespuestaNudge(BaseModel):
    respuesta: Literal["listo", "ahora_no"]


@app.get("/nudges/pendiente", response_model=Nudge | None)
def nudge_pendiente() -> Nudge | None:
    conexion = db.conectar()
    try:
        return iniciativa.pendiente_o_nuevo(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()


@app.post("/nudges/{nudge_id}/respuesta", response_model=Nudge)
def responder_nudge(nudge_id: UUID, cuerpo: RespuestaNudge) -> Nudge:
    conexion = db.conectar()
    try:
        nudge = iniciativa.responder(conexion, nudge_id, cuerpo.respuesta, datetime.now(timezone.utc))
        if nudge is None:
            raise HTTPException(status_code=404, detail="no tengo ese nudge")
        return nudge
    finally:
        conexion.close()


# — B5: avisos que jalan la atención (forma L) —


class AvisoVista(BaseModel):
    id: UUID
    tipo: str
    texto: str
    canal: str
    creado: datetime
    respuesta: str | None


def _vista_aviso(a: avisos.Aviso) -> AvisoVista:
    return AvisoVista(id=a.id, tipo=a.tipo, texto=a.texto, canal=a.canal, creado=a.creado, respuesta=a.respuesta)


@app.get("/avisos/hoy", response_model=list[AvisoVista])
def avisos_de_hoy() -> list[AvisoVista]:
    """Solo para el panel — nunca se muestra como contador (ley 4)."""
    conexion = db.conectar()
    try:
        return [_vista_aviso(a) for a in avisos.listar_de_hoy(conexion, datetime.now(timezone.utc))]
    finally:
        conexion.close()


@app.get("/avisos/pendiente", response_model=AvisoVista | None)
def aviso_pendiente() -> AvisoVista | None:
    """Lo que la ventanita muestra: evalúa las reglas de reloj (foco_25,
    desvio) y, si ya había uno sin contestar, ese."""
    conexion = db.conectar()
    try:
        existente = avisos.pendiente(conexion)
        if existente is not None:
            return _vista_aviso(existente)
        nuevo = avisos.evaluar(conexion, datetime.now(timezone.utc))
        return _vista_aviso(nuevo) if nuevo is not None else None
    finally:
        conexion.close()


class RespuestaAviso(BaseModel):
    respuesta: Literal["volver", "ahora_no"]


@app.post("/avisos/{aviso_id}/respuesta", response_model=AvisoVista)
def responder_aviso(aviso_id: UUID, cuerpo: RespuestaAviso) -> AvisoVista:
    conexion = db.conectar()
    try:
        aviso = avisos.responder(conexion, aviso_id, cuerpo.respuesta)
        if aviso is None:
            raise HTTPException(status_code=404, detail="no tengo ese aviso")
        return _vista_aviso(aviso)
    finally:
        conexion.close()


# — Caminos (Fase 3): los hitos del libro de un proyecto —


class HitoVisible(BaseModel):
    texto: str
    hecho: bool


class Camino(BaseModel):
    hitos: list[HitoVisible]
    siguiente: HitoVisible | None


@app.get("/camino/{tema}", response_model=Camino)
def camino_de(tema: str) -> Camino:
    conexion = db.conectar()
    try:
        resultado = caminos.hitos_de_tema(conexion, tema)
        if resultado is None:
            raise HTTPException(status_code=404, detail="no tengo un libro con ese tema")
        hitos, siguiente = resultado
        return Camino(
            hitos=[HitoVisible(texto=h.texto, hecho=h.hecho) for h in hitos],
            siguiente=HitoVisible(texto=siguiente.texto, hecho=siguiente.hecho) if siguiente else None,
        )
    finally:
        conexion.close()


class EntregaCercana(BaseModel):
    cliente: str
    fecha: datetime
    monto: float


class FaseVisible(BaseModel):
    nombre: str
    alcance: str
    monto: float | None
    listo_cuando: str
    estado: str
    # Forma A (T2): lo pagado del proyecto, repartido en cascada.
    cobrado: float
    # B6.2: cuánto se esperaba que tomara. None hasta que se pregunta.
    minutos_estimados: int | None


class CerradoPor(BaseModel):
    tipo: str
    ref: str
    en: datetime


class HitoConDetalle(BaseModel):
    texto: str
    hecho: bool
    # Forma A (T2): la línea del SOP que explica este paso. "" si el hito
    # no es del SOP (uno escrito a mano).
    detalle: str
    # Forma K (B3.4): cómo se cerró solo. None si está abierto, o si se
    # marcó a mano desde antes de B3 (sin fila en hito_cerrado).
    cerrado_por: CerradoPor | None = None


class UltimoEpisodio(BaseModel):
    titulo: str
    resumen: str
    archivo: str


class LibroVisible(BaseModel):
    tema: str
    titulo: str
    resumen: str
    compartible: bool
    # Forma A (T2): el cliente del proyecto (frontmatter `cliente:`). None
    # si no es de un cliente, o nadie lo escribió todavía (lo pregunta
    # Remi, T3).
    cliente: str | None
    # De estado_libro.leer_estado: vacíos si el libro no tiene ## Estado
    # todavía. Nunca el cuerpo completo del libro.
    quedaste: str
    proximo_paso: str
    # De caminos.leer_hitos: [] si no tiene ## Camino.
    hitos: list[HitoConDetalle]
    # La entrega viva (no pagada, con monto) más próxima de este libro, si
    # tiene una — para el orden del líder en Proyectos (panel).
    entrega_cercana: EntregaCercana | None
    # mtime del archivo del libro: el Estado vive ahí, así que esto es
    # «cuándo se tocó por última vez» — el último escalón del orden.
    ultimo_estado_en: datetime
    # — Encargo H: el camino sale del SOP (oficios/proyectos-sop.md) —
    # «propio» | «cliente» | None si el frontmatter no lo dice todavía.
    tipo: str | None
    fases: list[FaseVisible]
    # La fase en la que está el proyecto, contando desde 1: la primera que
    # todavía no se entregó. None sin fases, o con todas entregadas.
    fase_actual_n: int | None
    # El primer hito sin marcar, y hasta 3 que vienen después — nunca el
    # camino entero de nuevo (para eso está `hitos`).
    hito_actual: HitoConDetalle | None
    siguientes: list[HitoConDetalle]
    # Qué hace Remi en el paso de `hito_actual`, según el SOP. "" sin hito
    # actual (camino vacío o terminado) o si el texto no matchea ninguna
    # plantilla (un hito escrito a mano, fuera del SOP).
    paso_remi: str


class GastoVisible(BaseModel):
    concepto: str
    monto: float
    # B6.5: el id de la fila, solo si una única fila forma este grupo —
    # con eso el panel puede ofrecer "corregir" sobre esa línea.
    id: str | None = None


class LineaDeEvidenciaVisible(BaseModel):
    texto: str
    origen: str
    hace_min: int


class LibroDetalle(LibroVisible):
    # Solo en el detalle de un libro: el Estado entero (no solo quedaste/
    # próximo paso) y el último episodio — el resumen de la constelación
    # (LibroVisible) se queda liviano a propósito.
    estado_completo: str
    ultimo_episodio: UltimoEpisodio | None
    # B6 (tablero 5, la ficha de cliente): gastado, agrupado por concepto
    # (incluye la parte de los comunes, repartida por minutos del mes),
    # minutos trabajados desde siempre, y lo que queda por hora.
    gastado: float
    gastos: list[GastoVisible]
    minutos_total: int
    por_hora: float | None
    # B6.3/B6.4: lo acordado (decisiones y entregas futuras), lo que pasó
    # (hasta 6 líneas de evidencia) y a qué está atento Remi — sin IA.
    decisiones: list[str]
    entregas_futuras: list[str]
    lo_que_paso: list[LineaDeEvidenciaVisible]
    atento_a: list[str]


def _quedaste_de(estado_texto: str) -> str:
    for linea in estado_texto.splitlines():
        if linea.strip().lower().startswith("quedaste:"):
            return linea.split(":", 1)[1].strip()
    return ""


def _proximo_paso_de(estado_texto: str) -> str:
    for linea in estado_texto.splitlines():
        limpia = linea.strip().lower()
        if limpia.startswith("próximo paso:") or limpia.startswith("proximo paso:"):
            return linea.split(":", 1)[1].strip()
    return ""


def _ultimo_episodio_de(tema: str) -> UltimoEpisodio | None:
    """El episodio más nuevo de este tema — el nombre de archivo empieza
    con la fecha (YYYY-MM-DD-…), así que ordenar por nombre alcanza."""
    carpeta = episodios.carpeta_episodios()
    if not carpeta.is_dir():
        return None
    candidatos: list[tuple[str, dict[str, str | list[str]]]] = []
    for ruta in carpeta.glob("*.md"):
        if libros.fuera_del_estante(ruta):
            continue
        texto = ruta.read_text()
        if not texto.startswith("---"):
            continue
        partes = texto.split("---", 2)
        if len(partes) < 3:
            continue
        campos = libros._frontmatter(partes[1])
        if campos.get("tema") == tema:
            candidatos.append((ruta.name, campos))
    if not candidatos:
        return None
    nombre, campos = max(candidatos, key=lambda par: par[0])
    titulo = campos.get("titulo")
    resumen = campos.get("resumen")
    return UltimoEpisodio(
        # Los episodios escriben titulo/resumen entre comillas
        # (cierre.py/episodios.py); _frontmatter() no las saca — acá sí,
        # porque esto lo lee el panel tal cual.
        titulo=titulo.strip('"') if isinstance(titulo, str) else "",
        resumen=resumen.strip('"') if isinstance(resumen, str) else "",
        archivo=nombre,
    )


# Una fase deja de ser «la actual» cuando ya se entregó. Cualquier otro
# estado (propuesta, pagando, pagada, en curso…) sigue abierto.
ESTADOS_DE_FASE_CERRADA = frozenset({"entregada", "cobrada", "cerrada", "hecha"})


def _fase_actual_n(fases: tuple[libros.Fase, ...]) -> int | None:
    for n, fase in enumerate(fases, start=1):
        if fase.estado.strip().lower() not in ESTADOS_DE_FASE_CERRADA:
            return n
    return None


def _libro_visible(libro: libros.Libro, conexion: Any) -> LibroVisible:
    estado_texto = estado_libro.leer_estado(libro.archivo)
    hitos_crudos = caminos.leer_hitos(libro.archivo)
    hitos = [
        HitoConDetalle(
            texto=h.texto,
            hecho=h.hecho,
            detalle=caminos.detalle_de(libro.tipo, h.texto),
            cerrado_por=(
                (lambda c: CerradoPor(tipo=c.tipo, ref=c.ref, en=c.en) if c else None)(
                    db.hito_cerrado_de(conexion, libro.tema, i)
                )
                if h.hecho
                else None
            ),
        )
        for i, h in enumerate(hitos_crudos, start=1)
    ]
    idx_actual = next((i for i, h in enumerate(hitos) if not h.hecho), None)
    hito_actual = hitos[idx_actual] if idx_actual is not None else None
    siguientes = hitos[idx_actual + 1 : idx_actual + 4] if idx_actual is not None else []
    paso_remi = caminos.paso_remi_de(libro.tipo, hito_actual.texto) if hito_actual is not None else ""
    entrega = entregas.entrega_del_proyecto(conexion, entregas._proyecto_id_de_tema(libro.tema))
    total_pagado = entregas.total_pagado_proyecto(conexion, entregas._proyecto_id_de_tema(libro.tema))
    cobrados = entregas.cobrado_en_cascada([f.monto for f in libro.fases], total_pagado)
    return LibroVisible(
        tema=libro.tema,
        titulo=libro.titulo,
        resumen=libro.resumen,
        compartible=libro.compartible,
        cliente=libro.cliente,
        quedaste=_quedaste_de(estado_texto),
        proximo_paso=_proximo_paso_de(estado_texto),
        hitos=hitos,
        # entrega_del_proyecto() ya filtra monto IS NOT NULL.
        entrega_cercana=(
            EntregaCercana(cliente=entrega.cliente, fecha=entrega.fecha, monto=entrega.monto)
            if entrega is not None and entrega.monto is not None
            else None
        ),
        ultimo_estado_en=datetime.fromtimestamp(libro.archivo.stat().st_mtime, tz=timezone.utc),
        tipo=libro.tipo,
        fases=[
            FaseVisible(
                nombre=f.nombre, alcance=f.alcance, monto=f.monto, listo_cuando=f.listo_cuando,
                estado=f.estado, cobrado=cobrado, minutos_estimados=f.minutos_estimados,
            )
            for f, cobrado in zip(libro.fases, cobrados)
        ],
        fase_actual_n=_fase_actual_n(libro.fases),
        hito_actual=hito_actual,
        siguientes=siguientes,
        paso_remi=paso_remi,
    )


@app.get("/libros", response_model=list[LibroVisible])
def libros_de() -> list[LibroVisible]:
    """La constelación de proyectos para el panel: un resumen por libro,
    nunca el cuerpo completo."""
    conexion = db.conectar()
    try:
        return [_libro_visible(libro, conexion) for libro in libros.listar()]
    finally:
        conexion.close()


@app.get("/libros/{tema}", response_model=LibroDetalle)
def libro_de(tema: str) -> LibroDetalle:
    """El detalle de un libro: lo mismo que /libros, más el Estado entero
    y el último episodio — demasiado para la lista, justo para su pantalla."""
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        raise HTTPException(status_code=404, detail="no tengo un libro con ese tema")
    conexion = db.conectar()
    try:
        return _libro_detalle(libro, conexion)
    finally:
        conexion.close()


def _libro_detalle(libro: libros.Libro, conexion: Any) -> LibroDetalle:
    visible = _libro_visible(libro, conexion)
    todos_los_temas = [l.tema for l in libros.listar()]
    numeros = ficha.ficha_de(conexion, libro.tema, todos_los_temas)
    acordado = ficha.lo_acordado(conexion, libro.tema)
    return LibroDetalle(
        **visible.model_dump(),
        estado_completo=estado_libro.leer_estado(libro.archivo),
        ultimo_episodio=_ultimo_episodio_de(libro.tema),
        gastado=numeros.gastado,
        gastos=[GastoVisible(concepto=g.concepto, monto=g.monto, id=g.id) for g in numeros.gastos],
        minutos_total=numeros.minutos_total,
        por_hora=numeros.por_hora,
        decisiones=acordado.decisiones,
        entregas_futuras=acordado.entregas_futuras,
        lo_que_paso=[
            LineaDeEvidenciaVisible(texto=e.texto, origen=e.origen, hace_min=e.hace_min)
            for e in ficha.lo_que_paso(conexion, libro.tema)
        ],
        atento_a=ficha.atento_a(libro, numeros.minutos_total),
    )


class HechoNuevo(BaseModel):
    hecho: bool


@app.post("/libros/{tema}/camino/{n}", response_model=Camino)
def marcar_hito_de_libro(tema: str, n: int, cuerpo: HechoNuevo) -> Camino:
    """Marca (o desmarca) el hito número `n` (1-indexed) del camino de ese
    libro — solo esa línea, «- [ ]» <-> «- [x]» — y deja un commit en la
    bóveda, igual que cualquier otra escritura de Remi ahí."""
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        raise HTTPException(status_code=404, detail="no tengo un libro con ese tema")
    hitos_antes = caminos.leer_hitos(libro.archivo)
    if not 1 <= n <= len(hitos_antes):
        raise HTTPException(status_code=404, detail=f"ese libro tiene {len(hitos_antes)} hito(s)")
    boveda_git.snapshot_antes(f"marcar el hito {n} de {libro.archivo.name}")
    caminos.marcar_por_indice(libro.archivo, n - 1, cuerpo.hecho)
    boveda_git.snapshot_despues(
        f"bóveda: hito {n} de {libro.archivo.name} -> {'hecho' if cuerpo.hecho else 'por hacer'}"
    )
    hitos = caminos.leer_hitos(libro.archivo)
    siguiente = caminos.siguiente_abierto(hitos)
    return Camino(
        hitos=[HitoVisible(texto=h.texto, hecho=h.hecho) for h in hitos],
        siguiente=HitoVisible(texto=siguiente.texto, hecho=siguiente.hecho) if siguiente else None,
    )


@app.post("/libros/{tema}/camino/{n}/deshacer", response_model=LibroDetalle)
def deshacer_hito(tema: str, n: int) -> LibroDetalle:
    """Forma K (B3.4): vuelve el hito a abierto y quita su `cerrado_por`
    — nunca borra el commit que lo cerró: deja OTRO commit en la bóveda
    que lo revierte, igual que cualquier otra escritura de Remi ahí."""
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        raise HTTPException(status_code=404, detail="no tengo un libro con ese tema")
    hitos_antes = caminos.leer_hitos(libro.archivo)
    if not 1 <= n <= len(hitos_antes):
        raise HTTPException(status_code=404, detail=f"ese libro tiene {len(hitos_antes)} hito(s)")
    boveda_git.snapshot_antes(f"deshacer el hito {n} de {libro.archivo.name}")
    caminos.marcar_por_indice(libro.archivo, n - 1, False)
    boveda_git.snapshot_despues(f"bóveda: hito {n} de {libro.archivo.name} deshecho")
    conexion = db.conectar()
    try:
        db.deshacer_hito_cerrado(conexion, tema, n)
        return _libro_detalle(libro, conexion)
    finally:
        conexion.close()


class MontoCorregido(BaseModel):
    monto: float


@app.patch("/gastos/{gasto_id}", response_model=GastoVisible)
def corregir_gasto(gasto_id: str, cuerpo: MontoCorregido) -> GastoVisible:
    """B6.5: «cada número se toca y se corrige» — un gasto que se anotó
    mal se arregla a mano, sobre su propia fila."""
    if cuerpo.monto < 0:
        raise HTTPException(status_code=422, detail="el monto no puede ser negativo")
    conexion = db.conectar()
    try:
        corregido = db.corregir_gasto(conexion, gasto_id, cuerpo.monto)
        if corregido is None:
            raise HTTPException(status_code=404, detail="no tengo ese gasto")
        return GastoVisible(concepto=corregido.concepto, monto=corregido.monto, id=corregido.id)
    finally:
        conexion.close()


# — Configuración (Panel → Ajustes): llaves y tokens, nunca por el túnel —


def _vino_por_el_tunel(request: Request) -> bool:
    """Cualquier cabecera Cf-* la pone Cloudflare: la petición vino por el
    túnel, no de 127.0.0.1. Cambiar una llave desde el teléfono, lejos del
    Mac, no es una decisión para tomar a ciegas."""
    return any(nombre.lower().startswith("cf-") for nombre in request.headers.keys())


def _si_es_del_tunel_lo_corta(request: Request) -> None:
    if _vino_por_el_tunel(request):
        raise HTTPException(status_code=403, detail="esto se cambia desde el Mac")


class ConexionNueva(BaseModel):
    valor: str


@app.get("/config/conexiones", response_model=dict[str, conexiones.Conexion])
def listar_conexiones(request: Request) -> dict[str, conexiones.Conexion]:
    # Conexion.termina_en muestra los últimos caracteres de una llave real
    # (conexiones.py): un GET por el túnel ya es una fuga parcial, no solo
    # el PUT/POST (T5.3).
    _si_es_del_tunel_lo_corta(request)
    return conexiones.estado()


@app.put("/config/conexiones/{nombre}", response_model=conexiones.Conexion)
def guardar_conexion(nombre: str, cuerpo: ConexionNueva, request: Request) -> conexiones.Conexion:
    _si_es_del_tunel_lo_corta(request)
    try:
        conexiones.guardar(nombre, cuerpo.valor)
    except conexiones.NombreInvalido:
        raise HTTPException(status_code=400, detail="ese nombre no está en la lista blanca") from None
    return conexiones.estado()[nombre]


@app.post("/config/conexiones/{nombre}/probar", response_model=conexiones.Prueba)
def probar_conexion(nombre: str, request: Request) -> conexiones.Prueba:
    _si_es_del_tunel_lo_corta(request)
    try:
        return conexiones.probar(nombre)
    except conexiones.NombreInvalido:
        raise HTTPException(status_code=400, detail="ese nombre no está en la lista blanca") from None


class ConfigGastoNueva(BaseModel):
    tope_dia_usd: float
    tope_mes_usd: float
    activo: bool


class MetaMensualNueva(BaseModel):
    meta_mensual: float


@app.put("/config/plata")
def guardar_meta_mensual(cuerpo: MetaMensualNueva, request: Request) -> dict[str, object]:
    _si_es_del_tunel_lo_corta(request)
    try:
        return conexiones.escribir_meta_mensual(cuerpo.meta_mensual)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


class ConfigGastoVista(BaseModel):
    tope_dia_usd: float
    tope_mes_usd: float
    activo: bool
    gastado_dia_usd: float
    gastado_mes_usd: float


def _vista_gasto() -> ConfigGastoVista:
    config = gasto.leer_config()
    return ConfigGastoVista(
        tope_dia_usd=config.tope_dia_usd,
        tope_mes_usd=config.tope_mes_usd,
        activo=config.activo,
        gastado_dia_usd=gasto.gasto_dia_usd(),
        gastado_mes_usd=gasto.gasto_mes_usd(),
    )


@app.get("/config/gasto", response_model=ConfigGastoVista)
def leer_config_gasto(request: Request) -> ConfigGastoVista:
    _si_es_del_tunel_lo_corta(request)
    return _vista_gasto()


@app.put("/config/gasto", response_model=ConfigGastoVista)
def guardar_config_gasto(cuerpo: ConfigGastoNueva, request: Request) -> ConfigGastoVista:
    _si_es_del_tunel_lo_corta(request)
    if cuerpo.tope_dia_usd < 0 or cuerpo.tope_mes_usd < 0:
        raise HTTPException(status_code=422, detail="el tope no puede ser negativo")
    gasto.escribir_config(gasto.ConfigGasto(tope_dia_usd=cuerpo.tope_dia_usd, tope_mes_usd=cuerpo.tope_mes_usd, activo=cuerpo.activo))
    return _vista_gasto()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PUERTO)

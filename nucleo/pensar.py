"""Pensar con Claude, opt-in por mensaje (think=true). Por defecto Remi no
gasta nada: este módulo solo corre si la ventanita lo pide explícito.

Va por la CLI de Claude Code (`claude -p`), que usa la sesión con la que
Milo ya está logueado — NO la API con clave, que se factura aparte. Por eso
acá no hay ANTHROPIC_API_KEY ni .env: la clave se BORRA del entorno del
subproceso, para que ni existiendo en el shell se termine facturando.

Lo que sale del Mac es la frase que dijiste y nada más: ni tareas viejas,
ni sesiones, ni la base."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Callable

import httpx

import db
import libros
import precarga
import voseo
import trabajo
import vectores

BINARIO = "claude"
# Las claves viven en nucleo/.env (fuera del repo). Se leen a un dict y NUNCA
# se exportan al entorno: la CLI de Claude no tiene por qué ver la de Venice.
RUTA_ENV = Path(__file__).resolve().parent / ".env"
# Motores: "claude" (la membresía Max, por la CLI, con acceso al estante) y
# los OpenAI-compatibles, que comparten un solo cliente y no tienen
# herramientas —el índice viaja en el system prompt pero no pueden bajar
# nada del estante—: "venice" (pago por token), "groq" (gratis) y
# "openrouter" (centavos) con el modelo que diga config/motores.json → charla,
# y "ollama" (local, gratis, nada sale del Mac).
MOTOR_POR_DEFECTO = "claude"
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
# Los dos que ofrece el chip. El primero es el económico (respaldo si el
# chip no manda modelo). El segundo es el que menos inventa. Otro id del
# cliente cae al del entorno: no se le manda a Venice un nombre suelto.
MODELOS_VENICE = ("z-ai-glm-5-3-flash", "grok-4-7")
VENICE_MODELO_POR_DEFECTO = MODELOS_VENICE[0]
VENICE_TIMEOUT_SEGUNDOS = 20.0
OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_URL = f"{OLLAMA_BASE}/v1/chat/completions"
# gemma3:4b: buen español, ~3,3 GB, cabe holgado en 16 GB y contesta en
# un par de segundos en un M4. Se cambia con REMI_OLLAMA_MODELO.
OLLAMA_MODELO_POR_DEFECTO = "gemma3:4b"
# Local, pero un modelo frío tarda en cargar a memoria la primera vez.
OLLAMA_TIMEOUT_SEGUNDOS = 30.0

# — La trastienda (config/motores.json) —
#
# Lo que hoy llama a Ollama o a Haiku para tareas de fondo —resumen vivo,
# claves, títulos de episodios, consolidación nocturna: nunca la charla—
# ahora lee esta lista en orden y cae al siguiente motor si uno falla (sin
# responder, respuesta vacía, o rechazado por la verificación anti-invento
# de quien llama, que sigue igual). Groq y OpenRouter son OpenAI-compatibles,
# como Venice; Ollama ya lo era. Sin `config/motores.json`, o con uno mal
# formado, la cadena por defecto es la misma que documenta ese archivo.
RUTA_MOTORES = Path(__file__).resolve().parent / "config" / "motores.json"
PROVEEDORES_TRASTIENDA: dict[str, tuple[str, str | None]] = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "ollama": (OLLAMA_URL, None),
}
TRASTIENDA_POR_DEFECTO: tuple[tuple[str, str], ...] = (
    ("groq", "openai/gpt-oss-120b"),
    ("openrouter", "deepseek/deepseek-v4-flash"),
    ("ollama", "gemma3:4b"),
)
TRASTIENDA_TIMEOUT_SEGUNDOS = 20.0

# — El respaldo de charla —
#
# Si la CLI de Claude dice que se llegó al límite de uso (no un error
# cualquiera: ESE en particular), no tiene sentido reintentar con otro modo
# de Claude —todos comparten el mismo límite de la membresía Max—, así que
# el turno se reintenta una vez, directo, con OpenRouter y el modelo más
# inteligente de DeepSeek. La CLI no da un código de error estructurado para
# esto: es texto, y el patrón es lo mejor que hay para reconocerlo.
PATRON_LIMITE_ALCANZADO = re.compile(r"usage limit|límite alcanzado|límite de uso", re.IGNORECASE)
RESPALDO_DE_CHARLA = ("openrouter", "deepseek/deepseek-v4-pro")


class LimiteDeClaude(Exception):
    """La CLI dijo que se llegó al límite de uso de la membresía Max. No
    tiene sentido reintentar con otro modo de Claude —rápido, equilibrio e
    inteligente comparten el mismo límite—, así que corta la cadena acá
    mismo; `pensar()` la atrapa y hace el respaldo de charla."""


SERVIDOR_MEMORIA = Path(__file__).resolve().parent / "memoria_mcp.py"
# Las únicas dos cosas que la CLI puede hacer además de contestar. El
# prefijo `mcp__memoria__` lo arma Claude Code con el nombre del servidor.
HERRAMIENTAS = ("mcp__memoria__leer", "mcp__memoria__guardar")
# Remi es también el asistente técnico de Juan Camilo (30/09/2026): lee el
# código de sus proyectos para entender el plan antes de opinar o armar un
# prompt. Solo leer: nada de escribir, ejecutar ni red.
HERRAMIENTAS_DE_LECTURA = ("Read", "Grep", "Glob")
CARPETAS_DE_CODIGO = (Path.home() / "proyectos", Path.home() / "projects")
# Lo que nunca se lee aunque esté en esas carpetas: claves y bases. Las
# reglas de Read valen también para Grep y Glob. Van con ruta absoluta
# («//» + la carpeta): un patrón suelto se resuelve contra la carpeta
# temporal de la llamada y no bloquea nada (probado el 30/09: leyó un
# .env de prueba).
PATRONES_QUE_NO_SE_LEEN = (
    "**/.env",
    "**/.env.*",
    "**/*.pem",
    "**/*.key",
    "**/*.db",
    "**/*.sqlite",
    "**/credentials*",
    "**/secrets*",
)


def reglas_de_no_leer() -> list[str]:
    return [f"Read(/{carpeta}/{patron})" for carpeta in CARPETAS_DE_CODIGO for patron in PATRONES_QUE_NO_SE_LEEN]


# Leer el estante son tres vueltas (pide, recibe, contesta); leer código
# lleva varias más (buscar, abrir dos o tres archivos, contestar).
MAX_VUELTAS = "10"
# Tres modos (ARQUITECTURA-CEREBRO §9), todos por la sesión de Max. Cada uno
# con su techo de tiempo; si el elegido falla o se pasa, cae al anterior
# (inteligente → equilibrio → rápido) y queda en el log.
@dataclass(frozen=True)
class Modo:
    nombre: str
    modelo: str
    techo_segundos: float
    # Opus piensa antes de contestar; los otros dos no. El razonamiento
    # cuenta como salida, así que su techo de salida es mucho más alto.
    razonamiento_tokens: int
    salida_tokens: int


MODOS: dict[str, Modo] = {
    # Techos más largos que en 3a: ahora puede leer código antes de
    # contestar, y un encargo para Claude Code es largo (salida 4000).
    "rapido": Modo("rapido", "haiku", 20.0, 0, 4000),
    "equilibrio": Modo("equilibrio", "sonnet", 45.0, 0, 4000),
    "inteligente": Modo("inteligente", "opus", 60.0, 8000, 16000),
}
ORDEN_DE_MODOS = ("rapido", "equilibrio", "inteligente")
MODO_POR_DEFECTO = "equilibrio"
# Compatibilidad con quien lo lea: el modelo del modo por defecto.
MODELO_POR_DEFECTO = MODOS[MODO_POR_DEFECTO].modelo
# Con razonamiento el elegido espera 60 s; en «extra», 90.
TECHO_CON_RAZONAMIENTO = 60.0
TECHO_EXTRA = 90.0
# El peor caso: Opus en extra agota sus 90 s, y después Sonnet y Haiku los
# suyos. La ventanita espera por encima de eso (pruebas/test_timeouts.py).
PEOR_CASO_SEGUNDOS = TECHO_EXTRA + MODOS["equilibrio"].techo_segundos + MODOS["rapido"].techo_segundos

# El carácter de Remi ES el system prompt (Fase 3a). Vive en el disco, fuera
# del repo (datos personales), y se lee en CADA mensaje: si Juan Camilo lo
# edita, Remi cambia sin reiniciar nada. REMI_CARACTER apunta a otro archivo
# (las pruebas lo usan).
RUTA_CARACTER = Path(__file__).resolve().parent.parent / "conocimiento" / "caracter.md"

# La conversación (ARQUITECTURA-CEREBRO §5): los últimos 10 turnos
# literales más un resumen vivo de todo lo anterior de la misma
# conversación. Se resume, nunca se corta. Y sigue hasta que Juan Camilo la
# cambie (3-oct): ya no hay conversación nueva por tiempo.
MAX_TURNOS = 10
INSTRUCCIONES_RESUMEN = (
    "Resumes una conversación entre Juan Camilo y Remi, su asistente. Te dan el "
    "resumen que había y los turnos que acaban de salir de la memoria literal. "
    "Devuelve el resumen actualizado: decisiones, datos (montos, fechas, nombres), "
    "pendientes y tono. En español, en prosa, máximo 150 palabras. Solo el resumen."
)

# Solo si el archivo no está: un Remi mínimo, para no quedarse mudo.
CARACTER_DE_RESPALDO = (
    "Eres Remi, el socio de Juan Camilo. Le hablas de tú, en español de Colombia, "
    "corto y directo: primero la respuesta. Nunca urges, nunca cuentas fallos, nunca "
    "inventas datos de sus proyectos: si no está en tu memoria, lo dices."
)


def caracter() -> str:
    """El carácter, recién leído del disco."""
    ruta = Path(os.environ.get("REMI_CARACTER") or RUTA_CARACTER)
    try:
        texto = ruta.read_text().strip()
    except OSError:
        print(f"[pensar] no encuentro {ruta}: uso el carácter de respaldo", file=sys.stderr)
        return CARACTER_DE_RESPALDO
    return texto or CARACTER_DE_RESPALDO

# La mente: el índice entero viaja en el system prompt, siempre. Es texto,
# no una herramienta — mirarlo no cuesta un turno ni una llamada. El cuerpo
# de cada entrada NO está acá: eso vive en el estante.
ENCABEZADO_INDICE = (
    "\n\nEsto es lo que ya sabes. Cada línea es algo que te contaron antes: "
    "[id] fecha · tema · título — con qué te quedaste.\n"
    "El resumen te dice CUÁL es cada cosa, no alcanza para contestar sobre ella. "
    "Si te preguntan por algo de esta lista, bájalo con la herramienta `leer` "
    "usando su id, y recién entonces contesta. Y si te cuentan algo que valga la "
    "pena recordar, guárdalo con `guardar` — solo eso, no cada tarea suelta.\n"
)


def _linea_indice(entrada: db.EntradaIndice) -> str:
    corto = str(entrada.id)[:8]
    fecha = entrada.fecha.date().isoformat()
    linea = f"[{corto}] {fecha} · {entrada.tema} · {entrada.titulo} — {entrada.resumen}"
    return f"{linea} (claves: {entrada.claves})" if entrada.claves else linea


# T10: el índice no tiene techo hoy (db.indice_memoria devuelve TODO) — con
# 50.000 entradas da ~892.000 tokens en vez de 8.000 (hallazgo de T9.6, prueba
# de escala). Esto le pone un presupuesto fijo al armarlo, nunca a la base:
# lo que no entra sigue en remi.db y se encuentra con `buscar_memoria`.
PRESUPUESTO_INDICE_TOKENS = int(os.environ.get("REMI_PRESUPUESTO_INDICE") or 8000)
_CARACTERES_POR_TOKEN = 4  # misma heurística de siempre (T9.6)


def _uso_por_tema() -> dict[str, float]:
    """trabajo_estado_en: el cursor de cuándo se tocó cada tema por última
    vez — la señal de «uso» que ya existe, sin inventar una tabla nueva."""
    try:
        conexion = db.conectar()
    except Exception:
        return {}
    try:
        filas = conexion.execute("SELECT tema, fecha FROM trabajo_estado_en").fetchall()
    finally:
        conexion.close()
    return {fila["tema"]: datetime.fromisoformat(fila["fecha"]).timestamp() for fila in filas}


def _indice_con_presupuesto(
    indice: list[db.EntradaIndice], presupuesto_tokens: int = PRESUPUESTO_INDICE_TOKENS
) -> tuple[list[db.EntradaIndice], dict[str, int]]:
    """Nivel 0 y 1 van primero y completos — nunca se recortan, aunque por sí
    solos pasen el presupuesto (son pocos hoy; si algún día no lo son, el
    presupuesto lo dice la bitácora, no un recorte silencioso). El resto
    entra por frescura y uso hasta el presupuesto; lo que no entra se cuenta
    por tema, una línea — no se borra ni se mueve ninguna nota."""
    uso = _uso_por_tema()

    def _clave(entrada: db.EntradaIndice) -> tuple[float, float]:
        return (entrada.fecha.timestamp(), uso.get(entrada.tema, 0.0))

    def _nivel(e: db.EntradaIndice) -> int:
        return e.nivel if e.nivel is not None else 99

    protegidas = sorted((e for e in indice if _nivel(e) <= 1), key=_clave, reverse=True)
    resto = sorted((e for e in indice if _nivel(e) > 1), key=_clave, reverse=True)

    # Reserva para el encabezado y, en el peor caso, una línea de «no entró»
    # por cada tema que aparece en `resto` — así el total que arma
    # instrucciones_con_indice (encabezado + líneas + ese pie) no se pasa
    # del presupuesto, aunque el pie real sea más chico que el peor caso.
    temas_en_resto = {e.tema for e in resto}
    reserva_pie = sum(len(f"- {t}: 99999 más\n") for t in temas_en_resto)
    limite = presupuesto_tokens * _CARACTERES_POR_TOKEN - len(ENCABEZADO_INDICE) - reserva_pie
    incluidas = list(protegidas)
    usado = sum(len(_linea_indice(e)) + 1 for e in incluidas)
    recortadas_por_tema: dict[str, int] = {}
    for entrada in resto:
        costo = len(_linea_indice(entrada)) + 1
        if usado + costo <= limite:
            incluidas.append(entrada)
            usado += costo
        else:
            recortadas_por_tema[entrada.tema] = recortadas_por_tema.get(entrada.tema, 0) + 1
    return incluidas, recortadas_por_tema


# El modo «Prompt» (3b): arma un encargo de una tarea para Claude Code.
# Su system prompt vive en el repo (no tiene datos personales) y se lee en
# cada llamada, como el carácter.
RUTA_ENCARGO = Path(__file__).resolve().parent / "prompts" / "encargo.md"
# El rol técnico y de prompting, siempre junto al carácter (30/09/2026: «el
# modo prompt debe estar implícito»). Está en el repo; el carácter es de él.
RUTA_TECNICO = Path(__file__).resolve().parent / "prompts" / "tecnico.md"


def rol_tecnico() -> str:
    try:
        return RUTA_TECNICO.read_text().strip()
    except OSError:
        print(f"[pensar] no encuentro {RUTA_TECNICO}: sigo solo con el carácter", file=sys.stderr)
        return ""


def _cuerpo_oficio(nombre: str) -> str:
    """El cuerpo de un oficio (sin frontmatter), para meterlo nivel 2 —
    entero, no solo el título — en el system prompt de un encargo. Cadena
    vacía si no está: la puerta de prompts sigue andando sin ese oficio,
    peor pero sin caerse (Biblia Parte VI)."""
    import sembrar_conocimiento  # import diferido: evita ciclos de import

    ruta = sembrar_conocimiento.carpeta_oficios() / f"{nombre}.md"
    try:
        texto = ruta.read_text()
    except OSError:
        return ""
    partes = texto.split("---", 2)
    return partes[2].strip() if len(partes) >= 3 else texto.strip()


# «Me escribió un cliente» (Biblia Parte VI, oficio «clientes»): mismo
# patrón que el encargo — un archivo del repo (sin datos personales) más
# los oficios reales, nivel 2, cargados adentro.
RUTA_CLIENTE = Path(__file__).resolve().parent / "prompts" / "cliente.md"


def sistema_cliente() -> str:
    """Lectura, riesgos, respuesta recomendada y límites (oficio `clientes`)
    — con los oficios `clientes`, `proyectos-sop` y `mi-voz` cargados
    enteros, más el proyecto activo si hay uno. Remi nunca envía nada:
    esto es una propuesta para que Juan Camilo decida."""
    try:
        base = RUTA_CLIENTE.read_text().strip()
    except OSError:
        print(f"[pensar] no encuentro {RUTA_CLIENTE}: uso uno mínimo", file=sys.stderr)
        base = (
            "Te pegaron algo de un cliente. Devuelve LECTURA, RIESGOS, RESPUESTA "
            "RECOMENDADA y LÍMITES. Nunca envíes nada: es una propuesta."
        )
    piezas = [base]
    for oficio in ("clientes", "proyectos-sop", "mi-voz"):
        cuerpo = _cuerpo_oficio(oficio)
        if cuerpo:
            piezas.append(f"## Oficio: {oficio}\n" + cuerpo)

    try:
        activo = precarga.proyecto_activo()
        if activo is not None:
            tema, _razon = activo
            resumen = precarga.resumen_nivel2(tema)
            if resumen:
                piezas.append("## Proyecto activo\n" + resumen)
    except Exception as error:  # noqa: BLE001 — sin proyecto activo, sigue igual
        print(f"[pensar] no pude precargar el proyecto activo del cliente ({type(error).__name__})", file=sys.stderr)

    return "\n\n".join(piezas)


def sistema_encargo() -> str:
    """La puerta de los prompts (Biblia Parte VI): el encargo no sale solo
    con la forma fija de `encargo.md`, sino con los oficios `prompting` y
    `claude-code` de verdad cargados (nivel 2, el cuerpo entero) más el
    libro del proyecto activo, si hay uno. Sin ellos, cae al `encargo.md`
    solo — nunca se rompe por faltar un oficio.

    F2.5 (2/10/2026): el registro de trabajo es la misma persona que el de
    charla — el carácter va primero, y recién después la forma del encargo
    y los oficios. Antes el encargo salía sin carácter (3b)."""
    try:
        base = RUTA_ENCARGO.read_text().strip()
    except OSError:
        print(f"[pensar] no encuentro {RUTA_ENCARGO}: uso uno mínimo", file=sys.stderr)
        base = (
            "Devuelve lo que te dicen como UN encargo de UNA tarea para Claude Code, "
            "en español y sin markdown, con las secciones QUÉ, DÓNDE, LISTO CUANDO y NO TOCAR."
        )
    piezas = [caracter(), base]

    prompting = _cuerpo_oficio("prompting")
    if prompting:
        piezas.append("## Oficio: prompting — la forma fija del encargo\n" + prompting)

    claude_code = _cuerpo_oficio("claude-code")
    if claude_code:
        piezas.append("## Oficio: Claude Code — qué pieza y qué modelo recomendar\n" + claude_code)

    # T9.2: stack y vibe-coding viajan junto a prompting y claude-code —
    # las lecciones y las reglas que importan al escribir código.
    for oficio in ("stack", "vibe-coding"):
        cuerpo = _cuerpo_oficio(oficio)
        if cuerpo:
            piezas.append(f"## Oficio: {oficio}\n" + cuerpo)

    try:
        activo = precarga.proyecto_activo()
        if activo is not None:
            tema, _razon = activo
            resumen = precarga.resumen_nivel2(tema)
            if resumen:
                piezas.append("## Proyecto activo\n" + resumen)
            # T8.7: consultar antes de actuar — hasta tres lecciones de
            # este libro, antes de proponer un arreglo que ya se intentó.
            ojos = trabajo.lecciones_de_ojo(tema)
            if ojos:
                piezas.append("## Lecciones de este proyecto\n" + "\n".join(ojos))
            # T9.2: las reglas de este proyecto, si ya tiene alguna.
            libro = next((l for l in libros.listar() if l.tema == tema), None)
            if libro is not None:
                reglas = libros.reglas_de_este_proyecto(libro.archivo)
                if reglas:
                    piezas.append("## Reglas de este proyecto\n" + "\n".join(f"- {r}" for r in reglas))
    except Exception as error:  # noqa: BLE001 — sin proyecto activo, el encargo sigue
        print(f"[pensar] no pude precargar el proyecto activo del encargo ({type(error).__name__})", file=sys.stderr)

    return "\n\n".join(piezas)


def instrucciones_con_indice(
    indice: list[db.EntradaIndice], base: str | None = None, presupuesto_tokens: int = PRESUPUESTO_INDICE_TOKENS
) -> str:
    """El carácter (o el system prompt que se pida, como el del encargo) más
    lo que Remi tiene presente. Sin entradas no se anexa nada: un encabezado
    solo, sin líneas, invitaría a inventar. T10: el índice entra con un
    presupuesto de tokens — lo que no entra se cuenta por tema, no se oculta
    que existe."""
    if base is None:
        tecnico = rol_tecnico()
        base = f"{caracter()}\n\n{tecnico}" if tecnico else caracter()
    if not indice:
        return base
    incluidas, recortadas_por_tema = _indice_con_presupuesto(indice, presupuesto_tokens)
    lineas = [_linea_indice(entrada) for entrada in incluidas]
    if recortadas_por_tema:
        lineas.append("")
        lineas.append(
            "Y más que no entró aquí por espacio (nada se perdió — búscalo con "
            "`buscar_memoria` si hace falta):"
        )
        lineas.extend(f"- {tema}: {cantidad} más" for tema, cantidad in sorted(recortadas_por_tema.items()))
    return base + ENCABEZADO_INDICE + "\n".join(lineas)


def _indice() -> list[db.EntradaIndice]:
    """Si la base no está, Remi piensa sin memoria: mejor eso que no pensar."""
    try:
        conexion = db.conectar()
    except Exception as error:
        print(f"[claude] no pude leer la memoria ({type(error).__name__}): pienso sin ella", file=sys.stderr)
        return []
    try:
        return db.indice_memoria(conexion)
    finally:
        conexion.close()


ENCABEZADO_ASOCIADOS = (
    "\n\nEsto quizá tenga que ver (son solo títulos — asociación por vector, "
    "ARQUITECTURA-CEREBRO §3; no supongas de qué tratan, si hace falta "
    "pregunta o bájalos con `leer`): "
)


def _asociados(frase: str) -> list[str]:
    """3–5 títulos de la bóveda parecidos a `frase`. Sin Ollama arriba o sin
    vectores todavía, Remi piensa sin asociados — nunca se cae por esto."""
    try:
        conexion = db.conectar()
    except Exception as error:
        print(f"[asociar] no pude leer la memoria ({type(error).__name__}): sigo sin asociados", file=sys.stderr)
        return []
    try:
        return vectores.asociar(conexion, frase, con_fecha=True)
    except Exception as error:  # noqa: BLE001 — sin Ollama no hay asociados, no hay crash
        print(f"[asociar] no pude asociar ({type(error).__name__}): sigo sin asociados", file=sys.stderr)
        return []
    finally:
        conexion.close()


def _precarga() -> tuple[str, str] | None:
    """(texto, "<tema> razon=<razón>"), o None. Nunca rompe la respuesta:
    sin precarga, Remi piensa igual, solo que sin el nivel 2 ya puesto."""
    try:
        return precarga.bloque()
    except Exception as error:  # noqa: BLE001 — la precarga es una ayuda, no un requisito
        print(f"[precarga] no pude precargar ({type(error).__name__}): sigo sin ella", file=sys.stderr)
        return None


def _tema_dudoso(frase: str) -> tuple[str, str] | None:
    """precarga.tema_dudoso, sin romper nunca la respuesta."""
    try:
        return precarga.tema_dudoso(frase, _ahora())
    except Exception as error:  # noqa: BLE001 — si falla, se precarga como siempre
        print(f"[precarga] no pude ver si el tema es dudoso ({type(error).__name__})", file=sys.stderr)
        return None


def _pregunta_por_remi(frase: str) -> bool:
    try:
        return precarga.pregunta_por_remi(frase)
    except Exception:  # noqa: BLE001 — nunca rompe la respuesta
        return False


def _referencia(frase: str) -> str | None:
    """La sección de la Biblia que la frase pregunta (precarga.de_referencia).
    Nunca rompe la respuesta."""
    try:
        return precarga.de_referencia(frase)
    except Exception as error:  # noqa: BLE001 — una ayuda, no un requisito
        print(f"[precarga] no pude leer la referencia ({type(error).__name__}): sigo sin ella", file=sys.stderr)
        return None


@dataclass(frozen=True)
class Pensado:
    # Lo que el modelo contestó, entero. (El nombre es de cuando Remi solo
    # devolvía un paso mínimo; desde la Fase 3a es la respuesta completa.)
    paso_minimo: str
    tokens_entrada: int
    tokens_salida: int
    modelo: str
    # Cuántas cosas tenía presentes y si llegó a bajar alguna del estante.
    entradas_en_indice: int = 0
    leyo_memoria: bool = False
    # El motor real que contestó ("claude", "venice", "groq", "openrouter",
    # "ollama", o un proveedor de la trastienda): lo que el chip de la
    # ventanita debería mostrar, a
    # diferencia de `modelo`, que es el alias/id del modelo dentro de ese
    # motor.
    motor_usado: str = "claude"


def _leer_env(ruta: Path | None = None) -> dict[str, str]:
    """KEY=VALOR por línea; # comenta; comillas alrededor del valor se quitan.

    La ruta se resuelve al llamar, no al definir: un default `= RUTA_ENV`
    quedaba atado al arrancar y las pruebas leían el .env de verdad — una
    llamó a Venice con la clave real."""
    ruta = RUTA_ENV if ruta is None else ruta
    valores: dict[str, str] = {}
    if not ruta.exists():
        return valores
    for linea in ruta.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip("\"'")
    return valores


def _ajuste(clave: str, por_defecto: str) -> str:
    """La variable de entorno gana sobre el .env, para poder probar sin tocarlo."""
    return os.environ.get(clave) or _leer_env().get(clave) or por_defecto


def modelo() -> str:
    """El modelo del modo por defecto (lo muestra el dropdown de motores)."""
    return MODOS[MODO_POR_DEFECTO].modelo


def modo(pedido: str | None) -> Modo:
    if pedido in MODOS:
        return MODOS[pedido]
    if pedido is not None:
        print(f"[pensar] modo desconocido {pedido!r}: uso {MODO_POR_DEFECTO}", file=sys.stderr)
    return MODOS[MODO_POR_DEFECTO]


# El nivel de la ventanita («Opus 5.5 · Medio»): cuánto piensa antes de
# contestar el modelo elegido. Solo toca al elegido; si cae al anterior, ese
# va con lo suyo. Con razonamiento el techo sube a 60 s, que es el de Opus:
# el peor caso de la cadena sigue en PEOR_CASO_SEGUNDOS.
NIVELES = ("bajo", "medio", "alto", "extra")
_TOKENS_POR_NIVEL = {
    "bajo": (0, 4000),
    "medio": (8000, 16000),
    "alto": (16000, 24000),
    "extra": (32000, 40000),
}


def con_nivel(m: Modo, nivel: str | None) -> Modo:
    if nivel not in _TOKENS_POR_NIVEL:
        return m
    razonamiento, salida = _TOKENS_POR_NIVEL[nivel]
    if nivel == "extra":
        techo = TECHO_EXTRA
    elif razonamiento == 0:
        techo = m.techo_segundos
    else:
        techo = max(m.techo_segundos, TECHO_CON_RAZONAMIENTO)
    return replace(m, razonamiento_tokens=razonamiento, salida_tokens=salida, techo_segundos=techo)


def cadena_de_modos(elegido: Modo) -> list[Modo]:
    """El elegido y, si falla, los anteriores: inteligente → equilibrio → rápido."""
    hasta = ORDEN_DE_MODOS.index(elegido.nombre)
    return [MODOS[n] for n in reversed(ORDEN_DE_MODOS[: hasta + 1])]


MOTORES = ("claude", "venice", "groq", "openrouter", "ollama")


def motor(pedido: str | None = None) -> str:
    """El motor a usar: el que pida la ventanita (un dropdown, elegido a
    conciencia) y, si no pide, el del .env. Uno desconocido cae al por
    defecto y lo dice."""
    elegido = (pedido or _ajuste("REMI_PENSADOR", MOTOR_POR_DEFECTO)).lower()
    if elegido not in MOTORES:
        print(f"[pensar] motor desconocido {elegido!r}: uso {MOTOR_POR_DEFECTO}", file=sys.stderr)
        return MOTOR_POR_DEFECTO
    return elegido


@dataclass(frozen=True)
class MotorDisponible:
    id: str
    label: str
    # False si le falta algo (la CLI, la clave): se muestra igual, apagado,
    # para que se vea POR QUÉ no está.
    disponible: bool
    detalle: str


def _modelos_de_ollama() -> list[str] | None:
    """Los modelos que Ollama tiene bajados. None si Ollama no está sirviendo."""
    try:
        respuesta = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=1.5)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (httpx.HTTPError, ValueError):
        return None
    modelos = datos.get("models") if isinstance(datos, dict) else None
    if not isinstance(modelos, list):
        return []
    return [m["name"] for m in modelos if isinstance(m, dict) and isinstance(m.get("name"), str)]


def motores_disponibles() -> list[MotorDisponible]:
    """Lo que puede elegir el dropdown de la ventanita."""
    import shutil

    hay_cli = shutil.which(BINARIO) is not None
    hay_clave_venice = bool(_ajuste("VENICE_API_KEY", ""))
    hay_clave_groq = bool(_ajuste("GROQ_API_KEY", ""))
    hay_clave_openrouter = bool(_ajuste("OPENROUTER_API_KEY", ""))
    modelo_ollama = _ajuste("REMI_OLLAMA_MODELO", OLLAMA_MODELO_POR_DEFECTO)
    bajados = _modelos_de_ollama()
    if bajados is None:
        ollama_ok, ollama_detalle = False, "Ollama no está sirviendo (brew services start ollama)"
    elif modelo_ollama not in bajados and f"{modelo_ollama}:latest" not in bajados:
        ollama_ok, ollama_detalle = False, f"falta bajar el modelo (ollama pull {modelo_ollama})"
    else:
        ollama_ok, ollama_detalle = True, f"{modelo_ollama}, local, sin acceso al estante"
    return [
        MotorDisponible(
            id="claude",
            label="Claude (Max)",
            disponible=hay_cli,
            detalle=f"{modelo()}, con acceso al estante" if hay_cli else "no encuentro `claude` en el PATH",
        ),
        MotorDisponible(
            id="venice",
            label="Venice (pago)",
            disponible=hay_clave_venice,
            detalle=(
                "GLM Flash o Grok 4.7, sin acceso al estante"
                if hay_clave_venice
                else "sin VENICE_API_KEY en nucleo/.env"
            ),
        ),
        MotorDisponible(
            id="groq",
            label="Groq (gratis)",
            disponible=hay_clave_groq,
            detalle=(
                f"{_modelo_charla('groq', None)}, sin acceso al estante"
                if hay_clave_groq
                else "sin GROQ_API_KEY en nucleo/.env"
            ),
        ),
        MotorDisponible(
            id="openrouter",
            label="OpenRouter (centavos)",
            disponible=hay_clave_openrouter,
            detalle=(
                f"{_modelo_charla('openrouter', None)}, sin acceso al estante"
                if hay_clave_openrouter
                else "sin OPENROUTER_API_KEY en nucleo/.env"
            ),
        ),
        MotorDisponible(
            id="ollama",
            label="Ollama (local, gratis)",
            disponible=ollama_ok,
            detalle=ollama_detalle,
        ),
    ]


def _entorno(m: Modo | None = None) -> dict[str, str]:
    """El entorno del subproceso, sin credenciales de API. Si Milo tiene una
    clave exportada, la CLI la usaría y eso se factura por fuera del plan —
    justo lo que hay que evitar."""
    entorno = dict(os.environ)
    for clave in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        entorno.pop(clave, None)
    # El razonamiento cuenta contra el techo de salida: solo inteligente lo
    # prende, y por eso su techo de salida es mucho más alto.
    m = MODOS[MODO_POR_DEFECTO] if m is None else m
    entorno["MAX_THINKING_TOKENS"] = str(m.razonamiento_tokens)
    entorno["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(m.salida_tokens)
    return entorno


def _config_mcp(carpeta: Path, marca: Path | None = None) -> Path:
    """El único servidor que la CLI ve, escrito al vuelo en la carpeta
    temporal de esta llamada. Con --strict-mcp-config, ningún otro MCP del
    sistema entra: ni los de Claude Code, ni los del repo."""
    ruta = carpeta / "mcp.json"
    entorno_servidor = {}
    # El estante corre en otro proceso: si la base no es la de siempre,
    # hay que decírselo.
    if "REMI_DB_PATH" in os.environ:
        entorno_servidor["REMI_DB_PATH"] = os.environ["REMI_DB_PATH"]
    if marca is not None:
        entorno_servidor["REMI_MARCA_LECTURA"] = str(marca)
    ruta.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "memoria": {
                        "command": sys.executable,
                        "args": [str(SERVIDOR_MEMORIA)],
                        "env": entorno_servidor,
                    }
                }
            }
        )
    )
    return ruta


def _carpetas_de_codigo() -> list[str]:
    argumentos: list[str] = []
    for carpeta in CARPETAS_DE_CODIGO:
        if carpeta.is_dir():
            argumentos += ["--add-dir", str(carpeta)]
    return argumentos


INSTRUCCIONES_BUSQUEDA = (
    "Esta vez te pidió buscar en la web: usa WebSearch. Contesta en una o dos frases y después "
    "pon como máximo 3 links, uno por renglón, así: [título corto](https://…) — una línea de "
    "por qué sirve. Nada más."
)


def _comando(nombre_modelo: str, instrucciones: str, config_mcp: Path, buscar: bool = False) -> list[str]:
    # WebSearch solo en el mensaje que lo pide: nunca queda prendido.
    herramientas_casa = (*HERRAMIENTAS_DE_LECTURA, "WebSearch") if buscar else HERRAMIENTAS_DE_LECTURA
    return [
        BINARIO,
        "-p",
        "--model",
        nombre_modelo,
        "--output-format",
        "json",
        "--system-prompt",
        instrucciones,
        # El encierro: de las herramientas de la casa, solo leer; sin
        # settings del usuario, sin sesión en disco. Además, el estante y
        # solo esas dos puertas.
        "--tools",
        ",".join(herramientas_casa),
        *_carpetas_de_codigo(),
        "--restricted",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--mcp-config",
        str(config_mcp),
        "--allowedTools",
        ",".join((*HERRAMIENTAS, *herramientas_casa)),
        "--disallowedTools",
        ",".join(reglas_de_no_leer()),
        "--max-turns",
        MAX_VUELTAS,
    ]




def _tokens(uso: Any) -> tuple[int, int]:
    if not isinstance(uso, dict):
        return 0, 0
    entrada = uso.get("input_tokens")
    salida = uso.get("output_tokens")
    return (
        entrada if isinstance(entrada, int) else 0,
        salida if isinstance(salida, int) else 0,
    )


def _tokens_cacheados(uso: Any) -> tuple[int, int]:
    """Leídos y escritos en la caché, si la CLI lo informa; si no, 0."""
    if not isinstance(uso, dict):
        return 0, 0
    leida = uso.get("cache_read_input_tokens")
    escrita = uso.get("cache_creation_input_tokens")
    return (leida if isinstance(leida, int) else 0, escrita if isinstance(escrita, int) else 0)


def _modelo_real(datos: dict[str, Any], pedido: str) -> str:
    """El id exacto que usó la CLI, si lo dice; si no, el alias que pedimos."""
    uso_por_modelo = datos.get("modelUsage")
    if isinstance(uso_por_modelo, dict):
        for nombre, detalle in uso_por_modelo.items():
            if isinstance(detalle, dict):
                canonico = detalle.get("canonicalModel")
                if isinstance(canonico, str) and canonico:
                    return canonico
            if isinstance(nombre, str) and nombre:
                return nombre
    return pedido


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _conversacion() -> tuple[list[db.Turno], str]:
    """Los últimos 10 turnos literales y el resumen de lo anterior, de la
    conversación vigente. Sin conversación vigente, nada."""
    try:
        conexion = db.conectar()
    except Exception:
        return [], ""
    try:
        vigente = db.conversacion_vigente(conexion, _ahora())
        if vigente is None:
            return [], ""
        return db.turnos_de(conexion, vigente.id)[-MAX_TURNOS:], vigente.resumen
    finally:
        conexion.close()


def _turnos() -> list[db.Turno]:
    return _conversacion()[0]


def _guardar_turno(rol: str, texto: str) -> str | None:
    try:
        conexion = db.conectar()
    except Exception:
        return None
    try:
        return db.guardar_turno(conexion, rol, texto, _ahora())
    finally:
        conexion.close()


def _lineas(turnos: list[db.Turno]) -> str:
    return "\n".join(f"{'Juan Camilo' if t.rol == 'juan' else 'Remi'}: {t.texto}" for t in turnos)


def mensaje_con_historia(frase: str, turnos: list[db.Turno], resumen: str = "", contexto: str = "") -> str:
    """Lo que viaja como mensaje: el contexto que cambia por turno (la
    precarga del proyecto activo y los asociados por vector), el resumen de
    lo anterior, los últimos turnos literales y, al final, lo que Juan
    Camilo acaba de decir.

    V4 (2/10/2026): lo que cambia de un turno al otro va acá y no en el
    system prompt. La caché de la API es por prefijo y el system prompt es
    un solo bloque: un título de asociado distinto al final lo invalidaba
    entero (medido: cache_leida=0 en 10 de 12 llamadas seguidas)."""
    partes = []
    if contexto.strip():
        partes.append(contexto.strip())
    if resumen:
        partes.append(f"Resumen de lo anterior en esta conversación:\n{resumen}")
    if turnos:
        partes.append(f"Últimos turnos (lo más viejo primero):\n{_lineas(turnos)}")
    if not partes:
        return frase
    return "\n\n".join(partes) + f"\n\nAhora Juan Camilo dice:\n{frase}"


# — El resumen vivo —


def resumir(resumen: str, salientes: list[db.Turno]) -> str | None:
    """La trastienda de `config/motores.json` (groq → openrouter → ollama,
    por defecto): esto es tarea de fondo, nunca la charla."""
    pedido = f"Resumen que había:\n{resumen or '(ninguno)'}\n\nTurnos que salen:\n{_lineas(salientes)}"
    pensado = pensar_con_trastienda(pedido, INSTRUCCIONES_RESUMEN)
    return pensado.paso_minimo if pensado else None


def actualizar_resumen(conversacion_id: str, resumidor: "Any" = None) -> bool:
    """Cada turno que sale de los 10 literales entra al resumen. True si
    cambió algo. Si el resumidor falla, el resumen queda como estaba y se
    reintenta la próxima vez: los turnos no se pierden, siguen en la base."""
    resumidor = resumir if resumidor is None else resumidor
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT resumen, resumidos FROM conversaciones WHERE id = ?", (conversacion_id,)
        ).fetchone()
        if fila is None:
            return False
        turnos = db.turnos_de(conexion, conversacion_id)
        hasta = len(turnos) - MAX_TURNOS
        if hasta <= fila["resumidos"]:
            return False
        salientes = turnos[fila["resumidos"] : hasta]
        nuevo = resumidor(fila["resumen"], salientes)
        if not nuevo:
            print("[resumen] no se pudo resumir: queda para la próxima", file=sys.stderr)
            return False
        db.guardar_resumen(conexion, conversacion_id, nuevo.strip(), hasta)
        print(f"[resumen] +{len(salientes)} turnos al resumen ({hasta} en total)", file=sys.stderr)
        return True
    finally:
        conexion.close()


def _actualizar_resumen_en_segundo_plano(conversacion_id: str | None) -> None:
    """Después de contestar, no antes: resumir no puede demorar la respuesta."""
    if conversacion_id is None:
        return
    import threading

    def correr() -> None:
        try:
            actualizar_resumen(conversacion_id)
        except Exception as error:
            print(f"[resumen] falló ({type(error).__name__}: {error})", file=sys.stderr)

    threading.Thread(target=correr, daemon=True).start()


def _cerrar_conversaciones_inactivas_en_segundo_plano() -> None:
    """T9.5/T10: al abrir una conversación nueva, las que quedaron atrás (60
    min sin turnos) dejan su episodio si tuvieron sustancia. En segundo
    plano, después de contestar — igual que el resumen, nunca a mitad de un
    turno. La consolidación de la noche ya cubre esto en menos de 24 h; esto
    lo adelanta a la próxima vez que Juan Camilo le habla a Remi."""
    import threading

    def correr() -> None:
        try:
            import cierre

            cerradas = cierre.cerrar_conversaciones_inactivas(_ahora())
            if cerradas:
                print(f"[conversaciones] episodio(s) al abrir una nueva={cerradas}", file=sys.stderr)
        except Exception as error:
            print(
                f"[conversaciones] cierre en segundo plano falló ({type(error).__name__}: {error})",
                file=sys.stderr,
            )

    threading.Thread(target=correr, daemon=True).start()


# V3 (2/10/2026): un turno sale en frases. El generador rinde cada oración
# completa en cuanto el motor la termina y, al agotarse, devuelve el Pensado
# (o None). `pensar()` lo consume entero: es el mismo camino, sin público.
Frases = Generator[str, None, "Pensado | None"]


def _agotar(frases: Frases) -> Pensado | None:
    try:
        while True:
            next(frases)
    except StopIteration as fin:
        resultado: Pensado | None = fin.value
        return resultado


def pensar(
    frase: str,
    motor_pedido: str | None = None,
    modo_pedido: str | None = None,
    sistema: str | None = None,
    nivel: str | None = None,
    buscar: bool = False,
    modelo_ollama: str | None = None,
    modelo_venice: str | None = None,
) -> Pensado | None:
    """Lo que el motor elegido contesta a `frase`, con la conversación de la
    última hora. None si el motor no está, falla o no devolvió texto: el que
    llama sigue por el camino sin IA — nunca se rompe la respuesta por esto."""
    return _agotar(
        pensar_en_frases(
            frase, motor_pedido, modo_pedido, sistema, nivel, buscar, modelo_ollama, modelo_venice, en_vivo=False
        )
    )


def pensar_en_frases(
    frase: str,
    motor_pedido: str | None = None,
    modo_pedido: str | None = None,
    sistema: str | None = None,
    nivel: str | None = None,
    buscar: bool = False,
    modelo_ollama: str | None = None,
    modelo_venice: str | None = None,
    en_vivo: bool = True,
) -> Frases:
    """Como `pensar()`, pero rinde cada frase completa en cuanto llega (la
    voz arranca con la primera, no con la respuesta entera) y al final
    devuelve el mismo Pensado. Con `en_vivo=False` no transmite nada: pide
    la respuesta entera como siempre (es lo que hace `pensar()`).

    En vivo, si un motor falla después de haber soltado alguna frase, no se
    cae a otro motor ni a otro modo: lo dicho ya se oyó, y una segunda
    respuesta distinta encima sería peor que quedarse sin la primera. El que
    llama recibe None y contesta sin IA, como cuando el motor no está."""
    indice = _indice()
    # El system prompt es lo estable (carácter, rol técnico, índice): así la
    # caché de la API lo lee en vez de reescribirlo en cada turno.
    instrucciones = instrucciones_con_indice(indice, sistema)
    contexto = ""
    asociados = _asociados(frase)
    if asociados:
        contexto += ENCABEZADO_ASOCIADOS + ", ".join(asociados)
    dudoso = _tema_dudoso(frase)
    precargado = None if dudoso is not None else _precarga()
    if dudoso is not None:
        # Con un system prompt propio (el encargo, el cliente) no se pregunta:
        # el documento sale igual con el hueco marcado.
        contexto += precarga.linea_de_duda(dudoso, encargo=sistema is not None)
        print(f"[precarga] tema dudoso entre {dudoso[0]} y {dudoso[1]}: que pregunte", file=sys.stderr)
    elif precargado is not None:
        texto, registro = precargado
        contexto += texto
        print(f"[precarga] precargado={registro}", file=sys.stderr)
    else:
        print("[precarga] nada que precargar (sin bloque abierto ni libro tocado)", file=sys.stderr)
    # Con el tema dudoso tampoco entra la referencia: decidiría por él cuál de
    # los dos proyectos es (probado el 3-oct: con la Biblia de Remi delante no
    # preguntaba).
    if _pregunta_por_remi(frase):
        contexto += precarga.estado_propio()
        print("[precarga] estado propio: la frase pregunta por Remi, entra doctor.sh", file=sys.stderr)
    referencia = _referencia(frase) if dudoso is None else None
    if referencia is not None:
        contexto += referencia
        print("[precarga] referencia: la frase nombra la Biblia, entra la sección que toca", file=sys.stderr)
    turnos, resumen = _conversacion()
    abre_conversacion_nueva = not turnos  # toda conversación vigente tiene al menos un turno
    mensaje = mensaje_con_historia(frase, turnos, resumen, contexto)
    elegido = motor(motor_pedido)
    if buscar:
        # Solo Claude tiene WebSearch: una búsqueda va por Claude aunque el
        # chip diga Venice u Ollama, y queda dicho en el log.
        if elegido != "claude":
            print(f"[pensar] búsqueda pedida con {elegido}: va por Claude", file=sys.stderr)
        elegido = "claude"
        instrucciones = f"{instrucciones}\n\n{INSTRUCCIONES_BUSQUEDA}"
    try:
        if en_vivo:
            pensado = yield from _frases_del_motor(
                elegido, mensaje, instrucciones, indice, modo_pedido, nivel, buscar, modelo_ollama, modelo_venice
            )
        else:
            pensado = _respuesta_entera_del_motor(
                elegido, mensaje, instrucciones, indice, modo_pedido, nivel, buscar, modelo_ollama, modelo_venice
            )
    except LimiteDeClaude as limite:
        print(
            f"[pensar] Claude en su límite ({limite}): respaldo de charla por "
            f"{RESPALDO_DE_CHARLA[0]}/{RESPALDO_DE_CHARLA[1]}",
            file=sys.stderr,
        )
        pensado = _respaldo_de_charla(mensaje, instrucciones, len(indice))
        if pensado is not None and en_vivo:
            yield from _en_frases(_un_solo_delta(pensado.paso_minimo))

    # El turno de Juan Camilo se guarda siempre que se pensó; el de Remi,
    # solo si contestó. El voseo se quita acá, en la salida: lo que se
    # guarda, se muestra y (en el camino sin stream) se dice ya es de tú.
    # Cada frase del stream se convierte en `_en_frases`, antes de salir.
    conversacion_id = _guardar_turno("juan", frase)
    if pensado is not None:
        pensado = replace(pensado, paso_minimo=voseo.voseo_a_tu(pensado.paso_minimo))
        conversacion_id = _guardar_turno("remi", pensado.paso_minimo)
    _actualizar_resumen_en_segundo_plano(conversacion_id)
    if abre_conversacion_nueva:
        _cerrar_conversaciones_inactivas_en_segundo_plano()
    return pensado


def _respuesta_entera_del_motor(
    elegido: str,
    mensaje: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
    modo_pedido: str | None,
    nivel: str | None,
    buscar: bool,
    modelo_ollama: str | None,
    modelo_venice: str | None,
) -> Pensado | None:
    """El motor elegido, de una vez (sin público)."""
    if elegido == "venice":
        return _pensar_con_venice(mensaje, instrucciones, len(indice), modelo_venice)
    if elegido == "groq":
        return _pensar_con_charla("groq", "GROQ_API_KEY", mensaje, instrucciones, len(indice), modo_pedido)
    if elegido == "openrouter":
        return _pensar_con_charla("openrouter", "OPENROUTER_API_KEY", mensaje, instrucciones, len(indice), modo_pedido)
    if elegido == "ollama":
        return _pensar_con_ollama(mensaje, instrucciones, len(indice), modelo_ollama)
    return _pensar_con_claude(mensaje, instrucciones, indice, modo(modo_pedido), nivel, buscar)


def _frases_del_motor(
    elegido: str,
    mensaje: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
    modo_pedido: str | None,
    nivel: str | None,
    buscar: bool,
    modelo_ollama: str | None,
    modelo_venice: str | None,
) -> Frases:
    """El motor elegido, en frases y en vivo."""
    if elegido == "venice":
        return (yield from _en_frases(_charla_venice(mensaje, instrucciones, len(indice), modelo_venice, en_vivo=True)))
    if elegido == "groq":
        return (
            yield from _en_frases(
                _charla("groq", "GROQ_API_KEY", mensaje, instrucciones, len(indice), modo_pedido, en_vivo=True)
            )
        )
    if elegido == "openrouter":
        return (
            yield from _en_frases(
                _charla("openrouter", "OPENROUTER_API_KEY", mensaje, instrucciones, len(indice), modo_pedido, en_vivo=True)
            )
        )
    if elegido == "ollama":
        return (yield from _en_frases(_charla_ollama(mensaje, instrucciones, len(indice), modelo_ollama, en_vivo=True)))
    return (yield from _charla_claude(mensaje, instrucciones, indice, modo(modo_pedido), nivel, buscar, en_vivo=True))


# — Partir en frases (V3) —
#
# Mismo corte que `dividirEnFrases` en la ventanita (voz.ts): . ! ? …
# seguidos de espacio, o un salto de línea (cada renglón de una lista es
# una frase). Una frase muy corta («Ajá.») se pega a la siguiente: un audio
# por cada dos palabras suena entrecortado. «3.5» no corta (no hay espacio
# después del punto).
_FIN_DE_FRASE = re.compile(r"(?<=[.!?…])\s+|\n+")
PALABRAS_MINIMAS_POR_FRASE = 4


def _en_frases(deltas: Generator[str, None, Any]) -> Frases:
    """Convierte trozos de texto (como los suelta un motor) en oraciones
    completas. Devuelve lo que devuelva `deltas` al agotarse."""
    pendiente = ""
    corta = ""
    while True:
        try:
            pendiente += next(deltas)
        except StopIteration as fin:
            resultado: Pensado | None = fin.value
            break
        while True:
            corte = _FIN_DE_FRASE.search(pendiente)
            if corte is None:
                break
            completa = pendiente[: corte.start()].strip()
            pendiente = pendiente[corte.end() :]
            if not completa:
                continue
            corta = f"{corta} {completa}".strip()
            if len(corta.split()) >= PALABRAS_MINIMAS_POR_FRASE:
                yield voseo.voseo_a_tu(corta)
                corta = ""
    resto = f"{corta} {pendiente.strip()}".strip()
    if resto:
        yield voseo.voseo_a_tu(resto)
    return resultado


def _un_solo_delta(texto: str) -> Generator[str, None, None]:
    yield texto


# — Los OpenAI-compatibles: Venice, Groq, OpenRouter y Ollama comparten cliente y lector —


def _deltas_openai_compatible(
    url: str, clave: str | None, nombre_modelo: str, instrucciones: str, frase: str, timeout: float
) -> Generator[str, None, dict[str, Any]]:
    """La misma llamada que `_llamar_openai_compatible`, con `stream: true`:
    rinde cada trozo de texto al llegar y devuelve un JSON con la forma de
    la respuesta entera (choices[0].message.content, usage, model), para
    que `_leer_respuesta_venice` lo lea igual que siempre."""
    cabeceras = {"Content-Type": "application/json"}
    if clave:
        cabeceras["Authorization"] = f"Bearer {clave}"
    trozos: list[str] = []
    uso: dict[str, Any] = {}
    modelo_real = nombre_modelo
    with httpx.stream(
        "POST",
        url,
        headers=cabeceras,
        json={
            "model": nombre_modelo,
            "messages": [
                {"role": "system", "content": instrucciones},
                {"role": "user", "content": frase},
            ],
            "stream": True,
            "stream_options": {"include_usage": True},
        },
        timeout=timeout,
    ) as respuesta:
        respuesta.raise_for_status()
        for linea in respuesta.iter_lines():
            if not linea.startswith("data:"):
                continue
            dato = linea[5:].strip()
            if dato == "[DONE]":
                break
            try:
                trozo = json.loads(dato)
            except json.JSONDecodeError:
                continue
            if not isinstance(trozo, dict):
                continue
            if isinstance(trozo.get("usage"), dict):
                uso = trozo["usage"]
            if isinstance(trozo.get("model"), str):
                modelo_real = trozo["model"]
            for opcion in trozo.get("choices") or []:
                delta = opcion.get("delta") if isinstance(opcion, dict) else None
                contenido = delta.get("content") if isinstance(delta, dict) else None
                if isinstance(contenido, str) and contenido:
                    trozos.append(contenido)
                    yield contenido
    return {"choices": [{"message": {"content": "".join(trozos)}}], "usage": uso, "model": modelo_real}


def _llamar_openai_compatible(
    url: str, clave: str | None, nombre_modelo: str, instrucciones: str, frase: str, timeout: float
) -> dict[str, Any]:
    cabeceras = {"Content-Type": "application/json"}
    if clave:
        cabeceras["Authorization"] = f"Bearer {clave}"
    respuesta = httpx.post(
        url,
        headers=cabeceras,
        json={
            "model": nombre_modelo,
            "messages": [
                {"role": "system", "content": instrucciones},
                {"role": "user", "content": frase},
            ],
            # Un párrafo holgado; el carácter define el largo real.
            "max_tokens": 700,
        },
        timeout=timeout,
    )
    respuesta.raise_for_status()
    datos: dict[str, Any] = respuesta.json()
    return datos


def _llamar_venice(clave: str, nombre_modelo: str, instrucciones: str, frase: str) -> dict[str, Any]:
    return _llamar_openai_compatible(VENICE_URL, clave, nombre_modelo, instrucciones, frase, VENICE_TIMEOUT_SEGUNDOS)


def _llamar_ollama(nombre_modelo: str, instrucciones: str, frase: str) -> dict[str, Any]:
    return _llamar_openai_compatible(OLLAMA_URL, None, nombre_modelo, instrucciones, frase, OLLAMA_TIMEOUT_SEGUNDOS)


def _leer_respuesta_venice(
    datos: dict[str, Any], nombre_modelo: str, entradas: int, proveedor: str = "venice"
) -> Pensado | None:
    """Del JSON OpenAI-compatible al Pensado. None si no hay texto."""
    try:
        contenido = datos["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(contenido, str) or not contenido.strip():
        return None
    uso = datos.get("usage") if isinstance(datos.get("usage"), dict) else {}
    entrada = uso.get("prompt_tokens", 0) if isinstance(uso, dict) else 0
    salida = uso.get("completion_tokens", 0) if isinstance(uso, dict) else 0
    modelo_real = datos.get("model") if isinstance(datos.get("model"), str) else nombre_modelo
    return Pensado(
        paso_minimo=contenido.strip(),
        tokens_entrada=int(entrada) if isinstance(entrada, int) else 0,
        tokens_salida=int(salida) if isinstance(salida, int) else 0,
        modelo=f"{proveedor}/{modelo_real}",
        entradas_en_indice=entradas,
        leyo_memoria=False,
        motor_usado=proveedor,
    )


def _modelo_venice(pedido: str | None) -> str:
    """El del chip si es uno de los dos. Si no, el del entorno."""
    if pedido in MODELOS_VENICE:
        return pedido
    if pedido:
        print(f"[venice] modelo desconocido {pedido!r}: uso el del entorno", file=sys.stderr)
    return _ajuste("REMI_VENICE_MODELO", VENICE_MODELO_POR_DEFECTO)


def _pensar_con_venice(
    frase: str, instrucciones: str, entradas: int, modelo_pedido: str | None = None
) -> Pensado | None:
    return _agotar(_charla_venice(frase, instrucciones, entradas, modelo_pedido, en_vivo=False))


def _charla_venice(
    frase: str, instrucciones: str, entradas: int, modelo_pedido: str | None = None, en_vivo: bool = False
) -> Frases:
    clave = _ajuste("VENICE_API_KEY", "")
    if not clave:
        print("[venice] sin VENICE_API_KEY en nucleo/.env: sigo sin IA", file=sys.stderr)
        return None
    nombre_modelo = _modelo_venice(modelo_pedido)
    try:
        datos = (
            (yield from _deltas_openai_compatible(VENICE_URL, clave, nombre_modelo, instrucciones, frase, VENICE_TIMEOUT_SEGUNDOS))
            if en_vivo
            else _llamar_venice(clave, nombre_modelo, instrucciones, frase)
        )
    except httpx.HTTPStatusError as error:
        print(f"[venice] la API respondió {error.response.status_code}: sigo sin IA", file=sys.stderr)
        return None
    except httpx.HTTPError as error:
        print(f"[venice] sin conexión ({type(error).__name__}): sigo sin IA", file=sys.stderr)
        return None

    pensado = _leer_respuesta_venice(datos, nombre_modelo, entradas)
    if pensado is None:
        print("[venice] respuesta vacía: sigo sin IA", file=sys.stderr)
        return None
    print(
        f"[venice] modelo={pensado.modelo} tokens entrada={pensado.tokens_entrada} "
        f"salida={pensado.tokens_salida} memoria={entradas} leyó=no (sin herramientas)",
        file=sys.stderr,
    )
    return pensado


def _modelo_charla(proveedor: str, nivel_pedido: str | None) -> str | None:
    """El id de modelo de `proveedor` para charla, por nivel (rápido/
    equilibrio/inteligente) — siempre de config/motores.json → "charla",
    nunca a mano acá. None si el archivo no tiene esa sección o ese
    proveedor: el que llama decide qué hacer sin IA."""
    datos = _motores_json()
    charla = datos.get("charla") if isinstance(datos, dict) else None
    por_proveedor = charla.get(proveedor) if isinstance(charla, dict) else None
    if not isinstance(por_proveedor, dict):
        return None
    clave = nivel_pedido if nivel_pedido in por_proveedor else MODO_POR_DEFECTO
    modelo = por_proveedor.get(clave) or por_proveedor.get(MODO_POR_DEFECTO)
    return modelo if isinstance(modelo, str) and modelo else None


def _pensar_con_charla(
    proveedor: str, clave_env: str, frase: str, instrucciones: str, entradas: int, modo_pedido: str | None = None
) -> Pensado | None:
    return _agotar(_charla(proveedor, clave_env, frase, instrucciones, entradas, modo_pedido, en_vivo=False))


def _charla(
    proveedor: str,
    clave_env: str,
    frase: str,
    instrucciones: str,
    entradas: int,
    modo_pedido: str | None = None,
    en_vivo: bool = False,
) -> Frases:
    """Groq y OpenRouter en la charla: mismo cliente OpenAI-compatible que
    la trastienda, pero el id de modelo sale de config/motores.json → charla
    según el nivel pedido, y acá sí se guarda el turno (pensar() lo hace)."""
    clave = _ajuste(clave_env, "")
    if not clave:
        print(f"[{proveedor}] sin {clave_env} en nucleo/.env: sigo sin IA", file=sys.stderr)
        return None
    nombre_modelo = _modelo_charla(proveedor, modo_pedido)
    if nombre_modelo is None:
        print(f"[{proveedor}] sin modelo de charla en config/motores.json: sigo sin IA", file=sys.stderr)
        return None
    url, _ = PROVEEDORES_TRASTIENDA[proveedor]
    arranque = time.perf_counter()
    try:
        datos = (
            (yield from _deltas_openai_compatible(url, clave, nombre_modelo, instrucciones, frase, TRASTIENDA_TIMEOUT_SEGUNDOS))
            if en_vivo
            else _llamar_openai_compatible(url, clave, nombre_modelo, instrucciones, frase, TRASTIENDA_TIMEOUT_SEGUNDOS)
        )
    except httpx.HTTPStatusError as error:
        print(f"[{proveedor}] la API respondió {error.response.status_code}: sigo sin IA", file=sys.stderr)
        return None
    except httpx.HTTPError as error:
        print(f"[{proveedor}] sin conexión ({type(error).__name__}): sigo sin IA", file=sys.stderr)
        return None
    ms = (time.perf_counter() - arranque) * 1000

    pensado = _leer_respuesta_venice(datos, nombre_modelo, entradas, proveedor=proveedor)
    if pensado is None:
        print(f"[{proveedor}] respuesta vacía: sigo sin IA", file=sys.stderr)
        return None
    print(
        f"[{proveedor}] modelo={pensado.modelo} ms={ms:.0f} tokens entrada={pensado.tokens_entrada} "
        f"salida={pensado.tokens_salida} memoria={entradas} leyó=no (sin herramientas)",
        file=sys.stderr,
    )
    return pensado


def _llamar_proveedor(proveedor: str, nombre_modelo: str, instrucciones: str, frase: str) -> dict[str, Any]:
    url, clave_env = PROVEEDORES_TRASTIENDA[proveedor]
    clave = _ajuste(clave_env, "") if clave_env else None
    return _llamar_openai_compatible(url, clave, nombre_modelo, instrucciones, frase, TRASTIENDA_TIMEOUT_SEGUNDOS)


def _motores_json() -> dict[str, Any]:
    """El contenido de config/motores.json (o REMI_MOTORES en pruebas).
    {} si el archivo no está o no es JSON válido — quien llama decide el
    default, esto nunca lanza."""
    ruta = Path(os.environ.get("REMI_MOTORES") or RUTA_MOTORES)
    try:
        datos = json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return datos if isinstance(datos, dict) else {}


def trastienda() -> list[tuple[str, str]]:
    """[(proveedor, modelo), ...] de `config/motores.json`, en orden. Si el
    archivo no está, no es JSON, o no trae una lista `trastienda` usable, la
    cadena por defecto (la misma que documenta ese archivo)."""
    datos = _motores_json()
    lista = datos.get("trastienda") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        return list(TRASTIENDA_POR_DEFECTO)
    resultado: list[tuple[str, str]] = []
    for entrada in lista:
        if not isinstance(entrada, str) or "/" not in entrada:
            continue
        proveedor, _, modelo = entrada.partition("/")
        if proveedor in PROVEEDORES_TRASTIENDA and modelo:
            resultado.append((proveedor, modelo))
    return resultado or list(TRASTIENDA_POR_DEFECTO)


def pensar_con_trastienda(
    pedido: str, instrucciones: str, aceptar: Callable[[Pensado], bool] | None = None
) -> Pensado | None:
    """El primer motor de `trastienda()` que conteste — y que `aceptar` (si
    lo pasan) acepte; si no, sigue con el próximo. None si ninguno sirvió.
    Para tareas de fondo (resumen vivo, claves, títulos de episodios,
    consolidación nocturna): nunca la charla, que va por `pensar()`."""
    for proveedor, modelo in trastienda():
        try:
            datos = _llamar_proveedor(proveedor, modelo, instrucciones, pedido)
        except httpx.HTTPError as error:
            print(
                f"[trastienda] {proveedor}/{modelo} no contestó ({type(error).__name__}): "
                "sigo con el siguiente",
                file=sys.stderr,
            )
            continue
        pensado = _leer_respuesta_venice(datos, modelo, 0, proveedor=proveedor)
        if pensado is None:
            print(f"[trastienda] {proveedor}/{modelo} respuesta vacía: sigo con el siguiente", file=sys.stderr)
            continue
        if aceptar is not None and not aceptar(pensado):
            print(f"[trastienda] {proveedor}/{modelo} rechazado: sigo con el siguiente", file=sys.stderr)
            continue
        return pensado
    return None


def _respaldo_de_charla(frase: str, instrucciones: str, entradas: int) -> Pensado | None:
    """Un solo intento, directo (sin cadena): Claude ya avisó que está en su
    límite, y esto es charla — nadie quiere esperar una cadena entera de
    reintentos fallidos antes de contestar."""
    proveedor, modelo = RESPALDO_DE_CHARLA
    try:
        datos = _llamar_proveedor(proveedor, modelo, instrucciones, frase)
    except httpx.HTTPError as error:
        print(f"[respaldo] {proveedor}/{modelo} no contestó ({type(error).__name__}): sigo sin IA", file=sys.stderr)
        return None
    pensado = _leer_respuesta_venice(datos, modelo, entradas, proveedor=proveedor)
    if pensado is None:
        print(f"[respaldo] {proveedor}/{modelo} respuesta vacía: sigo sin IA", file=sys.stderr)
        return None
    print(
        f"[respaldo] modelo={pensado.modelo} tokens entrada={pensado.tokens_entrada} "
        f"salida={pensado.tokens_salida} memoria={entradas}",
        file=sys.stderr,
    )
    return pensado


# — Ollama (local) —


def modelos_de_ollama() -> list[str]:
    """Lo que devuelve `ollama list`, por su API. Vacío si no está."""
    try:
        respuesta = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=2.0)
        respuesta.raise_for_status()
        return sorted(m["name"] for m in respuesta.json().get("models", []) if isinstance(m, dict) and "name" in m)
    except (httpx.HTTPError, ValueError, KeyError):
        return []


def _pensar_con_ollama(frase: str, instrucciones: str, entradas: int, modelo_pedido: str | None = None) -> Pensado | None:
    return _agotar(_charla_ollama(frase, instrucciones, entradas, modelo_pedido, en_vivo=False))


def _charla_ollama(
    frase: str, instrucciones: str, entradas: int, modelo_pedido: str | None = None, en_vivo: bool = False
) -> Frases:
    nombre_modelo = modelo_pedido or _ajuste("REMI_OLLAMA_MODELO", OLLAMA_MODELO_POR_DEFECTO)
    try:
        datos = (
            (yield from _deltas_openai_compatible(OLLAMA_URL, None, nombre_modelo, instrucciones, frase, OLLAMA_TIMEOUT_SEGUNDOS))
            if en_vivo
            else _llamar_ollama(nombre_modelo, instrucciones, frase)
        )
    except httpx.HTTPStatusError as error:
        print(f"[ollama] respondió {error.response.status_code} (¿falta `ollama pull {nombre_modelo}`?): sigo sin IA", file=sys.stderr)
        return None
    except httpx.HTTPError as error:
        print(f"[ollama] no está sirviendo ({type(error).__name__}): sigo sin IA", file=sys.stderr)
        return None

    pensado = _leer_respuesta_venice(datos, nombre_modelo, entradas, proveedor="ollama")
    if pensado is None:
        print("[ollama] respuesta vacía: sigo sin IA", file=sys.stderr)
        return None
    print(
        f"[ollama] modelo={pensado.modelo} tokens entrada={pensado.tokens_entrada} "
        f"salida={pensado.tokens_salida} memoria={entradas} leyó=no (sin herramientas) · local",
        file=sys.stderr,
    )
    return pensado


# — Claude (la membresía Max, por la CLI) —


def _pensar_con_claude(
    frase: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
    elegido: Modo | None = None,
    nivel: str | None = None,
    buscar: bool = False,
) -> Pensado | None:
    """El modo elegido (con su nivel); si falla o se pasa de su techo, el anterior."""
    return _agotar(_charla_claude(frase, instrucciones, indice, elegido, nivel, buscar, en_vivo=False))


def _charla_claude(
    frase: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
    elegido: Modo | None = None,
    nivel: str | None = None,
    buscar: bool = False,
    en_vivo: bool = False,
) -> Frases:
    """La cadena de modos, en frases. En vivo, un modo que ya soltó alguna
    frase y después falló no cae al anterior (lo dicho ya se oyó)."""
    elegido = MODOS[MODO_POR_DEFECTO] if elegido is None else elegido
    cadena = cadena_de_modos(elegido)
    cadena[0] = con_nivel(cadena[0], nivel)
    for i, m in enumerate(cadena):
        if not en_vivo:
            pensado = _una_llamada_claude(m, frase, instrucciones, indice, buscar)
        else:
            dichas = 0
            frases = _en_frases(_deltas_claude(m, frase, instrucciones, indice, buscar))
            try:
                while True:
                    frase_lista = next(frases)
                    dichas += 1
                    yield frase_lista
            except StopIteration as fin:
                pensado = fin.value
            if pensado is None and dichas:
                print(f"[claude] modo={m.nombre} falló después de {dichas} frase(s): sigo sin IA", file=sys.stderr)
                return None
        if pensado is not None:
            return pensado
        if i + 1 < len(cadena):
            print(f"[claude] modo={m.nombre} no contestó: caigo a {cadena[i + 1].nombre}", file=sys.stderr)
    return None


# cwd de la CLI: una carpeta vacía y SIEMPRE la misma. La CLI escribe su
# carpeta de trabajo en el prompt; una temporal distinta por llamada
# reescribía ~855 tokens de caché en cada turno (medido 2/10/2026). Vacía
# para que no cargue CLAUDE.md ni contexto de ningún repo.
CARPETA_CWD = Path(tempfile.gettempdir()) / "remi-pensar-cwd"


def _cwd_de_la_cli() -> Path:
    CARPETA_CWD.mkdir(parents=True, exist_ok=True)
    return CARPETA_CWD


def _una_llamada_claude(
    m: Modo,
    frase: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
    buscar: bool = False,
) -> Pensado | None:
    nombre_modelo = m.modelo
    timeout = m.techo_segundos
    arranque = time.perf_counter()
    try:
        # La config del MCP y la marca de lectura son de esta llamada (una
        # carpeta temporal); el cwd no: es el fijo de arriba.
        with tempfile.TemporaryDirectory(prefix="remi-pensar-") as vacio:
            marca = Path(vacio) / "leyo"
            terminado = subprocess.run(
                _comando(nombre_modelo, instrucciones, _config_mcp(Path(vacio), marca), buscar),
                input=frase,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_entorno(m),
                cwd=_cwd_de_la_cli(),
            )
            # El JSON final de la CLI no dice qué herramientas usó; la marca
            # la deja el propio estante al ser leído. Hay que mirarla antes
            # de que la carpeta temporal desaparezca.
            libros = marca.read_text().split() if marca.exists() else []
    except FileNotFoundError:
        print(f"[claude] no encontré `{BINARIO}` en el PATH: sigo sin IA", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"[claude] {nombre_modelo} tardó más de {timeout:.0f} s", file=sys.stderr)
        return None
    except OSError as error:
        print(f"[claude] no pude correr la CLI ({error}): sigo sin IA", file=sys.stderr)
        return None

    if terminado.returncode != 0:
        print(
            f"[claude] la CLI terminó en {terminado.returncode}: sigo sin IA",
            file=sys.stderr,
        )
        return None

    try:
        datos = json.loads(terminado.stdout)
    except json.JSONDecodeError:
        print("[claude] no entendí la respuesta de la CLI: sigo sin IA", file=sys.stderr)
        return None
    if not isinstance(datos, dict):
        print("[claude] la CLI no devolvió un objeto: sigo sin IA", file=sys.stderr)
        return None
    return _pensado_de_la_cli(m, datos, indice, libros, arranque)


def _deltas_claude(
    m: Modo,
    frase: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
    buscar: bool = False,
) -> Generator[str, None, Pensado | None]:
    """La misma llamada que `_una_llamada_claude`, con `--output-format
    stream-json --include-partial-messages`: rinde cada trozo de texto del
    modelo al llegar (un salto de línea al cerrar cada mensaje, para que el
    corte en frases no pegue dos mensajes) y al final lee la línea `result`
    igual que siempre. El techo de tiempo lo pone un temporizador que mata
    el proceso: lo que ya se dijo, se dijo."""
    nombre_modelo = m.modelo
    timeout = m.techo_segundos
    arranque = time.perf_counter()
    datos: Any = None
    with tempfile.TemporaryDirectory(prefix="remi-pensar-") as vacio:
        marca = Path(vacio) / "leyo"
        comando = _comando(nombre_modelo, instrucciones, _config_mcp(Path(vacio), marca), buscar)
        comando[comando.index("--output-format") + 1] = "stream-json"
        comando += ["--include-partial-messages", "--verbose"]
        try:
            proceso = subprocess.Popen(
                comando,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                env=_entorno(m),
                cwd=_cwd_de_la_cli(),
            )
        except FileNotFoundError:
            print(f"[claude] no encontré `{BINARIO}` en el PATH: sigo sin IA", file=sys.stderr)
            return None
        except OSError as error:
            print(f"[claude] no pude correr la CLI ({error}): sigo sin IA", file=sys.stderr)
            return None
        vencido = threading.Event()

        def matar() -> None:
            vencido.set()
            proceso.kill()

        reloj = threading.Timer(timeout, matar)
        reloj.start()
        try:
            assert proceso.stdin is not None and proceso.stdout is not None
            try:
                proceso.stdin.write(frase)
                proceso.stdin.close()
            except OSError:
                pass
            for linea in proceso.stdout:
                try:
                    evento = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if not isinstance(evento, dict):
                    continue
                if evento.get("type") == "result":
                    datos = evento
                    continue
                if evento.get("type") != "stream_event":
                    continue
                interno = evento.get("event")
                if not isinstance(interno, dict):
                    continue
                if interno.get("type") == "content_block_delta":
                    delta = interno.get("delta")
                    if isinstance(delta, dict) and delta.get("type") == "text_delta":
                        texto = delta.get("text")
                        if isinstance(texto, str) and texto:
                            yield texto
                elif interno.get("type") == "message_stop":
                    yield "\n"
            proceso.wait()
        finally:
            reloj.cancel()
        libros = marca.read_text().split() if marca.exists() else []

    if vencido.is_set():
        print(f"[claude] {nombre_modelo} tardó más de {timeout:.0f} s", file=sys.stderr)
        return None
    if proceso.returncode != 0:
        print(f"[claude] la CLI terminó en {proceso.returncode}: sigo sin IA", file=sys.stderr)
        return None
    if not isinstance(datos, dict):
        print("[claude] la CLI no cerró con un resultado: sigo sin IA", file=sys.stderr)
        return None
    return _pensado_de_la_cli(m, datos, indice, libros, arranque)


def _pensado_de_la_cli(
    m: Modo, datos: dict[str, Any], indice: list[db.EntradaIndice], libros: list[str], arranque: float
) -> Pensado | None:
    """Del JSON final de la CLI (el de `--output-format json`, o la línea
    `result` del stream) al Pensado, con la línea de log de siempre."""
    nombre_modelo = m.modelo
    leyo = bool(libros)
    tokens_entrada, tokens_salida = _tokens(datos.get("usage"))
    cache_leida, cache_escrita = _tokens_cacheados(datos.get("usage"))
    modelo_real = _modelo_real(datos, nombre_modelo)
    ms = (time.perf_counter() - arranque) * 1000
    api_ms = datos.get("duration_api_ms")
    # La cuenta va a consola, no a la pantalla: es dato de operación.
    # `entrada` es solo lo no cacheado (así lo informa la CLI); lo que viajó
    # de verdad es entrada + cache_leida + cache_escrita. `api` es lo que
    # tardó el modelo según la CLI; la diferencia con `ms` es el arranque
    # de la CLI (node + el estante), ~1,5 s medidos.
    print(
        f"[claude] modo={m.nombre} modelo={modelo_real} ms={ms:.0f} "
        f"api={api_ms if isinstance(api_ms, int) else '-'} "
        f"tokens entrada={tokens_entrada} cache_leida={cache_leida} cache_escrita={cache_escrita} "
        f"salida={tokens_salida} memoria={len(indice)} "
        f"leyó={'sí' if leyo else 'no'} libros={','.join(libros) or '-'}",
        file=sys.stderr,
    )

    # Con is_error, `result` trae el TEXTO DEL ERROR ("API Error: …"): eso
    # jamás puede terminar siendo la voz de Remi.
    if datos.get("is_error"):
        texto_error = str(datos.get("result") or "")
        print(f"[claude] la CLI avisó un error: {texto_error!r}", file=sys.stderr)
        if PATRON_LIMITE_ALCANZADO.search(texto_error):
            raise LimiteDeClaude(texto_error)
        return None

    paso = datos.get("result")
    if not isinstance(paso, str) or not paso.strip():
        print("[claude] respuesta vacía: sigo sin IA", file=sys.stderr)
        return None

    return Pensado(
        paso_minimo=paso.strip(),
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        modelo=modelo_real,
        entradas_en_indice=len(indice),
        leyo_memoria=leyo,
        motor_usado="claude",
    )

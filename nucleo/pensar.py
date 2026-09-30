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
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

import db

BINARIO = "claude"
# Las claves viven en nucleo/.env (fuera del repo). Se leen a un dict y NUNCA
# se exportan al entorno: la CLI de Claude no tiene por qué ver la de Venice.
RUTA_ENV = Path(__file__).resolve().parent / ".env"
# Motores: "claude" (la membresía Max, por la CLI, con acceso al estante) y
# los OpenAI-compatibles, que comparten un solo cliente y no tienen
# herramientas —el índice viaja en el system prompt pero no pueden bajar
# nada del estante—: "venice" (pago por token) y "ollama" (local, gratis,
# nada sale del Mac).
MOTOR_POR_DEFECTO = "claude"
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
VENICE_MODELO_POR_DEFECTO = "venice-uncensored"
VENICE_TIMEOUT_SEGUNDOS = 20.0
OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_URL = f"{OLLAMA_BASE}/v1/chat/completions"
# gemma3:4b: buen español, ~3,3 GB, cabe holgado en 16 GB y contesta en
# un par de segundos en un M4. Se cambia con REMI_OLLAMA_MODELO.
OLLAMA_MODELO_POR_DEFECTO = "gemma3:4b"
# Local, pero un modelo frío tarda en cargar a memoria la primera vez.
OLLAMA_TIMEOUT_SEGUNDOS = 30.0
SERVIDOR_MEMORIA = Path(__file__).resolve().parent / "memoria_mcp.py"
# Las únicas dos cosas que la CLI puede hacer además de contestar. El
# prefijo `mcp__memoria__` lo arma Claude Code con el nombre del servidor.
HERRAMIENTAS = ("mcp__memoria__leer", "mcp__memoria__guardar")
# Con una sola vuelta no le alcanza para leer del estante y después
# responder. Tres son: pide la lectura, la recibe, contesta.
MAX_VUELTAS = "3"
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
    "rapido": Modo("rapido", "haiku", 8.0, 0, 1500),
    "equilibrio": Modo("equilibrio", "sonnet", 25.0, 0, 1500),
    "inteligente": Modo("inteligente", "opus", 60.0, 8000, 16000),
}
ORDEN_DE_MODOS = ("rapido", "equilibrio", "inteligente")
MODO_POR_DEFECTO = "equilibrio"
# Compatibilidad con quien lo lea: el modelo del modo por defecto.
MODELO_POR_DEFECTO = MODOS[MODO_POR_DEFECTO].modelo
# El peor caso: inteligente agota sus 60 s, equilibrio sus 25 y rápido sus
# 8. La ventanita espera por encima de eso (pruebas/test_timeouts.py).
PEOR_CASO_SEGUNDOS = sum(m.techo_segundos for m in MODOS.values())

# El carácter de Remi ES el system prompt (Fase 3a). Vive en el disco, fuera
# del repo (datos personales), y se lee en CADA mensaje: si Juan Camilo lo
# edita, Remi cambia sin reiniciar nada. REMI_CARACTER apunta a otro archivo
# (las pruebas lo usan).
RUTA_CARACTER = Path(__file__).resolve().parent.parent / "conocimiento" / "caracter.md"

# La conversación: cada llamada lleva los últimos 12 turnos de la última
# hora. Pasada la hora, conversación nueva.
MAX_TURNOS = 12
VENTANA_CONVERSACION_MINUTOS = 60

# Solo si el archivo no está: un Remi mínimo, para no quedarse mudo.
CARACTER_DE_RESPALDO = (
    "Sos Remi, el socio de Juan Camilo. Le hablás de tú, en español de Colombia, "
    "corto y directo: primero la respuesta. Nunca urgís, nunca contás fallos, nunca "
    "inventás datos de sus proyectos: si no está en tu memoria, lo decís."
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
    "\n\nEsto es lo que ya sabés. Cada línea es algo que te contaron antes: "
    "[id] fecha · tema · título — con qué te quedaste.\n"
    "El resumen te dice CUÁL es cada cosa, no alcanza para contestar sobre ella. "
    "Si te preguntan por algo de esta lista, bajalo con la herramienta `leer` "
    "usando su id, y recién entonces contestá. Y si te cuentan algo que valga la "
    "pena recordar, guardalo con `guardar` — solo eso, no cada tarea suelta.\n"
)


def _linea_indice(entrada: db.EntradaIndice) -> str:
    corto = str(entrada.id)[:8]
    fecha = entrada.fecha.date().isoformat()
    linea = f"[{corto}] {fecha} · {entrada.tema} · {entrada.titulo} — {entrada.resumen}"
    return f"{linea} (claves: {entrada.claves})" if entrada.claves else linea


def instrucciones_con_indice(indice: list[db.EntradaIndice]) -> str:
    """El carácter más lo que Remi tiene presente. Sin entradas no se anexa
    nada: un encabezado solo, sin líneas, invitaría a inventar."""
    base = caracter()
    if not indice:
        return base
    lineas = "\n".join(_linea_indice(entrada) for entrada in indice)
    return base + ENCABEZADO_INDICE + lineas


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


def cadena_de_modos(elegido: Modo) -> list[Modo]:
    """El elegido y, si falla, los anteriores: inteligente → equilibrio → rápido."""
    hasta = ORDEN_DE_MODOS.index(elegido.nombre)
    return [MODOS[n] for n in reversed(ORDEN_DE_MODOS[: hasta + 1])]


MOTORES = ("claude", "venice", "ollama")


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
    hay_clave = bool(_ajuste("VENICE_API_KEY", ""))
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
            disponible=hay_clave,
            detalle=(
                f"{_ajuste('REMI_VENICE_MODELO', VENICE_MODELO_POR_DEFECTO)}, sin acceso al estante"
                if hay_clave
                else "sin VENICE_API_KEY en nucleo/.env"
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


def _comando(nombre_modelo: str, instrucciones: str, config_mcp: Path) -> list[str]:
    return [
        BINARIO,
        "-p",
        "--model",
        nombre_modelo,
        "--output-format",
        "json",
        "--system-prompt",
        instrucciones,
        # El encierro no se afloja: sin herramientas de la casa, sin
        # settings del usuario, sin sesión en disco. Lo único que se abre
        # es el estante, y solo esas dos puertas.
        "--tools",
        "",
        "--restricted",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--mcp-config",
        str(config_mcp),
        "--allowedTools",
        ",".join(HERRAMIENTAS),
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


def _turnos() -> list[db.Turno]:
    from datetime import datetime, timedelta, timezone

    desde = datetime.now(timezone.utc) - timedelta(minutes=VENTANA_CONVERSACION_MINUTOS)
    try:
        conexion = db.conectar()
    except Exception:
        return []
    try:
        return db.turnos_recientes(conexion, desde, MAX_TURNOS)
    finally:
        conexion.close()


def _guardar_turno(rol: str, texto: str) -> None:
    from datetime import datetime, timezone

    try:
        conexion = db.conectar()
    except Exception:
        return
    try:
        db.guardar_turno(conexion, rol, texto, datetime.now(timezone.utc))
    finally:
        conexion.close()


def mensaje_con_historia(frase: str, turnos: list[db.Turno]) -> str:
    """Lo que viaja como mensaje: la conversación reciente y, al final, lo
    que Juan Camilo acaba de decir. Sin turnos, la frase sola."""
    if not turnos:
        return frase
    lineas = [
        f"{'Juan Camilo' if t.rol == 'juan' else 'Remi'}: {t.texto}" for t in turnos
    ]
    return (
        "Conversación de la última hora (lo más viejo primero):\n"
        + "\n".join(lineas)
        + f"\n\nAhora Juan Camilo dice:\n{frase}"
    )


def pensar(frase: str, motor_pedido: str | None = None, modo_pedido: str | None = None) -> Pensado | None:
    """Lo que el motor elegido contesta a `frase`, con la conversación de la
    última hora. None si el motor no está, falla o no devolvió texto: el que
    llama sigue por el camino sin IA — nunca se rompe la respuesta por esto."""
    indice = _indice()
    instrucciones = instrucciones_con_indice(indice)
    mensaje = mensaje_con_historia(frase, _turnos())
    elegido = motor(motor_pedido)
    if elegido == "venice":
        pensado = _pensar_con_venice(mensaje, instrucciones, len(indice))
    elif elegido == "ollama":
        pensado = _pensar_con_ollama(mensaje, instrucciones, len(indice))
    else:
        pensado = _pensar_con_claude(mensaje, instrucciones, indice, modo(modo_pedido))

    # El turno de Juan Camilo se guarda siempre que se pensó; el de Remi,
    # solo si contestó.
    _guardar_turno("juan", frase)
    if pensado is not None:
        _guardar_turno("remi", pensado.paso_minimo)
    return pensado


# — Los OpenAI-compatibles: Venice y Ollama comparten cliente y lector —


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
    )


def _pensar_con_venice(frase: str, instrucciones: str, entradas: int) -> Pensado | None:
    clave = _ajuste("VENICE_API_KEY", "")
    if not clave:
        print("[venice] sin VENICE_API_KEY en nucleo/.env: sigo sin IA", file=sys.stderr)
        return None
    nombre_modelo = _ajuste("REMI_VENICE_MODELO", VENICE_MODELO_POR_DEFECTO)
    try:
        datos = _llamar_venice(clave, nombre_modelo, instrucciones, frase)
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


# — Ollama (local) —


def _pensar_con_ollama(frase: str, instrucciones: str, entradas: int) -> Pensado | None:
    nombre_modelo = _ajuste("REMI_OLLAMA_MODELO", OLLAMA_MODELO_POR_DEFECTO)
    try:
        datos = _llamar_ollama(nombre_modelo, instrucciones, frase)
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
    frase: str, instrucciones: str, indice: list[db.EntradaIndice], elegido: Modo | None = None
) -> Pensado | None:
    """El modo elegido; si falla o se pasa de su techo, el anterior."""
    elegido = MODOS[MODO_POR_DEFECTO] if elegido is None else elegido
    cadena = cadena_de_modos(elegido)
    for i, m in enumerate(cadena):
        pensado = _una_llamada_claude(m, frase, instrucciones, indice)
        if pensado is not None:
            return pensado
        if i + 1 < len(cadena):
            print(f"[claude] modo={m.nombre} no contestó: caigo a {cadena[i + 1].nombre}", file=sys.stderr)
    return None


def _una_llamada_claude(
    m: Modo,
    frase: str,
    instrucciones: str,
    indice: list[db.EntradaIndice],
) -> Pensado | None:
    nombre_modelo = m.modelo
    timeout = m.techo_segundos
    import time

    arranque = time.perf_counter()
    try:
        # cwd neutral: dentro del repo la CLI cargaría CLAUDE.md y contexto
        # que acá no pinta nada.
        with tempfile.TemporaryDirectory(prefix="remi-pensar-") as vacio:
            marca = Path(vacio) / "leyo"
            terminado = subprocess.run(
                _comando(nombre_modelo, instrucciones, _config_mcp(Path(vacio), marca)),
                input=frase,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_entorno(m),
                cwd=vacio,
            )
            # El JSON final de la CLI no dice qué herramientas usó; la marca
            # la deja el propio estante al ser leído. Hay que mirarla antes
            # de que la carpeta temporal desaparezca.
            leyo = marca.exists()
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

    tokens_entrada, tokens_salida = _tokens(datos.get("usage"))
    modelo_real = _modelo_real(datos, nombre_modelo)
    ms = (time.perf_counter() - arranque) * 1000
    # La cuenta va a consola, no a la pantalla: es dato de operación.
    print(
        f"[claude] modo={m.nombre} modelo={modelo_real} ms={ms:.0f} tokens entrada={tokens_entrada} "
        f"salida={tokens_salida} memoria={len(indice)} "
        f"leyó={'sí' if leyo else 'no'}",
        file=sys.stderr,
    )

    # Con is_error, `result` trae el TEXTO DEL ERROR ("API Error: …"): eso
    # jamás puede terminar siendo la voz de Remi.
    if datos.get("is_error"):
        print(f"[claude] la CLI avisó un error: {datos.get('result')!r}", file=sys.stderr)
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
    )

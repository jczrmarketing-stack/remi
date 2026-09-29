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
# Ordenar un paso mínimo no necesita más. REMI_CLAUDE_MODELO lo cambia
# (en 2e.1 se comparan); vale cualquier alias que acepte la CLI.
MODELO_POR_DEFECTO = "haiku"
# El techo cuenta TODA la salida, y ahí entra el JSON de las llamadas a las
# herramientas: con 200, `guardar` una idea de verdad se corta a la mitad y
# la CLI devuelve "exceeded the 200 output token maximum" sin guardar nada.
# 1500 alcanza para bajar algo del estante, guardar algo nuevo y contestar;
# la frase de Remi la sigue recortando el servidor a 20 palabras.
MAX_TOKENS_SALIDA = "1500"
# Contestar solo tarda ~2 s; leer del estante ~3,5 s; guardar algo largo
# llega a 10 s. Ojo: la ventanita corta su propio fetch a los 8 s, así que
# un guardado largo pedido desde ahí igual se completa en el núcleo aunque
# la ventanita ya haya contestado sin IA.
TIMEOUT_SEGUNDOS = 20.0

INSTRUCCIONES = (
    "Te dan una frase suelta. Si es una tarea, una idea o un pendiente, respondé "
    "con UNA sola acción concreta para empezarla, tan chica que se pueda hacer en "
    "cinco minutos; si la frase es vaga, elegí igual un primer paso razonable y "
    "nunca pidas más detalles. Si en cambio te preguntan algo que ya sabés, "
    "contestá la pregunta con lo que sabés. "
    "Siempre: en español, hablándole de tú, máximo 20 palabras, una sola frase. "
    "Sin exclamaciones, sin explicar de más, sin listas, sin comillas, sin "
    "saludos. Respondé solo con esa frase y nada más."
)

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
    return f"[{corto}] {fecha} · {entrada.tema} · {entrada.titulo} — {entrada.resumen}"


def instrucciones_con_indice(indice: list[db.EntradaIndice]) -> str:
    """Las instrucciones más lo que Remi tiene presente. Sin entradas no se
    anexa nada: un encabezado solo, sin líneas, invitaría a inventar."""
    if not indice:
        return INSTRUCCIONES
    lineas = "\n".join(_linea_indice(entrada) for entrada in indice)
    return INSTRUCCIONES + ENCABEZADO_INDICE + lineas


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
    return _ajuste("REMI_CLAUDE_MODELO", MODELO_POR_DEFECTO)


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
            label="Venice (por token)",
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


def _entorno() -> dict[str, str]:
    """El entorno del subproceso, sin credenciales de API. Si Milo tiene una
    clave exportada, la CLI la usaría y eso se factura por fuera del plan —
    justo lo que hay que evitar."""
    entorno = dict(os.environ)
    for clave in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        entorno.pop(clave, None)
    # El razonamiento cuenta contra el techo de salida: apagado, 200 alcanzan.
    entorno["MAX_THINKING_TOKENS"] = "0"
    entorno["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = MAX_TOKENS_SALIDA
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


def pensar(frase: str, motor_pedido: str | None = None) -> Pensado | None:
    """Lo que el motor elegido contesta a `frase`. None si el motor no está,
    falla o no devolvió texto: el que llama sigue por el camino sin IA —
    nunca se rompe la respuesta por esto."""
    indice = _indice()
    instrucciones = instrucciones_con_indice(indice)
    elegido = motor(motor_pedido)
    if elegido == "venice":
        return _pensar_con_venice(frase, instrucciones, len(indice))
    if elegido == "ollama":
        return _pensar_con_ollama(frase, instrucciones, len(indice))
    return _pensar_con_claude(frase, instrucciones, indice)


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
            "max_tokens": 200,
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


def _pensar_con_claude(frase: str, instrucciones: str, indice: list[db.EntradaIndice]) -> Pensado | None:
    nombre_modelo = modelo()
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
                timeout=TIMEOUT_SEGUNDOS,
                env=_entorno(),
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
        print(f"[claude] tardó más de {TIMEOUT_SEGUNDOS:.0f} s: sigo sin IA", file=sys.stderr)
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
    # La cuenta va a consola, no a la pantalla: es dato de operación.
    print(
        f"[claude] modelo={modelo_real} tokens entrada={tokens_entrada} "
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

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

import db

BINARIO = "claude"
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


def modelo() -> str:
    return os.environ.get("REMI_CLAUDE_MODELO") or MODELO_POR_DEFECTO


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


def pensar(frase: str) -> Pensado | None:
    """El paso mínimo que Claude ordena para `frase`. None si la CLI no está,
    si falla o si no devolvió texto: el que llama sigue por el camino sin IA
    — nunca se rompe la respuesta por esto."""
    nombre_modelo = modelo()
    indice = _indice()
    instrucciones = instrucciones_con_indice(indice)
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

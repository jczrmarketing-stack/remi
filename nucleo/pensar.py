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
from typing import Any

BINARIO = "claude"
# Ordenar un paso mínimo no necesita más. REMI_CLAUDE_MODELO lo cambia
# (en 2e.1 se comparan); vale cualquier alias que acepte la CLI.
MODELO_POR_DEFECTO = "haiku"
# Un paso mínimo son ≤20 palabras. El techo cuenta TODA la salida, y el
# razonamiento del modelo entra ahí: sin apagarlo (MAX_THINKING_TOKENS=0)
# 200 tokens no alcanzan ni para frases cortas y la CLI devuelve error.
MAX_TOKENS_SALIDA = "200"
# La ventanita corta el fetch a los 8 s; una llamada real tarda ~2 s.
TIMEOUT_SEGUNDOS = 6.0

INSTRUCCIONES = (
    "Te dan una frase suelta: una tarea, una idea o un pendiente. Respondé con UNA "
    "sola acción concreta para empezarla, tan chica que se pueda hacer en cinco "
    "minutos. En español, hablándole de tú, en imperativo, máximo 20 palabras. Sin "
    "exclamaciones, sin explicar, sin preguntar, sin listas, sin comillas, sin "
    "saludos. Si la frase es vaga, elegí igual un primer paso razonable: nunca "
    "pidas más detalles. Respondé solo con esa frase y nada más."
)


@dataclass(frozen=True)
class Pensado:
    paso_minimo: str
    tokens_entrada: int
    tokens_salida: int
    modelo: str


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


def _comando(nombre_modelo: str) -> list[str]:
    return [
        BINARIO,
        "-p",
        "--model",
        nombre_modelo,
        "--output-format",
        "json",
        "--system-prompt",
        INSTRUCCIONES,
        # Remi solo quiere una frase: nada de herramientas, ni MCP, ni
        # settings del usuario, ni sesión guardada en disco.
        "--tools",
        "",
        "--restricted",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--max-turns",
        "1",
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
    try:
        # cwd neutral: dentro del repo la CLI cargaría CLAUDE.md y contexto
        # que acá no pinta nada.
        with tempfile.TemporaryDirectory(prefix="remi-pensar-") as vacio:
            terminado = subprocess.run(
                _comando(nombre_modelo),
                input=frase,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SEGUNDOS,
                env=_entorno(),
                cwd=vacio,
            )
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
        f"[claude] modelo={modelo_real} tokens entrada={tokens_entrada} salida={tokens_salida}",
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
    )

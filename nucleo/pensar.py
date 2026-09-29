"""Pensar con Claude, opt-in por mensaje (think=true). Por defecto Remi no
gasta un token: este módulo solo corre si la ventanita lo pide explícito.

La clave vive en nucleo/.env (ANTHROPIC_API_KEY=…), jamás en el repo — el
.gitignore de la raíz ya excluye .env. Lo que sale de acá es la frase que
dijiste y nada más: ni tareas viejas, ni sesiones, ni la base."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import anthropic

RUTA_ENV = Path(__file__).resolve().parent / ".env"

# Un paso mínimo son ≤20 palabras: 200 tokens de salida sobran y acotan el
# gasto si el modelo se va de tema.
MAX_TOKENS_SALIDA = 200
# La ventanita corta el fetch a los 8 s: si Claude tarda más, la respuesta
# igual sale por el camino sin IA antes de ese límite.
TIMEOUT_SEGUNDOS = 6.0
MODELO_POR_DEFECTO = "claude-opus-5"

INSTRUCCIONES = (
    "Sos Remi, asistente para una persona con TDAH. Te dan una frase suelta "
    "(una tarea, una idea, un pendiente). Respondé ÚNICAMENTE con el paso "
    "mínimo para empezar: una sola acción concreta, tan chica que se pueda "
    "hacer en cinco minutos. En español, hablándole de tú, en imperativo, "
    "máximo 20 palabras, sin exclamaciones, sin explicar, sin lista, sin comillas. "
    "Nunca urgir, nunca hablar de cuánto importa, nunca acusar."
)


@dataclass(frozen=True)
class Pensado:
    paso_minimo: str
    tokens_entrada: int
    tokens_salida: int
    modelo: str


def _leer_env(ruta: Path = RUTA_ENV) -> dict[str, str]:
    """KEY=VALOR por línea; # comenta; comillas simples o dobles alrededor
    del valor se quitan. Suficiente para una clave, sin otra dependencia."""
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


def clave_api() -> str | None:
    """La variable de entorno gana sobre el .env, para poder probar sin tocarlo."""
    return os.environ.get("ANTHROPIC_API_KEY") or _leer_env().get("ANTHROPIC_API_KEY")


def modelo() -> str:
    return os.environ.get("REMI_CLAUDE_MODELO") or _leer_env().get("REMI_CLAUDE_MODELO") or MODELO_POR_DEFECTO


def _texto_de(respuesta: anthropic.types.Message) -> str:
    return " ".join(
        bloque.text.strip() for bloque in respuesta.content if bloque.type == "text"
    ).strip()


def pensar(frase: str) -> Pensado | None:
    """El paso mínimo que Claude ordena para `frase`. None si no hay clave,
    si la API falla o si no devolvió texto: el que llama sigue por el
    camino sin IA — nunca se rompe la respuesta por esto."""
    clave = clave_api()
    if not clave:
        print("[claude] sin ANTHROPIC_API_KEY en nucleo/.env: sigo sin IA", file=sys.stderr)
        return None

    cliente = anthropic.Anthropic(api_key=clave, timeout=TIMEOUT_SEGUNDOS, max_retries=0)
    nombre_modelo = modelo()
    try:
        respuesta = cliente.messages.create(
            model=nombre_modelo,
            max_tokens=MAX_TOKENS_SALIDA,
            system=INSTRUCCIONES,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": frase}],
        )
    except anthropic.AuthenticationError:
        print("[claude] clave inválida: sigo sin IA", file=sys.stderr)
        return None
    except anthropic.RateLimitError:
        print("[claude] límite de uso alcanzado: sigo sin IA", file=sys.stderr)
        return None
    except anthropic.APIStatusError as error:
        print(f"[claude] la API respondió {error.status_code}: sigo sin IA", file=sys.stderr)
        return None
    except (anthropic.APIConnectionError, anthropic.APITimeoutError) as error:
        print(f"[claude] sin conexión ({type(error).__name__}): sigo sin IA", file=sys.stderr)
        return None

    tokens_entrada = respuesta.usage.input_tokens
    tokens_salida = respuesta.usage.output_tokens
    # La cuenta va a consola, no a la pantalla: es dato de operación.
    print(
        f"[claude] {nombre_modelo} · tokens entrada={tokens_entrada} salida={tokens_salida}",
        file=sys.stderr,
    )

    if respuesta.stop_reason == "refusal":
        print("[claude] no quiso responder: sigo sin IA", file=sys.stderr)
        return None

    paso = _texto_de(respuesta)
    if not paso:
        return None
    return Pensado(
        paso_minimo=paso,
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        modelo=nombre_modelo,
    )

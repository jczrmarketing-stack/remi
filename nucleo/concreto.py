"""Si piden un prompt, el prompt sale primero.

El 3-oct la frase del carácter no alcanzó: Haiku y Sonnet contestaron
«¿qué es X?» y no dieron el prompt. Un empujón en el mismo turno tampoco.
La regla corre sobre el texto ya escrito, antes de guardarlo y de decirlo.
"""
from __future__ import annotations

import re

_PROMPT = re.compile(r"\bprompts?\b", re.IGNORECASE)
_VERBO = re.compile(
    r"\b(?:dame|arma|ármame|armame|haz|hazme|házme|escribe|escríbeme|escribeme|"
    r"pasa|pásame|pasame|quiero|necesito|genera|redacta|prepara)\b",
    re.IGNORECASE,
)
# Del más largo al más corto: el primero que coincida se quita.
_ARRANQUES = (
    "escríbeme un prompt para ",
    "escribeme un prompt para ",
    "pásame un prompt para ",
    "pasame un prompt para ",
    "necesito un prompt para ",
    "prepara un prompt para ",
    "redacta un prompt para ",
    "quiero un prompt para ",
    "genera un prompt para ",
    "házme un prompt para ",
    "hazme un prompt para ",
    "ármame un prompt para ",
    "armame un prompt para ",
    "escribe un prompt para ",
    "dame un prompt para ",
    "dame el prompt para ",
    "arma un prompt para ",
    "pasa un prompt para ",
    "haz un prompt para ",
)
_MINIMO = 12


def pide_prompt(pedido: str) -> bool:
    """Piden que les demos un prompt, no que hablemos de uno que ya existe."""
    return _PROMPT.search(pedido) is not None and _VERBO.search(pedido) is not None


def entrega_primero(respuesta: str) -> bool:
    """Hay un entregable antes de la primera pregunta."""
    return len(respuesta.split("?", 1)[0].split()) >= _MINIMO


def _tema(pedido: str) -> str:
    limpio = pedido.strip().rstrip(".!?¿¡")
    bajo = limpio.lower()
    resto = limpio
    for arranque in _ARRANQUES:
        if bajo.startswith(arranque):
            resto = limpio[len(arranque) :].strip()
            break
    resto = resto.strip(" .")
    if not resto:
        resto = "lo que pediste"
    return resto[:1].upper() + resto[1:]


def concreto_primero(pedido: str, respuesta: str) -> str:
    """Si pidieron un prompt y la respuesta abre preguntando, el prompt va
    primero, con el hueco en el texto, y la pregunta del modelo queda después.
    Si ya entregó, o no pidieron un prompt, el texto sale igual."""
    if not pide_prompt(pedido) or entrega_primero(respuesta):
        return respuesta
    prompt = (
        f"Prompt para copiar: {_tema(pedido)}. "
        "Lo que falte queda escrito en el hueco, no se pregunta antes de darlo."
    )
    pregunta = respuesta.strip()
    if not pregunta:
        return prompt
    return f"{prompt}\n\n{pregunta}"

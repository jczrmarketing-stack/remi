"""Un cobro que llega hablado (T2.4): «Alfonso pagó 1.000», «me pagaron
1.500 de UpVisuals». Sin IA, función pura, como `entregas.parsear_entrega`.

Si no se reconoce de quién es (ni el cliente ni el proyecto aparecen en
ningún libro), no adivina: `tema` sale `None` y servidor.py no crea nada —
queda para que lo pregunte Remi (T3).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import temas

_VERBO = re.compile(
    r"\b(?:pag[oóaó]|pagaron|pagu[eé])\b",
    re.IGNORECASE,
)
_MONTO = re.compile(r"\$?\s*(\d[\d.,]*)")


@dataclass(frozen=True)
class CobroParseado:
    monto: float
    # El tema del libro, si alguno de sus `claves`/título lo nombra. None
    # si el verbo y el monto están pero no se sabe de quién — nunca una
    # adivinanza.
    tema: str | None


def parsear(texto: str) -> CobroParseado | None:
    if not _VERBO.search(texto):
        return None
    coincidencia = _MONTO.search(texto)
    if coincidencia is None:
        return None
    monto_texto = coincidencia.group(1).replace(".", "").replace(",", ".")
    try:
        monto = float(monto_texto)
    except ValueError:
        return None
    return CobroParseado(monto=monto, tema=temas.tema_de_texto(texto))

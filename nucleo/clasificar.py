"""Una frase no siempre es una tarea. Sin IA: idea, hoy o hecha.

La ley 6 manda lo suelto a enfriar 48 h en la Bandeja, así que el default
es `idea`: para que algo se vuelva tarea hay que decirlo. La ley 1 solo
puede decir «la última vez esto te tomó 1 h 40» si alguien cerró el bloque,
y por eso «listo» tiene que poder cerrarlo.

Esto es una función pura y sin IA a propósito. El tipo no lo elige el
modelo: pensar solo reformula la voz, nunca decide qué es lo que dijiste.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

TipoMensaje = Literal["idea", "hoy", "hecha"]

# Cierra el bloque. Van normalizadas (sin tildes): «terminé» entra como
# «termine», «paré» como «pare».
CIERRES = frozenset({"listo", "hecha", "termine", "paro", "pare"})
# La palabra sola, o con hasta tres más: «listo», «listo la tarjeta».
# Una frase larga que menciona «listo» de paso no cierra nada.
MAX_PALABRAS_CIERRE = 4

# Abren un bloque ahora. «voy a» y «vamos con» son la frase entera, no dos
# palabras sueltas que podrían aparecer en cualquier lado.
ARRANQUES = (
    re.compile(r"\bvoy a\b"),
    re.compile(r"\bvamos con\b"),
    re.compile(r"\bahora\b"),
    re.compile(r"\bhoy\b"),
    re.compile(r"\bempiezo\b"),
    re.compile(r"\barranco\b"),
)


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin signos, porque así es como se escribe de
    verdad: «TERMINÉ!!», «termine» y «Terminé» son lo mismo.

    La ñ se descompone y pierde su virgulilla como cualquier otra tilde, así
    que «añadir» queda «anadir». No importa para las palabras que buscamos, y
    evita tener que escribirlas de dos formas.
    """
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes).strip()


def clasificar(texto: str) -> TipoMensaje:
    limpio = normalizar(texto)
    if not limpio:
        return "idea"

    palabras = limpio.split()
    if len(palabras) <= MAX_PALABRAS_CIERRE and any(p in CIERRES for p in palabras):
        return "hecha"

    if any(arranque.search(limpio) for arranque in ARRANQUES):
        return "hoy"

    return "idea"

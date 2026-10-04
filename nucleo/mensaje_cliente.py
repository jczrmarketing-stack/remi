"""B3.1: «ya le mandé el avance a Alfonso» cierra el hito de ese cliente
cuyo `cierra_con` es "mensaje" — sin IA, función pura, como cobros.py.

Nunca inventa un cliente: solo cuenta si el nombre que aparece en la
frase es, literalmente, el `cliente:` de un libro — así «ya le mandé el
avance a Alfonso» cierra el de UpVisuals (si ese es su cliente) y nunca
el de BeaM."""
from __future__ import annotations

import re

import clasificar
import libros

_VERBO = re.compile(
    r"\bya\s+(?:le\s+)?(?:mand[eé]|avis[eé]|entregu[eé]|avanc[eé]|dije|conte[sx]t[eé])\b",
    re.IGNORECASE,
)


def libro_nombrado(texto: str) -> libros.Libro | None:
    """El libro cuyo `cliente:` aparece en la frase, SI además la frase
    tiene la forma de un mensaje ya enviado. None en cualquier otro caso
    — nunca el que tenga una clave en común, nunca una adivinanza."""
    if not _VERBO.search(texto):
        return None
    normalizado = clasificar.normalizar(texto)
    mejor: libros.Libro | None = None
    mejor_largo = -1
    for libro in libros.listar():
        if not libro.cliente:
            continue
        nombre = clasificar.normalizar(libro.cliente)
        if not nombre:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(nombre)}(?![a-z0-9])", normalizado) and len(nombre) > mejor_largo:
            mejor = libro
            mejor_largo = len(nombre)
    return mejor

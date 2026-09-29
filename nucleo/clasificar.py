"""Una frase no siempre es una tarea. Sin IA: idea, hoy o hecha.

La ley 6 manda lo suelto a enfriar 48 h en la Bandeja, así que el default
es `idea`: para que algo se vuelva tarea hay que decirlo con una de las
formas de arranque, y para cerrar hay que decirlo con una palabra exacta.
La ley 1 solo puede decir «la última vez esto te tomó 1 h 40» si alguien
cerró el bloque de verdad, y por eso un cierre no puede salir de una frase
que solo menciona «listo» de paso.

Función pura y sin IA a propósito. El tipo no lo elige el modelo: pensar
solo reformula la voz, nunca decide qué es lo que dijiste.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

TipoMensaje = Literal["idea", "hoy", "hecha"]

# Cierra el bloque SOLO si la frase normalizada es exactamente una de estas.
# «listo el contrato» no cierra: menciona «listo», no lo dice. Van sin
# tildes porque se comparan contra el texto normalizado.
CIERRES_EXACTOS = frozenset(
    {
        "listo",
        "hecha",
        "hecho",
        "termine",
        "paro",
        "pare",
        "ya esta",
        "ya termine",
        "ya estuvo",
        "hasta aca",
        "cerrado",
    }
)

# Abren un bloque si la frase EMPIEZA con una de estas, después de un
# «ahora», «hoy» o «ya» opcional. «hoy» o «ahora» sueltos ya no abren nada:
# «hoy no puedo» no es una tarea.
PREFIJOS_OPCIONALES = ("ahora", "hoy", "ya")
ARRANQUES = (
    "voy a",
    "vamos con",
    "me pongo con",
    "arranco",
    "arranque",
    "empiezo",
    "empece",
    "sigo con",
)

# Con cualquiera de estas, un arranque no abre: la frase duda, o es una
# idea con forma de plan. «voy a ver si armo el curso» es una idea.
NEGACIONES = frozenset({"no", "nunca", "tampoco"})
FRENOS = ("ver si", "quizas", "a lo mejor", "se me ocurrio", "idea")

_PATRON_FRENOS = re.compile(r"\b(?:" + "|".join(re.escape(f) for f in FRENOS) + r")\b")
_PATRON_ARRANQUE = re.compile(
    r"^(?:(?:" + "|".join(PREFIJOS_OPCIONALES) + r") )?"
    r"(?:" + "|".join(re.escape(a) for a in ARRANQUES) + r")\b"
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

    # Una pregunta nunca cierra: «¿listo?» está preguntando, no avisando.
    if "?" not in texto and limpio in CIERRES_EXACTOS:
        return "hecha"

    palabras = limpio.split()
    niega = any(p in NEGACIONES for p in palabras)
    frena = _PATRON_FRENOS.search(limpio) is not None
    if not niega and not frena and _PATRON_ARRANQUE.match(limpio):
        return "hoy"

    return "idea"

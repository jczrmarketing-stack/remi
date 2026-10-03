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

TipoMensaje = Literal["idea", "hoy", "hecha", "pregunta"]

# Una pregunta se contesta y no se guarda: «¿qué tengo pendiente con
# Alfonso?» no es algo suelto que tenga que enfriar 48 h en la Bandeja
# (ley 2 limpia). Whisper transcribe con ¿?, y eso es lo principal. Sin
# signos solo cuentan los arranques inequívocos: «cuando», «como», «que» y
# «para que» abren tanto preguntas como frases («cuando esté listo te
# aviso», «para que no se me olvide»), y ante la duda gana la ley 6.
_PATRON_PREGUNTA = re.compile(
    r"^(?:y )?(?:donde|cuanto|cuanta|cuantos|cuantas|cual|cuales|quien|quienes|por que)\b"
)

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


# Buscar en la web solo cuando se pide con esas palabras (3c · 8): «buscá
# el precio…», «buscame dónde…». Sin IA, como el resto: el modelo nunca
# decide salir a internet por su cuenta.
_PATRON_BUSQUEDA = re.compile(r"^(?:remi |lucho )?(?:busca|buscame|buscanos|buscalo|busquemos)\b")


def pide_busqueda(texto: str) -> bool:
    return bool(_PATRON_BUSQUEDA.match(normalizar(texto)))


# «Me escribió un cliente» (Biblia Parte VI, oficio «clientes»): Juan Camilo
# pega o cuenta lo que le dijo un tercero. Sin IA, como el resto de este
# archivo — las frases exactas que lo anuncian, nada de adivinar por el
# largo del texto (eso ya lo cubre `episodios.LARGO_MINIMO` para otra cosa:
# ofrecer guardar la charla, no leerla como cliente).
_PATRON_CLIENTE = re.compile(
    r"\b(?:me (?:escribio|dijo|escribieron|dijeron)|"
    r"(?:el|la) cliente (?:dice|escribio|me escribio|me dijo)|"
    r"le escribio (?:el|la) cliente|"
    r"escribio (?:el|la) cliente)\b"
)


def es_texto_de_cliente(texto: str) -> bool:
    return bool(_PATRON_CLIENTE.search(normalizar(texto)))


# T8.7: «anotá esta lección: …» en la charla hace lo mismo que el MCP
# `anotar_leccion` — sobre el texto crudo, nunca el normalizado (la
# lección en sí no pierde sus tildes ni su puntuación).
_PATRON_ANOTAR_LECCION = re.compile(r"^anot[aá]\s+esta\s+lecci[oó]n:?\s*(.+)$", re.IGNORECASE | re.DOTALL)


def contenido_anotar_leccion(texto: str) -> str | None:
    coincidencia = _PATRON_ANOTAR_LECCION.match(texto.strip())
    return coincidencia.group(1).strip() or None if coincidencia else None


# T11.1: «Gracias.» no es una idea. Las de cortesía, exactas (sin
# contenido que valga enfriar 48 h); el largo, cualquier frase de menos de
# tres palabras — no hace falta nombrarlas todas.
CORTESIAS = frozenset(
    {
        "gracias", "de nada", "ok", "oka", "okay", "dale", "genial", "perfecto",
        "buenisimo", "excelente", "bien", "bueno", "chau", "adios", "hola",
        "buenos dias", "buenas tardes", "buenas noches", "nada mas",
    }
)


def es_cortesia_o_muy_corta(texto: str) -> bool:
    limpio = normalizar(texto)
    if not limpio:
        return True
    if limpio in CORTESIAS:
        return True
    return len(limpio.split()) < 3


# Mientras se charla con Remi, nada se guarda en la Bandeja por defecto
# (ARQUITECTURA-CEREBRO): la única puerta explícita es «anotá esto: …».
_PATRON_ANOTA_ESTO = re.compile(r"^anot[aá]\s+esto:?\s*(.+)$", re.IGNORECASE | re.DOTALL)


def contenido_anota_esto(texto: str) -> str | None:
    coincidencia = _PATRON_ANOTA_ESTO.match(texto.strip())
    return coincidencia.group(1).strip() or None if coincidencia else None


def _solo_cierres(limpio: str) -> bool:
    """La frase entera son cierres exactos, uno o varios seguidos: «listo»,
    «listo, ya terminé», «ya está, listo». «listo la tarjeta» o «listo por
    hoy» no: tienen algo que no es un cierre."""
    palabras = limpio.split()
    if not palabras:
        return False
    # Partir en trozos de 1 a 3 palabras, cada uno un cierre exacto.
    puede = [True] + [False] * len(palabras)
    for fin in range(1, len(palabras) + 1):
        for largo in (1, 2, 3):
            inicio = fin - largo
            if inicio >= 0 and puede[inicio] and " ".join(palabras[inicio:fin]) in CIERRES_EXACTOS:
                puede[fin] = True
                break
    return puede[-1]


def clasificar(texto: str) -> TipoMensaje:
    limpio = normalizar(texto)
    if not limpio:
        return "idea"

    # Una pregunta nunca cierra: «¿listo?» está preguntando, no avisando.
    if "?" not in texto and _solo_cierres(limpio):
        return "hecha"

    # Y tampoco abre un bloque ni se guarda: se contesta.
    if "?" in texto or "¿" in texto or _PATRON_PREGUNTA.match(limpio):
        return "pregunta"

    palabras = limpio.split()
    niega = any(p in NEGACIONES for p in palabras)
    frena = _PATRON_FRENOS.search(limpio) is not None
    if not niega and not frena and _PATRON_ARRANQUE.match(limpio):
        return "hoy"

    return "idea"

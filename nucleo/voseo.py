"""De vos a tú, sin modelo.

El carácter ya pide de tú y el 3-oct Remi igual dijo «querés», «tenés»,
«mirá». El prompt no alcanza: esto corre sobre cada frase antes de
mostrarla y de decirla. Pura: la misma entrada da la misma salida, y
aplicarla dos veces no cambia nada.

El mapa cubre lo irregular (querés → quieres, no «queres»). Lo regular
de segunda persona es la tilde final: hablás → hablas, comés → comes,
vivís → vives. No se toca lo que no es verbo (además, después, país),
ni el futuro, que ya es de tú (hablarás, verás), ni «estás».
"""
from __future__ import annotations

import re

# Lo que el cambio de tilde no deja bien, o no es un verbo en -ás/-és/-ís.
_MAPA = {
    "querés": "quieres",
    "tenés": "tienes",
    "podés": "puedes",
    "sabés": "sabes",
    "decís": "dices",
    "mandás": "mandas",
    "callás": "callas",
    "pensás": "piensas",
    "referís": "refieres",
    "vos": "tú",
    "decime": "dime",
    "mirá": "mira",
    "fijate": "fíjate",
    "contame": "cuéntame",
    "sos": "eres",
    "sentís": "sientes",
    "pedís": "pides",
    "soltás": "sueltas",
    "venís": "vienes",
    "entendés": "entiendes",
    "empezás": "empiezas",
    "seguís": "sigues",
    "dormís": "duermes",
    "mentís": "mientes",
    "servís": "sirves",
    "repetís": "repites",
    "medís": "mides",
    "preferís": "prefieres",
    "elegís": "eliges",
    "corregís": "corriges",
    "conseguís": "consigues",
    "reís": "ríes",
    "oís": "oyes",
    "hacés": "haces",
    "volvés": "vuelves",
    "movés": "mueves",
    "perdés": "pierdes",
    "cerrás": "cierras",
    "recordás": "recuerdas",
    "encontrás": "encuentras",
    "contás": "cuentas",
    "mostrás": "muestras",
    "probás": "pruebas",
    "jugás": "juegas",
    "soñás": "sueñas",
    "construís": "construyes",
    "incluís": "incluyes",
}

# Palabra entera, no un pedazo. «además» termina en ás y no es «tú amas».
_NO_SON_VOSEO = frozenset(
    {
        "además",
        "después",
        "atrás",
        "más",
        "jamás",
        "quizás",
        "quizá",
        "detrás",
        "demás",
        "nomás",
        "país",
        "maíz",
        "raíz",
        "anís",
        "parís",
        "compás",
        "ananás",
        "interés",
        "través",
        "francés",
        "inglés",
        "cortés",
        "revés",
        "portugués",
        "japonés",
        "holandés",
        "cordobés",
        "montés",
        "burgués",
        "estás",
        # Futuro de tú, irregular y corto: la regla de abajo no lo ve
        # porque el resto no llega a infinitivo (ver, dar, ir, decir).
        "verás",
        "harás",
        "darás",
        "irás",
        "dirás",
        "tendrás",
        "podrás",
        "saldrás",
        "vendrás",
        "pondrás",
        "querrás",
        "sabrás",
        "habrás",
        "cabrás",
        "valdrás",
    }
)

_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
_INFINITIVO = ("ar", "er", "ir")


def _caso(origen: str, destino: str) -> str:
    if origen.isupper():
        return destino.upper()
    if origen[:1].isupper():
        return destino[:1].upper() + destino[1:]
    return destino


def _es_futuro(baja: str) -> bool:
    """hablarás, comerás, vivirás, pararás. No parás ni mirás: ahí el
    resto no es un infinitivo."""
    if not baja.endswith("ás"):
        return False
    resto = baja[:-2]
    return len(resto) >= 5 and resto.endswith(_INFINITIVO)


def _regular(baja: str) -> str | None:
    if baja in _NO_SON_VOSEO or _es_futuro(baja):
        return None
    if baja.endswith("ás"):
        return baja[:-2] + "as"
    if baja.endswith("és"):
        return baja[:-2] + "es"
    if baja.endswith("ís"):
        return baja[:-2] + "es"
    return None


def _una(palabra: str) -> str:
    baja = palabra.lower()
    if baja in _MAPA:
        return _caso(palabra, _MAPA[baja])
    regular = _regular(baja)
    if regular is None or regular == baja:
        return palabra
    return _caso(palabra, regular)


def voseo_a_tu(texto: str) -> str:
    """Cada forma de vos pasa a tú. El resto del texto queda igual."""
    return _PALABRA.sub(lambda hallado: _una(hallado.group(0)), texto)

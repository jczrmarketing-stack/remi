"""B6.1: un gasto que llega hablado — «gasté 40 en el servidor de
UpVisuals», «pagué 20 del dominio», «la membresía de Claude: 100 al mes».
Sin IA, función pura, como `cobros.py`.

Sin proyecto reconocido, un gasto es «común» (de nadie en particular) SOLO
si la frase lo deja claro — con el verbo de gasto, o con una palabra de
gasto recurrente conocida («membresía», «suscripción», «dominio»,
«hosting», «servidor», «herramienta»). Si no se reconoce el proyecto Y no
es un común claro, `claro` sale False: servidor.py no adivina, lo pregunta
Remi (T3)."""
from __future__ import annotations

import re
from dataclasses import dataclass

import temas

_VERBO = re.compile(r"\b(?:gast[eé]|pagu[eé]|pag[oóaó])\b", re.IGNORECASE)
_MONTO = re.compile(r"\$?\s*(\d[\d.,]*)")
_COMUN = re.compile(
    r"\b(?:membres[ií]a|suscripci[oó]n|herramienta|dominio|hosting|servidor)\b", re.IGNORECASE
)
# «la membresía de Claude: 100 al mes» — sin verbo, con dos puntos y un
# número después: una forma de gasto igual de válida, siempre común (no
# tiene sentido que un gasto fijo mensual sea "del proyecto X" sin decirlo).
_SIN_VERBO_CON_DOSPUNTOS = re.compile(r"^(.+?):\s*\$?\s*\d[\d.,]*")

_CONECTORES_INICIALES = ("en", "de", "del", "la", "el", "los", "las", "un", "una")


@dataclass(frozen=True)
class GastoParseado:
    monto: float
    concepto: str
    # El tema del libro, si la frase lo nombra. None cuando es un gasto
    # común (de nadie en particular) o cuando no se reconoce nada.
    tema: str | None
    # False si ni hay proyecto ni es un común reconocible — nunca se
    # adivina: queda para que lo pregunte Remi.
    claro: bool


def _concepto_de(texto: str, antes_de_dos_puntos: str | None) -> str:
    if antes_de_dos_puntos is not None:
        return antes_de_dos_puntos.strip()
    sin_verbo = _VERBO.sub("", texto, count=1)
    sin_monto = _MONTO.sub("", sin_verbo, count=1)
    palabras = sin_monto.strip().split()
    while palabras and palabras[0].lower() in _CONECTORES_INICIALES:
        palabras.pop(0)
    return " ".join(palabras).strip(" .,") or "gasto"


def parsear(texto: str) -> GastoParseado | None:
    con_dos_puntos = _SIN_VERBO_CON_DOSPUNTOS.match(texto.strip())
    tiene_verbo = bool(_VERBO.search(texto))
    if not tiene_verbo and con_dos_puntos is None:
        return None
    coincidencia = _MONTO.search(texto)
    if coincidencia is None:
        return None
    monto_texto = coincidencia.group(1).replace(".", "").replace(",", ".")
    try:
        monto = float(monto_texto)
    except ValueError:
        return None
    tema = temas.tema_de_texto(texto)
    es_comun_claro = bool(_COMUN.search(texto)) or con_dos_puntos is not None
    concepto = _concepto_de(texto, con_dos_puntos.group(1) if con_dos_puntos else None)
    return GastoParseado(
        monto=monto,
        concepto=concepto,
        tema=tema,
        claro=tema is not None or es_comun_claro,
    )

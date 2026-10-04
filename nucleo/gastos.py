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

# Solo primera persona («gasté», «pagué»): «pagó»/«pagaron»/«me pagaron»
# es alguien pagándoME — eso es un cobro (cobros.py), no un gasto. Sin
# esta frontera, «Alfonso pagó 1.500» caería acá si no se reconoce el
# cliente, y Remi preguntaría si es un gasto en vez de anotarlo como cobro.
_VERBO = re.compile(r"\b(?:gast[eé]|pagu[eé])\b", re.IGNORECASE)
_MONTO = re.compile(r"\$?\s*(\d[\d.,]*)")
_COMUN = re.compile(
    r"\b(?:membres[ií]a|suscripci[oó]n|herramienta|dominio|hosting|servidor)\b", re.IGNORECASE
)
# «la membresía de Claude: 100 al mes» — sin verbo, con dos puntos y un
# número después: una forma de gasto igual de válida, siempre común (no
# tiene sentido que un gasto fijo mensual sea "del proyecto X" sin decirlo).
# Exige además una palabra de gasto recurrente (_COMUN) — sin eso, «UpVisuals:
# 3 bugs pendientes» o «Reunión: 3 pm» no son gastos, son cualquier frase con
# dos puntos y un número (hallazgo de revisión, B6).
_SIN_VERBO_CON_DOSPUNTOS = re.compile(r"^(.+?):\s*\$?\s*\d[\d.,]*")
# Un número dentro de una fecha hablada («el 15 de octubre») nunca es el
# monto — se descarta antes de buscar el monto y antes de armar el
# concepto (hallazgo de revisión, B6).
_MESES = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
_FECHA = re.compile(rf"\d{{1,2}}\s+de\s+(?:{_MESES})\b", re.IGNORECASE)

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


def _monto_de(numero: str) -> float:
    """"1.500" son mil quinientos (punto de miles, como en el resto de la
    app); "40.50" son cuarenta con cincuenta (un solo punto con dos
    decimales se lee como decimal, no como miles)."""
    if "," in numero:
        return float(numero.replace(".", "").replace(",", "."))
    partes = numero.split(".")
    if len(partes) == 2 and len(partes[1]) == 2:
        return float(numero)
    return float(numero.replace(".", ""))


def _concepto_de(texto: str, antes_de_dos_puntos: str | None) -> str:
    if antes_de_dos_puntos is not None:
        return antes_de_dos_puntos.strip()
    sin_verbo = _VERBO.sub("", texto, count=1)
    sin_fechas = _FECHA.sub("", sin_verbo)
    sin_monto = _MONTO.sub("", sin_fechas, count=1)
    palabras = sin_monto.strip().split()
    while palabras and palabras[0].lower() in _CONECTORES_INICIALES:
        palabras.pop(0)
    return " ".join(palabras).strip(" .,") or "gasto"


def parsear(texto: str) -> GastoParseado | None:
    con_dos_puntos = _SIN_VERBO_CON_DOSPUNTOS.match(texto.strip())
    es_comun_de_dos_puntos = con_dos_puntos is not None and bool(_COMUN.search(texto))
    if con_dos_puntos is not None and not es_comun_de_dos_puntos:
        con_dos_puntos = None
    tiene_verbo = bool(_VERBO.search(texto))
    if not tiene_verbo and con_dos_puntos is None:
        return None
    sin_fechas = _FECHA.sub("", texto)
    coincidencia = _MONTO.search(sin_fechas)
    if coincidencia is None:
        return None
    try:
        monto = _monto_de(coincidencia.group(1))
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

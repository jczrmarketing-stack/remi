"""Agenda por voz (T2.5): «mañana…», «a las 3…», «el viernes…», «vence el
15 de octubre…» crean una tarea con fecha u hora — nunca abren un bloque.

Sin IA, función pura. Solo dispara si la frase EMPIEZA con una marca de
tiempo inequívoca, o dice «vence el D de MES» — eso ya basta para no
necesitar los frenos ni las negaciones de clasificar.py: «se me ocurrió
vender plantillas mañana» no empieza con nada de esto, así que no entra
acá y sigue ganando la ley 6 (idea).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}

_PASADO_MANANA = re.compile(r"^pasado\s+mañana\b")
_MANANA = re.compile(r"^mañana\b")
_A_LAS = re.compile(r"^a las?\s+(\d{1,2})(?::(\d{2}))?\b")
_EL_DIA_SEMANA = re.compile(r"^el\s+(" + "|".join(DIAS_SEMANA) + r")\b")
_EL_DIA_MES = re.compile(r"^el\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\b")
_VENCE = re.compile(r"\bvence\s+el\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\b")


@dataclass(frozen=True)
class AgendaParseada:
    titulo: str
    hora: str | None
    fecha_limite: date | None


def _titulo_de(texto: str, fin: int) -> str:
    resto = texto[fin:].strip(" ,.-")
    return resto if resto else texto.strip()


def _fecha_dia_mes(hoy: date, dia: int, mes_nombre: str) -> date | None:
    mes = MESES.get(mes_nombre.lower())
    if mes is None:
        return None
    try:
        fecha = date(hoy.year, mes, dia)
    except ValueError:
        return None
    if fecha < hoy:
        try:
            fecha = date(hoy.year + 1, mes, dia)
        except ValueError:
            return None
    return fecha


def _proximo_dia_semana(hoy: date, objetivo: int) -> date:
    delta = (objetivo - hoy.weekday()) % 7
    return hoy + timedelta(days=delta or 7)


def parsear(texto: str, hoy: date) -> AgendaParseada | None:
    """None si la frase no empieza con una marca de tiempo clara y no dice
    «vence el D de MES» — nunca adivina."""
    limpio = texto.strip()
    minuscula = limpio.lower()

    coincidencia = _PASADO_MANANA.match(minuscula)
    if coincidencia:
        return AgendaParseada(_titulo_de(limpio, coincidencia.end()), None, hoy + timedelta(days=2))

    coincidencia = _MANANA.match(minuscula)
    if coincidencia:
        return AgendaParseada(_titulo_de(limpio, coincidencia.end()), None, hoy + timedelta(days=1))

    coincidencia = _A_LAS.match(minuscula)
    if coincidencia:
        hora = int(coincidencia.group(1))
        minuto = int(coincidencia.group(2) or 0)
        if 0 <= hora <= 23 and 0 <= minuto <= 59:
            return AgendaParseada(_titulo_de(limpio, coincidencia.end()), f"{hora:02d}:{minuto:02d}", None)
        return None

    coincidencia = _EL_DIA_SEMANA.match(minuscula)
    if coincidencia:
        objetivo = DIAS_SEMANA[coincidencia.group(1)]
        return AgendaParseada(_titulo_de(limpio, coincidencia.end()), None, _proximo_dia_semana(hoy, objetivo))

    coincidencia = _EL_DIA_MES.match(minuscula)
    if coincidencia:
        fecha = _fecha_dia_mes(hoy, int(coincidencia.group(1)), coincidencia.group(2))
        if fecha is None:
            return None
        return AgendaParseada(_titulo_de(limpio, coincidencia.end()), None, fecha)

    coincidencia = _VENCE.search(minuscula)
    if coincidencia:
        fecha = _fecha_dia_mes(hoy, int(coincidencia.group(1)), coincidencia.group(2))
        if fecha is None:
            return None
        return AgendaParseada(limpio, None, fecha)

    return None

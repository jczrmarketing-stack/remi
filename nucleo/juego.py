"""R3 (PLAN-FINAL.md): «Ábreme el juego» — 20 jugadas con muestreo
verbalizado y los lentes de la Parte IX. Quien de verdad piensa es
`generador` (inyectado: el modelo real en producción, un doble en
pytest — nunca una llamada de pago dentro de una prueba); este módulo
solo descarta repetidas (similitud) y palabras de moda, y garantiza que
al menos una jugada cuestione la meta — nunca inventa el contenido.

Las jugadas van a la Bandeja como `Idea(origen="rumbo")`: no se vuelven
proyecto solas (ley 6, enfriamiento de 48h, igual que cualquier otra).

El `generador` real (la llamada al modelo con el prompt de muestreo
verbalizado) no está wireado todavía — mismo BLOQUEADO que el
investigador de `analisis_camino.py`: diseñar ese prompt es trabajo de
una sesión dedicada. Lo que sí está completo y probado es el filtro.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable
from uuid import uuid4

from modelos import Idea

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "rumbo.json"
UMBRAL_SIMILITUD = 0.82
CANTIDAD_JUGADAS = 20
HORAS_ENFRIAMIENTO = 48

_PALABRAS_META = ("meta", "visión", "vision", "norte")


def _config() -> dict[str, object]:
    return json.loads(RUTA_CONFIG.read_text())


@dataclass(frozen=True)
class JugadaCruda:
    texto: str
    # 1-6: a cuál problema de la Parte IX responde la jugada; None si es
    # la que cuestiona la meta (no responde a un problema, cuestiona el
    # objetivo mismo).
    lente: int | None


Generador = Callable[[], list[JugadaCruda]]


def _es_repetida(texto: str, ya_vistas: list[str]) -> bool:
    bajo = texto.lower()
    return any(SequenceMatcher(None, bajo, vista.lower()).ratio() >= UMBRAL_SIMILITUD for vista in ya_vistas)


def _tiene_palabra_de_moda(texto: str, palabras: list[str]) -> bool:
    bajo = texto.lower()
    return any(palabra.lower() in bajo for palabra in palabras)


def _cuestiona_la_meta(texto: str) -> bool:
    bajo = texto.lower()
    return "?" in texto and any(palabra in bajo for palabra in _PALABRAS_META)


def filtrar_jugadas(crudas: list[JugadaCruda]) -> list[JugadaCruda]:
    """Descarta repetidas y palabras de moda; si ninguna de las que
    sobreviven cuestiona la meta, agrega la jugada fija que lo hace —
    nunca se queda sin ese ángulo."""
    palabras = _config().get("palabras_de_moda", [])
    assert isinstance(palabras, list)
    filtradas: list[JugadaCruda] = []
    vistas: list[str] = []
    for jugada in crudas:
        if _tiene_palabra_de_moda(jugada.texto, palabras):
            continue
        if _es_repetida(jugada.texto, vistas):
            continue
        filtradas.append(jugada)
        vistas.append(jugada.texto)
    if not any(_cuestiona_la_meta(j.texto) for j in filtradas):
        filtradas.append(JugadaCruda(texto="¿Y si la meta de plata no es la correcta y el norte real es otro?", lente=None))
    return filtradas


def generar_jugadas(generador: Generador) -> list[JugadaCruda]:
    return filtrar_jugadas(generador())


def jugadas_a_ideas(jugadas: list[JugadaCruda], ahora: datetime) -> list[Idea]:
    return [
        Idea(
            id=uuid4(), texto=jugada.texto, origen="rumbo", creada_en=ahora,
            enfria_hasta=ahora + timedelta(hours=HORAS_ENFRIAMIENTO), estado="enfriando",
            problema_vision=jugada.lente, tema=None,
        )
        for jugada in jugadas
    ]

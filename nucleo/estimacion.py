"""R4.1-R4.3 (PLAN-FINAL.md): números honestos. El código nunca decide
qué es verdad — combina en código (mediana, mezcla con pesos fijos) lo
que YA dijeron modelos de familias distintas, inyectados siempre como
`estimador`/`critico` (nunca una llamada real de pago en pytest)."""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "rumbo.json"

PESOS_POR_DEFECTO = (0.5, 0.3, 0.2)  # (modelos, tasa_base, propio) — suman 1


def _config() -> dict[str, object]:
    return json.loads(RUTA_CONFIG.read_text())


def combinar_a_ciegas(estimaciones: list[float]) -> float:
    """La mediana, sin extremizar — un valor raro no mueve el número
    final como lo haría un promedio."""
    return statistics.median(estimaciones)


def pesos_mezcla() -> tuple[float, float, float]:
    crudo = _config().get("pesos_mezcla", list(PESOS_POR_DEFECTO))
    assert isinstance(crudo, list) and len(crudo) == 3
    return float(crudo[0]), float(crudo[1]), float(crudo[2])


def mezclar(mediana_modelos: float, tasa_base: float, estimado_propio: float, pesos: tuple[float, float, float] | None = None) -> float:
    """Pesos fijos de `config/rumbo.json` (nunca a mano en cada llamada,
    salvo que quien llama quiera forzar otros para una prueba). Si no
    suman uno (o suman 0), se normalizan — un typo de configuración no
    tiene que romper la cuenta."""
    w_modelos, w_base, w_propio = pesos or pesos_mezcla()
    total = w_modelos + w_base + w_propio
    if total <= 0:
        return mediana_modelos
    return (mediana_modelos * w_modelos + tasa_base * w_base + estimado_propio * w_propio) / total


EstimadorCiego = Callable[[], float]


def estimar_a_ciegas(estimadores: list[EstimadorCiego]) -> list[float]:
    """Cada `estimador` es un modelo de una familia distinta (Claude,
    Groq, OpenRouter...), llamado sin saber qué prefiere Juan Camilo —
    eso lo decide quien construye el estimador real, nunca este módulo."""
    return [estimador() for estimador in estimadores]


@dataclass(frozen=True)
class Critica:
    autor: str  # "A" | "B" | "C" (anónima) | "abogado_del_diablo"
    problemas: list[str]


MINIMO_PROBLEMAS_ABOGADO_DEL_DIABLO = 3


def necesita_segunda_ronda(criticas: list[Critica], supuestos_originales: set[str]) -> bool:
    """Una segunda ronda a ciegas SOLO si la crítica de verdad toca uno
    de los supuestos con los que se armó la primera — nunca «por si
    acaso»."""
    supuestos_tocados = {problema for critica in criticas for problema in critica.problemas}
    return bool(supuestos_tocados & supuestos_originales)

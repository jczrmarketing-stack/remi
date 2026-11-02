"""Dónde está la bóveda (B3, 2-nov). Antes había 7 copias de «/Volumes/ORGANIC/boveda» escritas a mano:
si el disco externo no estaba, Remi se quedaba sin bóveda. Ahora la bóveda vive en el disco interno
(~/proyectos/boveda) y ORGANIC queda solo como respaldo mientras dura la mudanza.

Las variables de entorno de cada sitio (REMI_BOVEDA, BOVEDA_RAIZ) siguen mandando primero: las pruebas
las usan para aislar."""
from __future__ import annotations

from pathlib import Path

INTERNA = Path.home() / "proyectos" / "boveda"
EXTERNA = Path("/Volumes/ORGANIC/boveda")
FIJAS: tuple[str, ...] = (str(INTERNA), str(EXTERNA))


def ubicar(*preferidas: str | None, marca: str = "newsletter.py") -> Path | None:
    """La primera carpeta que exista y tenga `marca` (para no confundirla con otra carpeta «boveda»)."""
    for c in (*preferidas, *FIJAS):
        if c and (Path(c) / marca).exists():
            return Path(c)
    return None

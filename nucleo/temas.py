"""A qué libro pertenece una idea (Biblia v3.7: `Idea.tema`).

Sin IA, como el clasificador: el tema sale de comparar lo dicho contra el
`tema` y las `claves` del frontmatter de cada libro de proyectos/ y áreas/.
Una clave que comparten dos libros (next.js, whatsapp) no decide nada, y
ante un empate no se elige: la idea queda suelta (None), que es un estado
válido — el panel la muestra como «suelta».
"""
from __future__ import annotations

import re
from pathlib import Path

import libros
from clasificar import normalizar

LARGO_MINIMO_DE_FRASE = 4


def _frases_de(ruta: Path) -> tuple[str, list[str]] | None:
    """(tema, frases normalizadas) de un libro. None si no tiene tema."""
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None
    campos = libros._frontmatter(partes[1])
    tema = campos.get("tema")
    if not isinstance(tema, str) or not tema:
        return None
    crudas: list[str] = [tema.replace("-", " ")]
    claves = campos.get("claves")
    if isinstance(claves, list):
        crudas += claves
    elif isinstance(claves, str):
        crudas += claves.strip().strip("[]").split(",")
    frases: list[str] = []
    for cruda in crudas:
        frase = normalizar(cruda)
        if len(frase) >= LARGO_MINIMO_DE_FRASE and frase not in frases:
            frases.append(frase)
    return tema, frases


def _libros_con_frases() -> dict[str, list[str]]:
    """{tema: frases que solo ese libro tiene}."""
    proyectos = libros.carpeta()
    carpetas = (proyectos, proyectos.parent / "areas")
    por_tema: dict[str, list[str]] = {}
    for carpeta in carpetas:
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.glob("*.md")):
            leido = _frases_de(ruta)
            if leido is not None:
                por_tema.setdefault(leido[0], []).extend(leido[1])
    veces: dict[str, int] = {}
    for frases in por_tema.values():
        for frase in set(frases):
            veces[frase] = veces.get(frase, 0) + 1
    return {tema: [f for f in frases if veces[f] == 1] for tema, frases in por_tema.items()}


def tema_de_texto(texto: str) -> str | None:
    """El tema del libro que el texto nombra con más de sus frases. None si
    no nombra ninguno o si dos libros empatan."""
    limpio = f" {normalizar(texto)} "
    if not limpio.strip():
        return None
    puntos: dict[str, int] = {}
    for tema, frases in _libros_con_frases().items():
        aciertos = sum(1 for frase in frases if re.search(rf"(?<![a-z0-9]){re.escape(frase)}(?![a-z0-9])", limpio))
        if aciertos:
            puntos[tema] = aciertos
    if not puntos:
        return None
    mejor = max(puntos.values())
    ganadores = [tema for tema, valor in puntos.items() if valor == mejor]
    return ganadores[0] if len(ganadores) == 1 else None

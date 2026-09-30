#!/usr/bin/env python
"""Mete las fichas de conocimiento/proyectos/*.md en el estante.

Cada archivo es un proyecto: frontmatter con titulo, tema y resumen, y el
cuerpo debajo. Queda en el estante como fuente «manual», una entrada por
tema: el índice (siempre en el prompt) tiene una línea por proyecto, y el
modelo usa `leer` para el detalle.

Idempotente por tema. Si ya hay una entrada con ese tema y el archivo
cambió, se actualiza; si no cambió, no se toca; si no hay, se crea. Corre
solo al arrancar el núcleo, y también a mano:

    cd nucleo && uv run python sembrar_conocimiento.py

Las fichas viven fuera del repo (datos personales): conocimiento/ está en
.gitignore. REMI_CONOCIMIENTO apunta a otra carpeta (las pruebas lo usan).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

import db
from modelos import Memoria

CARPETA = Path(__file__).resolve().parent.parent / "conocimiento" / "proyectos"


@dataclass(frozen=True)
class Ficha:
    archivo: str
    titulo: str
    tema: str
    resumen: str
    cuerpo: str
    claves: str | None


def carpeta() -> Path:
    return Path(os.environ.get("REMI_CONOCIMIENTO") or CARPETA)


def carpeta_oficios() -> Path:
    """Los oficios viven al lado de proyectos/, no adentro (Biblia Parte VI:
    son libros del mismo estante, con `tipo: oficio` en el frontmatter)."""
    return carpeta().parent / "oficios"


def leer_ficha(ruta: Path) -> Ficha | None:
    """None si no tiene el frontmatter completo: se avisa y se salta."""
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None
    campos: dict[str, str] = {}
    for linea in partes[1].splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            campos[clave.strip()] = valor.strip()
    if not all(campos.get(c) for c in ("titulo", "tema", "resumen")):
        return None
    return Ficha(
        ruta.name,
        campos["titulo"],
        campos["tema"],
        campos["resumen"],
        partes[2].strip(),
        campos.get("claves") or None,
    )


# Un libro de proyecto vive en la capa de arriba de la mente (nivel 1: su
# título y resumen siempre presentes) mientras esté activo; si nadie lo toca
# en una semana baja a nivel 2 (se puede seguir pidiendo, ya no ocupa la capa
# de arriba) — ARQUITECTURA-CEREBRO §2, «olvidar = bajar de nivel, nunca
# borrar». La consolidación nocturna (`noche.py`) vuelve a sembrar cada
# noche para que esto se reordene solo, con el mtime del día.
NIVEL_RECIENTE = 1
NIVEL_ANTIGUO = 2
DIAS_RECIENTE = 7


def nivel_de(ruta: Path) -> int:
    """Nivel 1 si el archivo se tocó (mtime) en los últimos 7 días; si no, 2."""
    dias = (datetime.now(timezone.utc).timestamp() - ruta.stat().st_mtime) / 86400
    return NIVEL_RECIENTE if dias <= DIAS_RECIENTE else NIVEL_ANTIGUO


def sembrar() -> dict[str, int]:
    """Cuántas se crearon, actualizaron, quedaron igual o se saltaron."""
    return _sembrar_desde(carpeta(), "conocimiento")


def sembrar_oficios() -> dict[str, int]:
    """Los oficios (Biblia Parte VI) entran al mismo estante que los
    proyectos: título y resumen siempre en la mente, `tipo: oficio` es solo
    una marca en el frontmatter (no cambia cómo se siembran). Nivel 1
    siempre — un oficio no se "olvida" por no tocarlo, es saber-hacer, no
    actividad reciente."""
    return _sembrar_desde(carpeta_oficios(), "oficios", nivel_fijo=NIVEL_RECIENTE)


def _sembrar_desde(origen: Path, etiqueta: str, nivel_fijo: int | None = None) -> dict[str, int]:
    cuenta = {"creadas": 0, "actualizadas": 0, "iguales": 0, "saltadas": 0}
    if not origen.is_dir():
        print(f"[{etiqueta}] no está {origen}: nada que sembrar", file=sys.stderr)
        return cuenta

    conexion = db.conectar()
    try:
        for ruta in sorted(origen.glob("*.md")):
            ficha = leer_ficha(ruta)
            if ficha is None:
                print(f"[{etiqueta}] {ruta.name}: sin titulo/tema/resumen, la salto", file=sys.stderr)
                cuenta["saltadas"] += 1
                continue

            nivel = nivel_fijo if nivel_fijo is not None else nivel_de(ruta)
            existentes = db.memorias_por_tema(conexion, ficha.tema)
            try:
                if not existentes:
                    db.guardar_memoria(
                        conexion,
                        Memoria(
                            id=uuid4(),
                            titulo=ficha.titulo,
                            resumen=ficha.resumen,
                            tema=ficha.tema,
                            fecha=datetime.now(timezone.utc),
                            cuerpo=ficha.cuerpo,
                            fuente="manual",
                            claves=ficha.claves,
                            nivel=nivel,
                        ),
                    )
                    cuenta["creadas"] += 1
                    continue

                actual = existentes[0]
                ahora = (ficha.titulo, ficha.resumen, ficha.cuerpo, ficha.claves, nivel)
                if (actual.titulo, actual.resumen, actual.cuerpo, actual.claves, actual.nivel) == ahora:
                    cuenta["iguales"] += 1
                    continue
                db.editar_memoria(
                    conexion,
                    actual.id,
                    titulo=ficha.titulo,
                    resumen=ficha.resumen,
                    cuerpo=ficha.cuerpo,
                    claves=ficha.claves,
                    nivel=nivel,
                )
                cuenta["actualizadas"] += 1
            except ValidationError:
                print(
                    f"[{etiqueta}] {ruta.name}: el título pasa de 80 o el resumen de 240, la salto",
                    file=sys.stderr,
                )
                cuenta["saltadas"] += 1
    finally:
        conexion.close()

    print(
        f"[{etiqueta}] "
        + " · ".join(f"{clave}={valor}" for clave, valor in cuenta.items()),
        file=sys.stderr,
    )
    return cuenta


if __name__ == "__main__":
    sembrar()
    sembrar_oficios()

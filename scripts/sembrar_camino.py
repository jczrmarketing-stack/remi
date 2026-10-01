#!/usr/bin/env python3
"""Siembra «## Camino» en los libros que todavía no lo tienen, con los
hitos del SOP (oficios/proyectos-sop.md en la bóveda) según el tipo del
proyecto — propio (7 pasos de §A) o cliente (10 pasos de §B).

Dry-run por defecto: solo dice qué libros le falta `## Camino` y, si el
frontmatter ya dice el tipo, cuál usaría. Con --escribir, agrega la
sección de verdad — nunca toca nada más del archivo, nunca borra ni
reordena un hito existente — y deja un commit en la bóveda por libro.

Si el frontmatter no dice «tipo: propio» ni «tipo: cliente», lo pregunta
en la terminal; nunca lo adivina. Responder «saltar» deja ese libro para
otra corrida.

    cd nucleo && uv run python ../scripts/sembrar_camino.py
    cd nucleo && uv run python ../scripts/sembrar_camino.py --escribir
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# caminos.py/libros.py/boveda_git.py viven en nucleo/, no en scripts/ — este
# archivo corre con el Python (y el venv) de nucleo/, pero desde afuera.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))

import boveda_git  # noqa: E402
import caminos  # noqa: E402
import libros  # noqa: E402


def _sin_camino() -> list[libros.Libro]:
    return [libro for libro in libros.listar() if not caminos.leer_hitos(libro.archivo)]


def _preguntar_tipo(libro: libros.Libro) -> str | None:
    print(f"\n«{libro.titulo}» ({libro.tema}) no dice el tipo en el frontmatter.")
    while True:
        respuesta = input("¿Es un proyecto propio o de cliente? [propio/cliente/saltar] ").strip().lower()
        if respuesta in ("propio", "cliente"):
            return respuesta
        if respuesta in ("saltar", "s", ""):
            return None
        print("Escribí «propio», «cliente» o «saltar».")


def _sembrar(libro: libros.Libro, tipo: str) -> None:
    bloque = caminos.bloque_camino_de(tipo)
    original = libro.archivo.read_text()
    nuevo = original.rstrip("\n") + "\n\n" + bloque
    boveda_git.snapshot_antes(f"## Camino de {libro.archivo.name}")
    libro.archivo.write_text(nuevo)
    boveda_git.snapshot_despues(f"bóveda: ## Camino de {libro.archivo.name} (tipo {tipo}, SOP)")


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument(
        "--escribir", action="store_true", help="agrega ## Camino de verdad. Sin esto, solo dry-run."
    )
    argumentos = analizador.parse_args()

    faltantes = _sin_camino()
    if not faltantes:
        print("Los libros ya tienen ## Camino.")
        return 0

    print(f"{len(faltantes)} libro(s) sin ## Camino:")
    for libro in faltantes:
        print(f"  - {libro.titulo} ({libro.tema}) · tipo en frontmatter: {libro.tipo or '(sin decir)'}")

    if not argumentos.escribir:
        print("\nDry-run. Para escribir de verdad: --escribir")
        return 0

    for libro in faltantes:
        tipo = libro.tipo or _preguntar_tipo(libro)
        if tipo is None:
            print(f"  - {libro.tema}: salteado (sin tipo).")
            continue
        _sembrar(libro, tipo)
        print(f"  - {libro.tema}: sembrado ({tipo}, {len(caminos.plantilla_de(tipo) or ())} hitos).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

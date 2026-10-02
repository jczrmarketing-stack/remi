#!/usr/bin/env python3
"""T9.4: exporta cada oficio de la bóveda como skill de usuario de Claude
Code, para que toda sesión los tenga (no solo las que trabajan en Remi).

Claude Code lee los skills de usuario en `~/.claude/skills/<nombre>/
SKILL.md` (fuera de cualquier repo, globales a toda sesión — distinto del
skill de proyecto `.claude/skills/remi/`, que solo carga en este repo).

Un oficio es solo conocimiento (lo que dice, no scripts que corran): el
skill que sale de acá tampoco ejecuta nada — Remi lo nombra en un encargo
y lo corre Claude Code, como con cualquier otro oficio.

Dry-run por defecto. --escribir de verdad copia los archivos.

    cd nucleo && uv run python ../scripts/oficios_a_skills.py
    cd nucleo && uv run python ../scripts/oficios_a_skills.py --escribir
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))

import sembrar_conocimiento  # noqa: E402

CARPETA_SKILLS_USUARIO = Path.home() / ".claude" / "skills"
PREFIJO = "remi-oficio-"


def _slug(texto: str) -> str:
    import re
    import unicodedata

    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes).strip("-")


def _skill_md_de(ficha: "sembrar_conocimiento.Ficha") -> str:
    descripcion = ficha.resumen.replace("\n", " ").strip()
    return f"---\nname: {PREFIJO}{_slug(ficha.titulo)}\ndescription: {descripcion}\n---\n\n{ficha.cuerpo}\n"


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--escribir", action="store_true", help="copia los archivos de verdad")
    argumentos = analizador.parse_args()

    carpeta = sembrar_conocimiento.carpeta_oficios()
    if not carpeta.is_dir():
        print(f"No hay oficios en {carpeta}.")
        return 0

    exportados = 0
    for ruta in sorted(carpeta.glob("*.md")):
        ficha = sembrar_conocimiento.leer_ficha(ruta)
        if ficha is None:
            print(f"  salto {ruta.name}: sin título/tema/resumen completos")
            continue
        nombre_skill = f"{PREFIJO}{_slug(ficha.titulo)}"
        destino = CARPETA_SKILLS_USUARIO / nombre_skill / "SKILL.md"
        if argumentos.escribir:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(_skill_md_de(ficha))
            print(f"  escrito: {destino}")
        else:
            print(f"  exportaría: {ruta.name} -> {destino}")
        exportados += 1

    print(f"\n{exportados} oficio(s) {'exportado(s)' if argumentos.escribir else 'por exportar (dry-run)'}.")
    if not argumentos.escribir:
        print("Nada escrito. Para escribir de verdad: --escribir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

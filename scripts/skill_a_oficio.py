#!/usr/bin/env python3
"""T9.4: trae un SKILL.md de solo conocimiento (sin scripts que ejecuten
nada) como oficio de la bóveda — la misma fuente, en el otro sentido que
oficios_a_skills.py.

Un skill con scripts no entra al cerebro de Remi (ella lee, no ejecuta):
si la carpeta del skill trae algo más que el SKILL.md, esto se niega y
dice por qué — Remi lo nombra en un encargo y lo corre Claude Code, pero
no se copia como si fuera conocimiento suyo.

    cd nucleo && uv run python ../scripts/skill_a_oficio.py ~/.claude/skills/mi-skill
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))

import boveda_git  # noqa: E402
import sembrar_conocimiento  # noqa: E402


def _slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes).strip("-")


def _solo_conocimiento(carpeta: Path) -> list[str]:
    """Los archivos de la carpeta del skill que no son el SKILL.md — si
    hay alguno, trae scripts (o algo más) y esto se niega."""
    return sorted(p.name for p in carpeta.iterdir() if p.name != "SKILL.md")


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("carpeta", help="la carpeta del skill (con su SKILL.md adentro)")
    argumentos = analizador.parse_args()

    carpeta = Path(argumentos.carpeta).expanduser().resolve()
    skill_md = carpeta / "SKILL.md"
    if not skill_md.is_file():
        print(f"No encuentro {skill_md}.", file=sys.stderr)
        return 1

    extra = _solo_conocimiento(carpeta)
    if extra:
        print(
            f"«{carpeta.name}» trae algo más que SKILL.md ({', '.join(extra)}): no es solo "
            "conocimiento. Remi lo nombra en un encargo y lo corre Claude Code — esto no lo "
            "copia como oficio.",
            file=sys.stderr,
        )
        return 1

    texto = skill_md.read_text()
    if not texto.startswith("---"):
        print(f"{skill_md} no tiene frontmatter (name/description): no sé cómo titularlo.", file=sys.stderr)
        return 1
    partes = texto.split("---", 2)
    if len(partes) < 3:
        print(f"{skill_md} tiene un frontmatter que no cierra.", file=sys.stderr)
        return 1
    campos: dict[str, str] = {}
    for linea in partes[1].splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            campos[clave.strip()] = valor.strip()
    nombre = campos.get("name") or carpeta.name
    descripcion = campos.get("description") or f"Skill «{nombre}», traído a oficio."
    cuerpo = partes[2].strip()

    tema = f"oficio-{_slug(nombre)}"
    destino = sembrar_conocimiento.carpeta_oficios() / f"{_slug(nombre)}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        print(f"Ya hay un oficio en {destino} — esto no lo pisa.", file=sys.stderr)
        return 1

    boveda_git.snapshot_antes(f"traer el skill {nombre} como oficio")
    destino.write_text(
        f'---\ntitulo: "{nombre}"\ntema: {tema}\nresumen: "{descripcion}"\ntipo: oficio\n---\n\n{cuerpo}\n'
    )
    boveda_git.snapshot_despues(f"oficios: {destino.name}, traído del skill «{nombre}»")
    print(f"Escrito: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""T11.2: las ideas de ruido que T8.0 dejó de crear, pero que ya habían
entrado antes del fix, siguen en la Bandeja. Dos patrones, nada más:

1. «proyecto sin ficha: <ruta>» — el hook de sesión sin ficha que tocara.
2. «qué te falta…» — la pregunta de estado que T8.0 dejó de anotar como
   idea, corta (sin esto, una idea real que solo MENCIONE «falta» de paso
   no se archiva por error).

Solo toca ideas con estado `enfriando` — una ya revisada (lista, proyecto,
soltada, archivada) no se vuelve a tocar. Nunca un DELETE: archiva (estado
`archivada`), igual que limpiar_pruebas.py.

Dry-run por defecto.

    cd nucleo && uv run python ../scripts/archivar_ruido_de_sesiones.py
    cd nucleo && uv run python ../scripts/archivar_ruido_de_sesiones.py --si
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))

import db  # noqa: E402
import trabajo  # noqa: E402

PREFIJO_SIN_FICHA = "proyecto sin ficha: "
PALABRAS_MAXIMO_QUE_FALTA = 12


def es_ruido(texto: str) -> bool:
    if texto.startswith(PREFIJO_SIN_FICHA):
        return True
    return trabajo.es_que_falta(texto) and len(texto.split()) <= PALABRAS_MAXIMO_QUE_FALTA


def candidatas(conexion: sqlite3.Connection) -> list:
    return [idea for idea in db.listar_ideas(conexion) if idea.estado == "enfriando" and es_ruido(idea.texto)]


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--si", action="store_true", help="archiva de verdad (dry-run por defecto)")
    argumentos = analizador.parse_args()

    conexion = db.conectar()
    try:
        encontradas = candidatas(conexion)
        if not encontradas:
            print("No hay ideas de ruido de sesiones en enfriando.")
            return 0
        for idea in encontradas:
            print(f"  {idea.id} · {idea.creada_en.isoformat()} · {idea.texto!r}")
        if not argumentos.si:
            print(f"\n{len(encontradas)} idea(s) archivaría (dry-run). Para archivar de verdad: --si")
            return 0
        for idea in encontradas:
            conexion.execute("UPDATE ideas SET estado = 'archivada' WHERE id = ?", (str(idea.id),))
        conexion.commit()
        print(f"\n{len(encontradas)} idea(s) archivada(s). Ninguna se borró.")
    finally:
        conexion.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

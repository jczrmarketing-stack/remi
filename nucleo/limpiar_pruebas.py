#!/usr/bin/env python
"""Lo que quedó de probar Remi en la base real — dos patrones, nada más:

1. Ideas «proyecto sin ficha: <ruta>» donde <ruta> es una carpeta de
   pruebas (trabajo.es_ruta_de_pruebas: pytest-of-, $TMPDIR, /private/var/
   folders, /tmp). Quedaron de antes de que es_carpeta_de_proyecto() y los
   hooks de test las filtraran (1-oct): cientos, una por corrida.
2. Tareas tituladas exactamente «hola», sin ninguna sesión.

Sin --borrar, solo cuenta y lista — no borra nada. Con --borrar, borra
exactamente esas dos cosas y nada más.

    cd nucleo && uv run python limpiar_pruebas.py
    cd nucleo && uv run python limpiar_pruebas.py --borrar
"""
from __future__ import annotations

import argparse
import sqlite3
from uuid import UUID

import db
import trabajo

PREFIJO_SIN_FICHA = "proyecto sin ficha: "


def _ideas_de_prueba(conexion: sqlite3.Connection) -> list[tuple[UUID, str]]:
    resultado: list[tuple[UUID, str]] = []
    for idea in db.listar_ideas(conexion):
        if not idea.texto.startswith(PREFIJO_SIN_FICHA):
            continue
        ruta = idea.texto[len(PREFIJO_SIN_FICHA):]
        if trabajo.es_ruta_de_pruebas(ruta):
            resultado.append((idea.id, idea.texto))
    return resultado


def _tareas_hola_sin_sesiones(conexion: sqlite3.Connection) -> list[tuple[UUID, str]]:
    resultado: list[tuple[UUID, str]] = []
    for fila in conexion.execute("SELECT id, titulo FROM tareas WHERE titulo = 'hola'").fetchall():
        tiene_sesion = conexion.execute(
            "SELECT 1 FROM sesiones WHERE tarea_id = ? LIMIT 1", (fila["id"],)
        ).fetchone()
        if tiene_sesion is None:
            resultado.append((UUID(fila["id"]), fila["titulo"]))
    return resultado


def _recortar(texto: str, largo: int = 90) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument(
        "--borrar", action="store_true", help="borra lo que lista. Sin esto, solo cuenta y lista."
    )
    argumentos = analizador.parse_args()

    conexion = db.conectar()
    try:
        ideas = _ideas_de_prueba(conexion)
        tareas = _tareas_hola_sin_sesiones(conexion)
        total = len(ideas) + len(tareas)

        print(f"{len(ideas)} idea(s) «proyecto sin ficha:» con ruta de pruebas:")
        for _id, texto in ideas:
            print(f"  - {_recortar(texto)}")
        print(f"\n{len(tareas)} tarea(s) «hola» sin sesiones:")
        for tarea_id, _titulo in tareas:
            print(f"  - {tarea_id}")
        print(f"\nTotal: {total}.")

        if not argumentos.borrar:
            print("\nNada borrado. Para borrar: --borrar")
            return 0

        for idea_id, _texto in ideas:
            conexion.execute("DELETE FROM ideas WHERE id = ?", (str(idea_id),))
        for tarea_id, _titulo in tareas:
            conexion.execute("DELETE FROM tareas WHERE id = ?", (str(tarea_id),))
        conexion.commit()
        print(f"\n{total} fila(s) borrada(s).")
        return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())

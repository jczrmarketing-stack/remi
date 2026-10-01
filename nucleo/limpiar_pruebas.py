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

--dia-cero (T1, Biblia v3.8): ideas creadas antes del 1-oct-2026 00:00
(Bogotá) y tareas cuya primera sesión es anterior o que no tienen ninguna.
Nunca un DELETE: archiva (estado `archivada`). --deshacer las devuelve.

    cd nucleo && uv run python limpiar_pruebas.py --dia-cero
    cd nucleo && uv run python limpiar_pruebas.py --dia-cero --si
    cd nucleo && uv run python limpiar_pruebas.py --dia-cero --deshacer
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from uuid import UUID

import db
import trabajo
from plata import BOGOTA

PREFIJO_SIN_FICHA = "proyecto sin ficha: "

# El corte de «día cero» (1-oct-2026, Biblia v3.8 / T1): todo lo creado, o
# cuya primera sesión fue, antes de medianoche de Bogotá de ese día es
# charla de prueba de antes de que Remi tuviera datos reales.
CORTE_DIA_CERO = datetime(2026, 10, 1, 0, 0, tzinfo=BOGOTA).astimezone(timezone.utc)


def _ideas_dia_cero(conexion: sqlite3.Connection, *, archivadas: bool) -> list[tuple[UUID, str]]:
    resultado: list[tuple[UUID, str]] = []
    for idea in db.listar_ideas(conexion):
        if (idea.estado == "archivada") != archivadas:
            continue
        creada = idea.creada_en if idea.creada_en.tzinfo else idea.creada_en.replace(tzinfo=timezone.utc)
        if creada < CORTE_DIA_CERO:
            resultado.append((idea.id, idea.texto))
    return resultado


def _tareas_dia_cero(conexion: sqlite3.Connection, *, archivadas: bool) -> list[tuple[UUID, str]]:
    resultado: list[tuple[UUID, str]] = []
    estado_sql = "= 'archivada'" if archivadas else "!= 'archivada'"
    filas = conexion.execute(f"SELECT id, titulo FROM tareas WHERE estado {estado_sql}").fetchall()
    for fila in filas:
        primera = conexion.execute(
            "SELECT MIN(inicio) AS inicio FROM sesiones WHERE tarea_id = ?", (fila["id"],)
        ).fetchone()
        if primera["inicio"] is None:
            resultado.append((UUID(fila["id"]), fila["titulo"]))
            continue
        inicio = datetime.fromisoformat(primera["inicio"])
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        if inicio < CORTE_DIA_CERO:
            resultado.append((UUID(fila["id"]), fila["titulo"]))
    return resultado


def candidatos_dia_cero(
    conexion: sqlite3.Connection,
) -> tuple[list[tuple[UUID, str]], list[tuple[UUID, str]]]:
    """Lo que `--dia-cero` archivaría ahora: ideas y tareas de antes del
    corte que todavía no están archivadas."""
    return (
        _ideas_dia_cero(conexion, archivadas=False),
        _tareas_dia_cero(conexion, archivadas=False),
    )


def archivar_dia_cero(conexion: sqlite3.Connection) -> int:
    """`--dia-cero --si`: nunca un DELETE. Devuelve cuántas filas tocó."""
    ideas, tareas = candidatos_dia_cero(conexion)
    for idea_id, _texto in ideas:
        conexion.execute("UPDATE ideas SET estado = 'archivada' WHERE id = ?", (str(idea_id),))
    for tarea_id, _titulo in tareas:
        conexion.execute("UPDATE tareas SET estado = 'archivada' WHERE id = ?", (str(tarea_id),))
    conexion.commit()
    return len(ideas) + len(tareas)


def deshacer_dia_cero(conexion: sqlite3.Connection) -> int:
    """`--dia-cero --deshacer`: vuelve a archivar exactamente lo que
    `archivar_dia_cero` archivó (mismo criterio, ahora sobre lo archivado),
    a su estado de antes — `enfriando` la idea, `hoy` la tarea."""
    ideas, tareas = (
        _ideas_dia_cero(conexion, archivadas=True),
        _tareas_dia_cero(conexion, archivadas=True),
    )
    for idea_id, _texto in ideas:
        conexion.execute("UPDATE ideas SET estado = 'enfriando' WHERE id = ?", (str(idea_id),))
    for tarea_id, _titulo in tareas:
        conexion.execute("UPDATE tareas SET estado = 'hoy' WHERE id = ?", (str(tarea_id),))
    conexion.commit()
    return len(ideas) + len(tareas)


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
    analizador.add_argument(
        "--dia-cero", action="store_true",
        help="ideas y tareas de antes del 1-oct-2026 (Bogotá). Nunca borra: archiva.",
    )
    analizador.add_argument(
        "--si", action="store_true", help="con --dia-cero: archiva lo que lista. Sin esto, solo cuenta."
    )
    analizador.add_argument(
        "--deshacer", action="store_true", help="con --dia-cero: devuelve lo archivado a su estado de antes."
    )
    argumentos = analizador.parse_args()

    if argumentos.dia_cero:
        return _main_dia_cero(argumentos)

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


def _main_dia_cero(argumentos: argparse.Namespace) -> int:
    conexion = db.conectar()
    try:
        if argumentos.deshacer:
            total = deshacer_dia_cero(conexion)
            print(f"{total} fila(s) devuelta(s) a su estado de antes.")
            return 0

        ideas, tareas = candidatos_dia_cero(conexion)
        print(f"{len(ideas)} idea(s) de antes del día cero:")
        for _id, texto in ideas:
            print(f"  - {_recortar(texto)}")
        print(f"\n{len(tareas)} tarea(s) de antes del día cero:")
        for tarea_id, titulo in tareas:
            print(f"  - {tarea_id} «{titulo}»")
        print(f"\nTotal: {len(ideas) + len(tareas)}.")

        if not argumentos.si:
            print("\nNada archivado. Para archivar: --dia-cero --si")
            return 0

        total = archivar_dia_cero(conexion)
        print(f"\n{total} fila(s) archivada(s) (estado = archivada, ningún DELETE).")
        return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())

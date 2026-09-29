#!/usr/bin/env python
"""Las tareas de prueba que quedaron de probar Remi.

Sin argumentos no borra nada: imprime numeradas las tareas en estado `hoy`
con sus sesiones, para que Juan Camilo elija. Con `--borrar 1,4,7` borra
esas y sus sesiones, después de imprimir qué se va.

    cd nucleo && uv run python limpiar_pruebas.py
    cd nucleo && uv run python limpiar_pruebas.py --borrar 1,4,7

Elegir cuáles no es decisión de este script: una tarea borrada no se
recupera. Las ideas de la Bandeja no se tocan nunca desde acá.
"""
from __future__ import annotations

import argparse
import sqlite3
from uuid import UUID

import db


def _listar(conexion: sqlite3.Connection) -> list[tuple[UUID, str, list[int], int]]:
    """Por cada tarea `hoy`: id, título, minutos de cada sesión y el total."""
    filas = []
    for tarea in db.listar_tareas_hoy(conexion):
        sesiones = db.listar_sesiones_tarea(conexion, tarea.id)
        minutos = [s.real_min for s in sesiones]
        filas.append((tarea.id, tarea.titulo, minutos, sum(minutos)))
    return filas


def _imprimir(filas: list[tuple[UUID, str, list[int], int]]) -> None:
    if not filas:
        print("No hay tareas en estado `hoy`.")
        return
    print(f"{len(filas)} tarea(s) en estado `hoy`:\n")
    for numero, (_id, titulo, minutos, total) in enumerate(filas, start=1):
        recortado = titulo if len(titulo) <= 52 else titulo[:51] + "…"
        detalle = f"{len(minutos)} sesión(es), {total} min" if minutos else "sin sesiones"
        print(f"  {numero:>2}. {recortado:<52}  {detalle}")


def _borrar(conexion: sqlite3.Connection, filas, numeros: list[int]) -> int:
    elegidas = []
    for numero in numeros:
        if not 1 <= numero <= len(filas):
            print(f"No hay una tarea {numero}: hay {len(filas)}. No borré nada.")
            return 0
        elegidas.append(filas[numero - 1])

    print("\nSe van estas, con sus sesiones:")
    for numero, (_id, titulo, minutos, total) in zip(numeros, elegidas):
        print(f"  {numero:>2}. {titulo}  ({len(minutos)} sesión(es), {total} min)")

    for tarea_id, _titulo, _minutos, _total in elegidas:
        # Las sesiones primero: la clave ajena apunta a la tarea.
        conexion.execute("DELETE FROM sesiones WHERE tarea_id = ?", (str(tarea_id),))
        conexion.execute("DELETE FROM tareas WHERE id = ?", (str(tarea_id),))
    conexion.commit()
    return len(elegidas)


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--borrar",
        metavar="1,4,7",
        help="números de la lista, separados por comas. Sin esto no se borra nada.",
    )
    argumentos = analizador.parse_args()

    conexion = db.conectar()
    try:
        filas = _listar(conexion)
        _imprimir(filas)

        if argumentos.borrar is None:
            print("\nNada borrado. Para borrar: --borrar 1,4,7")
            return 0

        try:
            numeros = [int(n) for n in argumentos.borrar.split(",") if n.strip()]
        except ValueError:
            print("\n--borrar espera números separados por comas, como 1,4,7.")
            return 1
        if not numeros:
            print("\n--borrar sin números: no borré nada.")
            return 1

        cuantas = _borrar(conexion, filas, numeros)
        if cuantas:
            print(f"\n{cuantas} tarea(s) borrada(s). Las ideas de la Bandeja no se tocaron.")
        return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""SQLite: fuente de verdad de Remi. remi.db nunca va al repo (ver .gitignore)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from uuid import UUID

from modelos import Tarea

RUTA_DB = Path(os.environ.get("REMI_DB_PATH", str(Path(__file__).resolve().parent / "remi.db")))

ESQUEMA_TAREAS = """
CREATE TABLE IF NOT EXISTS tareas (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    proyecto_id TEXT,
    estado TEXT NOT NULL,
    paso_minimo TEXT NOT NULL,
    estimado_min INTEGER,
    real_min INTEGER,
    compartible INTEGER NOT NULL
)
"""


def conectar(ruta: Path = RUTA_DB) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute(ESQUEMA_TAREAS)
    return conexion


def guardar_tarea(conexion: sqlite3.Connection, tarea: Tarea) -> None:
    conexion.execute(
        """
        INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(tarea.id),
            tarea.titulo,
            str(tarea.proyecto_id) if tarea.proyecto_id else None,
            tarea.estado,
            tarea.paso_minimo,
            tarea.estimado_min,
            tarea.real_min,
            int(tarea.compartible),
        ),
    )
    conexion.commit()


def _fila_a_tarea(fila: sqlite3.Row) -> Tarea:
    return Tarea(
        id=UUID(fila["id"]),
        titulo=fila["titulo"],
        proyecto_id=UUID(fila["proyecto_id"]) if fila["proyecto_id"] else None,
        estado=fila["estado"],
        paso_minimo=fila["paso_minimo"],
        estimado_min=fila["estimado_min"],
        real_min=fila["real_min"],
        compartible=bool(fila["compartible"]),
    )


def listar_tareas_por_estado(conexion: sqlite3.Connection, estado: str) -> list[Tarea]:
    filas = conexion.execute(
        "SELECT * FROM tareas WHERE estado = ? ORDER BY rowid", (estado,)
    ).fetchall()
    return [_fila_a_tarea(fila) for fila in filas]

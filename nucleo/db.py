"""SQLite: fuente de verdad de Remi. remi.db nunca va al repo (ver .gitignore)."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from modelos import Sesion, Tarea

RUTA_DB = Path(os.environ.get("REMI_DB_PATH", str(Path(__file__).resolve().parent / "remi.db")))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tareas (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    proyecto_id TEXT,
    estado TEXT NOT NULL,
    paso_minimo TEXT NOT NULL,
    estimado_min INTEGER,
    real_min INTEGER,
    compartible INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sesiones (
    id TEXT PRIMARY KEY,
    tarea_id TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT,
    real_min INTEGER NOT NULL,
    app_contexto TEXT,
    FOREIGN KEY (tarea_id) REFERENCES tareas(id)
);

CREATE INDEX IF NOT EXISTS idx_sesiones_tarea_id ON sesiones(tarea_id);

CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY,
    texto TEXT NOT NULL,
    origen TEXT NOT NULL,
    creada_en TEXT NOT NULL,
    enfria_hasta TEXT NOT NULL,
    estado TEXT NOT NULL,
    problema_vision INTEGER
);

CREATE TABLE IF NOT EXISTS nudges (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    voz TEXT NOT NULL,
    salida_amable INTEGER NOT NULL,
    respuesta TEXT
);

CREATE TABLE IF NOT EXISTS entregas (
    id TEXT PRIMARY KEY,
    cliente TEXT NOT NULL,
    proyecto_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    monto REAL,
    estado TEXT NOT NULL,
    compartible INTEGER NOT NULL
);
"""


_rutas_con_esquema_listo: set[str] = set()


def inicializar_esquema(ruta: Path = RUTA_DB) -> None:
    """El CREATE TABLE/INDEX corre una sola vez por archivo, no en cada
    conectar() — PRAGMA foreign_keys en cambio es por-conexión en SQLite y
    hay que activarlo siempre, eso sí lo hace conectar()."""
    clave = str(ruta)
    if clave in _rutas_con_esquema_listo:
        return
    conexion = sqlite3.connect(ruta)
    try:
        conexion.executescript(ESQUEMA)
        conexion.commit()
    finally:
        conexion.close()
    _rutas_con_esquema_listo.add(clave)


def conectar(ruta: Path = RUTA_DB) -> sqlite3.Connection:
    inicializar_esquema(ruta)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_tarea(conexion: sqlite3.Connection, tarea: Tarea) -> None:
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


def actualizar_estado_tarea(
    conexion: sqlite3.Connection, tarea_id: UUID, estado: str
) -> Tarea | None:
    """None si no existe esa tarea. El estado ya viene validado contra el
    contrato por Pydantic antes de llegar acá (Literal en el endpoint)."""
    conexion.execute("UPDATE tareas SET estado = ? WHERE id = ?", (estado, str(tarea_id)))
    conexion.commit()
    fila = conexion.execute("SELECT * FROM tareas WHERE id = ?", (str(tarea_id),)).fetchone()
    return _fila_a_tarea(fila) if fila else None


def listar_tareas_hoy(conexion: sqlite3.Connection) -> list[Tarea]:
    filas = conexion.execute(
        "SELECT * FROM tareas WHERE estado = 'hoy' ORDER BY rowid"
    ).fetchall()
    return [_fila_a_tarea(fila) for fila in filas]


def crear_sesion(conexion: sqlite3.Connection, sesion: Sesion) -> None:
    conexion.execute(
        """
        INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(sesion.id),
            str(sesion.tarea_id),
            sesion.inicio.isoformat(),
            sesion.fin.isoformat() if sesion.fin else None,
            sesion.real_min,
            sesion.app_contexto,
        ),
    )
    conexion.commit()


def _fila_a_sesion(fila: sqlite3.Row) -> Sesion:
    return Sesion(
        id=UUID(fila["id"]),
        tarea_id=UUID(fila["tarea_id"]),
        inicio=fila["inicio"],
        fin=fila["fin"],
        real_min=fila["real_min"],
        app_contexto=fila["app_contexto"],
    )


def listar_sesiones_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> list[Sesion]:
    filas = conexion.execute(
        "SELECT * FROM sesiones WHERE tarea_id = ? ORDER BY inicio", (str(tarea_id),)
    ).fetchall()
    return [_fila_a_sesion(fila) for fila in filas]


def listar_sesiones_cerradas_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> list[Sesion]:
    filas = conexion.execute(
        "SELECT * FROM sesiones WHERE tarea_id = ? AND fin IS NOT NULL ORDER BY inicio",
        (str(tarea_id),),
    ).fetchall()
    return [_fila_a_sesion(fila) for fila in filas]


def ultima_sesion_cerrada_min(conexion: sqlite3.Connection, tarea_id: UUID) -> int | None:
    """El dato que pide la ley 1: cuánto tardó la última vez. None si la
    tarea nunca tuvo una sesión cerrada — no hay de dónde sacarlo."""
    fila = conexion.execute(
        "SELECT real_min FROM sesiones WHERE tarea_id = ? AND fin IS NOT NULL "
        "ORDER BY fin DESC LIMIT 1",
        (str(tarea_id),),
    ).fetchone()
    return fila["real_min"] if fila else None


def sesion_abierta_de_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> UUID | None:
    fila = conexion.execute(
        "SELECT id FROM sesiones WHERE tarea_id = ? AND fin IS NULL ORDER BY inicio DESC LIMIT 1",
        (str(tarea_id),),
    ).fetchone()
    return UUID(fila["id"]) if fila else None


def cerrar_sesion(conexion: sqlite3.Connection, sesion_id: UUID) -> Sesion | None:
    """Escribe `fin` y calcula `real_min` desde `inicio` (ley 1). None si la
    sesión no existe o ya estaba cerrada — cerrar dos veces no la altera."""
    fila = conexion.execute(
        "SELECT * FROM sesiones WHERE id = ?", (str(sesion_id),)
    ).fetchone()
    if fila is None or fila["fin"] is not None:
        return None

    inicio = datetime.fromisoformat(fila["inicio"])
    fin = datetime.now(timezone.utc)
    real_min = max(0, round((fin - inicio).total_seconds() / 60))

    conexion.execute(
        "UPDATE sesiones SET fin = ?, real_min = ? WHERE id = ?",
        (fin.isoformat(), real_min, str(sesion_id)),
    )
    conexion.commit()
    return _fila_a_sesion(
        conexion.execute("SELECT * FROM sesiones WHERE id = ?", (str(sesion_id),)).fetchone()
    )

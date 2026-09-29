import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

import pytest

import db
from modelos import Sesion


def test_foreign_keys_esta_activo_por_conexion(tmp_path):
    conexion = db.conectar(tmp_path / "remi.db")
    fila = conexion.execute("PRAGMA foreign_keys").fetchone()
    assert fila[0] == 1


def test_sesion_de_tarea_inexistente_no_se_puede_insertar(tmp_path):
    conexion = db.conectar(tmp_path / "remi.db")
    sesion = Sesion(
        id=uuid4(),
        tarea_id=uuid4(),  # no existe ninguna tarea con este id
        inicio=datetime.now(timezone.utc),
        fin=None,
        real_min=0,
        app_contexto=None,
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.crear_sesion(conexion, sesion)


def test_indice_de_sesiones_por_tarea_existe(tmp_path):
    conexion = db.conectar(tmp_path / "remi.db")
    fila = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_sesiones_tarea_id'"
    ).fetchone()
    assert fila is not None


def test_inicializar_esquema_no_repite_el_executescript(tmp_path, monkeypatch):
    ruta = tmp_path / "remi.db"
    conteo = {"n": 0}
    original_connect = db.sqlite3.connect

    def connect_contado(*args: object, **kwargs: object) -> sqlite3.Connection:
        conteo["n"] += 1
        return original_connect(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(db.sqlite3, "connect", connect_contado)

    # inicializar_esquema abre su propia conexión SOLO si todavía no
    # corrió el executescript para esta ruta — de la segunda llamada en
    # adelante, el guard corta antes de llegar a sqlite3.connect.
    db.inicializar_esquema(ruta)
    db.inicializar_esquema(ruta)
    db.inicializar_esquema(ruta)

    assert conteo["n"] == 1

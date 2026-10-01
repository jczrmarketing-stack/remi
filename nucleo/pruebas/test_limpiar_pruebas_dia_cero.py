"""T1 punto 2: `limpiar_pruebas.py --dia-cero`. Nunca un DELETE — archiva
(estado `archivada`) y `--deshacer` lo devuelve. Sin `--si` solo cuenta y
lista."""
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import limpiar_pruebas
from modelos import Idea, Tarea


def _db(tmp_path, monkeypatch):
    ruta = tmp_path / "remi.db"
    monkeypatch.setenv("REMI_DB_PATH", str(ruta))
    for nombre in ("db",):
        sys.modules.pop(nombre, None)
    import db as _db_mod

    return _db_mod


ANTES = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
DESPUES = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _idea(creada_en, estado="enfriando"):
    return Idea(
        id=uuid4(), texto=f"idea {creada_en.isoformat()}", origen="texto",
        creada_en=creada_en, enfria_hasta=creada_en + timedelta(hours=48),
        estado=estado, problema_vision=None, tema=None,
    )


def _tarea(conexion, estado="hoy"):
    tarea = Tarea(
        id=uuid4(), titulo="hola", proyecto_id=None, estado=estado,
        paso_minimo="x", estimado_min=None, real_min=None, hora=None,
        fecha_limite=None, compartible=False,
    )
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, "
        "real_min, hora, fecha_limite, compartible) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (str(tarea.id), tarea.titulo, None, tarea.estado, tarea.paso_minimo, None, None,
         None, None, 0),
    )
    conexion.commit()
    return tarea


def _sesion(conexion, tarea_id, inicio):
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) "
        "VALUES (?, ?, ?, ?, ?, NULL)",
        (str(uuid4()), str(tarea_id), inicio.isoformat(), inicio.isoformat(), 1),
    )
    conexion.commit()


def test_lista_sin_tocar_nada_sin_si(tmp_path, monkeypatch):
    dbmod = _db(tmp_path, monkeypatch)
    conexion = dbmod.conectar()
    dbmod.crear_idea(conexion, _idea(ANTES))
    dbmod.crear_idea(conexion, _idea(DESPUES))
    vieja = _tarea(conexion)
    nueva = _tarea(conexion)
    _sesion(conexion, vieja.id, ANTES)
    _sesion(conexion, nueva.id, DESPUES)

    ideas, tareas = limpiar_pruebas.candidatos_dia_cero(conexion)
    assert len(ideas) == 1
    assert {t[0] for t in tareas} == {vieja.id}

    # Sin --si: nada cambia.
    assert conexion.execute("SELECT estado FROM ideas WHERE estado = 'archivada'").fetchall() == []
    assert conexion.execute("SELECT estado FROM tareas WHERE estado = 'archivada'").fetchall() == []


def test_tarea_sin_ninguna_sesion_tambien_es_dia_cero(tmp_path, monkeypatch):
    dbmod = _db(tmp_path, monkeypatch)
    conexion = dbmod.conectar()
    sin_sesion = _tarea(conexion)

    _, tareas = limpiar_pruebas.candidatos_dia_cero(conexion)
    assert {t[0] for t in tareas} == {sin_sesion.id}


def test_si_archiva_y_deshacer_devuelve(tmp_path, monkeypatch):
    dbmod = _db(tmp_path, monkeypatch)
    conexion = dbmod.conectar()
    idea = _idea(ANTES)
    dbmod.crear_idea(conexion, idea)
    tarea = _tarea(conexion)
    _sesion(conexion, tarea.id, ANTES)

    antes_ideas = conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
    antes_tareas = conexion.execute("SELECT COUNT(*) FROM tareas").fetchone()[0]

    limpiar_pruebas.archivar_dia_cero(conexion)

    assert conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == antes_ideas
    assert conexion.execute("SELECT COUNT(*) FROM tareas").fetchone()[0] == antes_tareas
    assert conexion.execute(
        "SELECT estado FROM ideas WHERE id = ?", (str(idea.id),)
    ).fetchone()[0] == "archivada"
    assert conexion.execute(
        "SELECT estado FROM tareas WHERE id = ?", (str(tarea.id),)
    ).fetchone()[0] == "archivada"

    limpiar_pruebas.deshacer_dia_cero(conexion)

    assert conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == antes_ideas
    assert conexion.execute("SELECT COUNT(*) FROM tareas").fetchone()[0] == antes_tareas
    assert conexion.execute(
        "SELECT estado FROM ideas WHERE id = ?", (str(idea.id),)
    ).fetchone()[0] == "enfriando"
    assert conexion.execute(
        "SELECT estado FROM tareas WHERE id = ?", (str(tarea.id),)
    ).fetchone()[0] == "hoy"


def test_nunca_hay_un_delete_en_dia_cero():
    import inspect

    for funcion in (
        limpiar_pruebas.candidatos_dia_cero,
        limpiar_pruebas.archivar_dia_cero,
        limpiar_pruebas.deshacer_dia_cero,
        limpiar_pruebas._ideas_dia_cero,
        limpiar_pruebas._tareas_dia_cero,
    ):
        assert "DELETE FROM" not in inspect.getsource(funcion)

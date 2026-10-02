"""T4.2 · Forma D: GET /semana, de lunes (Bogotá) a ahora."""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import plata


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "semana", "bandeja", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _tarea(conexion, titulo="x", estado="hoy", fecha_limite=None) -> str:
    tid = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, "
        "real_min, compartible, hora, fecha_limite) VALUES (?, ?, NULL, ?, 'p', NULL, NULL, 0, NULL, ?)",
        (tid, titulo, estado, fecha_limite),
    )
    conexion.commit()
    return tid


def _sesion_cerrada(conexion, tarea_id, inicio, fin, real_min, app_contexto=None) -> None:
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid4()), tarea_id, inicio.isoformat(), fin.isoformat(), real_min, app_contexto),
    )
    conexion.commit()


def test_vacio_sin_datos(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/semana").json()

    assert cuerpo["cerrado"] == []
    assert cuerpo["aplazado"] == []
    assert cuerpo["ideas_frias"] == 0
    assert cuerpo["destacada"] is None


def test_cerrado_lista_las_sesiones_de_esta_semana(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
    lunes = plata._lunes(ahora)
    tarea_id = _tarea(conexion, titulo="Contrato de Alfonso")
    _sesion_cerrada(conexion, tarea_id, lunes, lunes + timedelta(minutes=40), 40, "upvisuals")
    _sesion_cerrada(conexion, tarea_id, lunes - timedelta(days=3), lunes - timedelta(days=3), 10, "vieja")
    conexion.close()

    import semana

    resultado = semana.calcular(db.conectar(), ahora)
    assert [(c.titulo, c.tema, c.real_min) for c in resultado.cerrado] == [("Contrato de Alfonso", "upvisuals", 40)]


def test_aplazado_son_tareas_abiertas_con_fecha_ya_vencida_maximo_5(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
    for n in range(7):
        _tarea(
            conexion, titulo=f"vencida {n}", estado="camino",
            fecha_limite=(ahora - timedelta(days=n + 1)).isoformat(),
        )
    _tarea(conexion, titulo="futura", estado="camino", fecha_limite=(ahora + timedelta(days=1)).isoformat())
    _tarea(conexion, titulo="hecha vencida", estado="hecha", fecha_limite=(ahora - timedelta(days=1)).isoformat())
    conexion.close()

    import semana

    resultado = semana.calcular(db.conectar(), ahora)
    assert len(resultado.aplazado) == 5
    assert all(a.titulo.startswith("vencida") for a in resultado.aplazado)


def test_ideas_frias_cuenta_sin_listar(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    import db

    cliente.post("/mensaje", json={"texto": "se me ocurrió una idea"})
    conexion = db.conectar()
    conexion.execute("UPDATE ideas SET enfria_hasta = ?", ((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),))
    conexion.commit()
    conexion.close()

    cuerpo = cliente.get("/semana").json()
    assert cuerpo["ideas_frias"] == 1


def test_destacada_aparece_en_semana(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "se me ocurrió una idea para destacar"})
    idea_id = cliente.get("/bandeja").json()[0]["idea"]["id"]
    cliente.post(f"/idea/{idea_id}/destacar", json={"destacada": True})

    cuerpo = cliente.get("/semana").json()
    assert cuerpo["destacada"]["id"] == idea_id
    assert cuerpo["destacada"]["texto"] == "se me ocurrió una idea para destacar"

"""Entrega (3f · 2): el parser de reglas y el CRUD contra la app real."""
import importlib
import sys

import pytest
from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "entregas"):
        sys.modules.pop(nombre, None)
    import db
    import entregas
    import servidor

    importlib.reload(db)
    importlib.reload(entregas)
    importlib.reload(servidor)
    return servidor


def test_parsea_cliente_fecha_y_monto():
    from entregas import parsear_entrega

    parseada = parsear_entrega("entrega para Alfonso el 18 de octubre por 5.000")
    assert parseada is not None
    assert parseada.cliente == "Alfonso"
    assert parseada.monto == 5000.0
    assert parseada.fecha.month == 10
    assert parseada.fecha.day == 18


def test_no_inventa_si_falta_la_forma():
    from entregas import parsear_entrega

    assert parsear_entrega("hoy es un lindo día") is None


def test_crear_entrega_desde_texto(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/entregas", json={"texto": "entrega para Alfonso el 18 de octubre por 5.000"})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["cliente"] == "Alfonso"
    assert cuerpo["monto"] == 5000.0
    assert cuerpo["estado"] == "camino"
    assert cuerpo["compartible"] is True


def test_texto_sin_forma_da_422(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/entregas", json={"texto": "guardame esto para después"})
    assert respuesta.status_code == 422


def test_de_proyecto_encuentra_la_entrega_viva(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    creada = cliente.post(
        "/entregas",
        json={"texto": "entrega para Alfonso el 18 de octubre por 5.000", "tema": "malik"},
    ).json()

    from entregas import _proyecto_id_de_tema

    proyecto_id = str(_proyecto_id_de_tema("malik"))
    respuesta = cliente.get(f"/entregas/de-proyecto/{proyecto_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creada["id"]


def test_de_proyecto_sin_entrega_da_null(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    from entregas import _proyecto_id_de_tema

    respuesta = cliente.get(f"/entregas/de-proyecto/{_proyecto_id_de_tema('nada')}")
    assert respuesta.status_code == 200
    assert respuesta.json() is None

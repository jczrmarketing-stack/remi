"""T8: «qué te falta para que estés al 100% listo» no se guarda como idea
— es una pregunta de estado, sin modelo, sin inventar un número."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "trabajo", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_que_te_falta_no_crea_una_idea(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/mensaje", json={"texto": "que te falta para que estes al 100% listo"}
    )

    assert respuesta.json()["tipo"] == "pregunta"
    assert cliente.get("/bandeja").json() == []


def test_sin_preguntas_pendientes_lo_dice(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "qué te falta?"})

    assert respuesta.json()["texto"] == "No tengo ninguna pregunta pendiente ahora."


def test_una_frase_sin_que_falta_sigue_normal(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "se me ocurrió una idea"})

    assert respuesta.json()["tipo"] == "idea"

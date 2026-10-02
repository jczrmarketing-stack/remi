"""T4.3 · Forma E: destacada en IdeaBandeja, POST /idea/{id}/destacar."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "bandeja", "db", "modelos", "clasificar", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _crear_idea(cliente: TestClient, texto: str) -> str:
    cliente.post("/mensaje", json={"texto": texto})
    return cliente.get("/bandeja").json()[0]["idea"]["id"]


def test_bandeja_trae_destacada_false_por_defecto(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    _crear_idea(cliente, "se me ocurrió una idea")

    assert cliente.get("/bandeja").json()[0]["destacada"] is False


def test_destacar_una_idea_la_marca(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    idea_id = _crear_idea(cliente, "se me ocurrió una idea")

    respuesta = cliente.post(f"/idea/{idea_id}/destacar", json={"destacada": True})

    assert respuesta.status_code == 200
    assert respuesta.json()["destacada"] is True
    assert cliente.get("/bandeja").json()[0]["destacada"] is True


def test_destacar_una_nueva_le_quita_la_marca_a_la_anterior(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    primera = _crear_idea(cliente, "primera idea suelta")
    cliente.post(f"/idea/{primera}/destacar", json={"destacada": True})
    cliente.post("/mensaje", json={"texto": "segunda idea distinta"})
    segunda = next(i["idea"]["id"] for i in cliente.get("/bandeja").json() if i["idea"]["id"] != primera)

    cliente.post(f"/idea/{segunda}/destacar", json={"destacada": True})

    por_id = {i["idea"]["id"]: i["destacada"] for i in cliente.get("/bandeja").json()}
    assert por_id[primera] is False
    assert por_id[segunda] is True


def test_quitar_la_marca(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    idea_id = _crear_idea(cliente, "se me ocurrió una idea")
    cliente.post(f"/idea/{idea_id}/destacar", json={"destacada": True})

    respuesta = cliente.post(f"/idea/{idea_id}/destacar", json={"destacada": False})

    assert respuesta.json()["destacada"] is False
    assert cliente.get("/bandeja").json()[0]["destacada"] is False


def test_destacar_idea_inexistente_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/idea/99999999-9999-9999-9999-999999999999/destacar", json={"destacada": True}
    )

    assert respuesta.status_code == 404

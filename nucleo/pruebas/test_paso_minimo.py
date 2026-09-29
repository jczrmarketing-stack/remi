import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar_servidor():
    for nombre in ("servidor", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_paso_minimo_nace_universal_no_copia_el_titulo(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Llamar al banco"}).json()
    assert creada["tarea"]["titulo"] == "Llamar al banco"
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["tarea"]["paso_minimo"] != creada["tarea"]["titulo"]
    # La voz sigue hablando del título, no del paso_minimo (son cosas
    # distintas ahora).
    assert "Llamar al banco" in creada["voz"]


def test_fijar_paso_minimo_de_verdad(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Llamar al banco"}).json()
    tarea_id = creada["tarea"]["id"]

    respuesta = cliente.post(
        f"/tarea/{tarea_id}/paso-minimo", json={"paso_minimo": "Marcar el número"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["paso_minimo"] == "Marcar el número"

    inexistente = cliente.post(
        "/tarea/00000000-0000-0000-0000-000000000000/paso-minimo",
        json={"paso_minimo": "algo"},
    )
    assert inexistente.status_code == 404

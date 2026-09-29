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


def test_historial_devuelve_sesiones_cerradas_y_total(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Llamar al banco"}).json()
    tarea_id = creada["tarea"]["id"]
    sesion_id = creada["sesion"]["id"]

    # Sin sesiones cerradas todavía: historial vacío, no revienta.
    vacio = cliente.get(f"/tarea/{tarea_id}/historial").json()
    assert vacio == {"sesiones": [], "total_min": 0}

    cliente.post(f"/sesion/{sesion_id}/cerrar")

    historial = cliente.get(f"/tarea/{tarea_id}/historial").json()
    assert len(historial["sesiones"]) == 1
    assert historial["sesiones"][0]["id"] == sesion_id
    assert historial["total_min"] == historial["sesiones"][0]["real_min"]


def test_hoy_incluye_ultima_vez_min(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Mandar la factura"}).json()
    tarea_id = creada["tarea"]["id"]
    sesion_id = creada["sesion"]["id"]

    # Sesión abierta todavía: no hay "última vez" (ley 1: no inventar un dato).
    hoy = cliente.get("/hoy").json()
    encontrada = next(t for t in hoy if t["tarea"]["id"] == tarea_id)
    assert encontrada["ultima_vez_min"] is None

    cliente.post(f"/sesion/{sesion_id}/cerrar")

    hoy = cliente.get("/hoy").json()
    encontrada = next(t for t in hoy if t["tarea"]["id"] == tarea_id)
    assert encontrada["ultima_vez_min"] is not None

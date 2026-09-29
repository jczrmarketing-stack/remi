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


def test_actualizar_estado_valida_contra_el_contrato(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "voy a mandar la factura"}).json()
    tarea_id = creada["tarea"]["id"]

    respuesta = cliente.post(f"/tarea/{tarea_id}/estado", json={"estado": "camino"})
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "camino"

    # Un estado fuera del contrato no pasa (Literal lo valida antes de tocar la DB).
    invalido = cliente.post(f"/tarea/{tarea_id}/estado", json={"estado": "urgente"})
    assert invalido.status_code == 422

    # Tarea que no existe: 404, no revienta.
    inexistente = cliente.post(
        "/tarea/00000000-0000-0000-0000-000000000000/estado", json={"estado": "camino"}
    )
    assert inexistente.status_code == 404


def test_pasar_a_hecha_cierra_la_sesion_abierta(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)
    import db

    creada = cliente.post("/mensaje", json={"texto": "voy a llamar al banco"}).json()
    tarea_id = creada["tarea"]["id"]
    sesion_id = creada["sesion"]["id"]
    assert creada["sesion"]["fin"] is None

    respuesta = cliente.post(f"/tarea/{tarea_id}/estado", json={"estado": "hecha"})
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "hecha"

    conexion = db.conectar()
    try:
        sesiones = db.listar_sesiones_tarea(conexion, tarea_id)
    finally:
        conexion.close()
    cerrada = next(s for s in sesiones if str(s.id) == sesion_id)
    assert cerrada.fin is not None

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


def test_cerrar_sesion_escribe_fin_y_calcula_real_min(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "ahora llamo al banco"}).json()
    sesion_id = creada["sesion"]["id"]
    assert creada["sesion"]["fin"] is None
    assert creada["sesion"]["real_min"] == 0

    respuesta = cliente.post(f"/sesion/{sesion_id}/cerrar")
    assert respuesta.status_code == 200
    cerrada = respuesta.json()
    assert cerrada["fin"] is not None
    assert cerrada["real_min"] >= 0

    # Cerrar una sesión que no existe (o ya cerrada): 404, sin culpa, no revienta.
    otra = cliente.post(f"/sesion/{sesion_id}/cerrar")
    assert otra.status_code == 404


def test_mensaje_no_deja_dos_sesiones_abiertas_para_la_misma_tarea(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)
    import db

    creada = cliente.post("/mensaje", json={"texto": "voy a mandar la factura"}).json()
    tarea_id = creada["tarea"]["id"]

    conexion = db.conectar()
    try:
        abierta = db.sesion_abierta_de_tarea(conexion, tarea_id)
    finally:
        conexion.close()
    assert str(abierta) == creada["sesion"]["id"]

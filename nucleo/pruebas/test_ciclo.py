import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar_servidor():
    """Importa (o reimporta) db y servidor en frío — simula un arranque del proceso."""
    for nombre in ("servidor", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_mensaje_crea_tarea_y_sobrevive_a_reiniciar_servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))

    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "Llamar al banco"})
    assert respuesta.status_code == 200
    tarea_creada = respuesta.json()
    assert tarea_creada["titulo"] == "Llamar al banco"
    assert tarea_creada["estado"] == "hoy"

    # Reinicio del servidor: módulos frescos, misma ruta de remi.db en disco.
    servidor_reiniciado = _arrancar_servidor()
    cliente_reiniciado = TestClient(servidor_reiniciado.app)

    respuesta_hoy = cliente_reiniciado.get("/hoy")
    assert respuesta_hoy.status_code == 200
    tareas_hoy = respuesta_hoy.json()

    assert any(t["id"] == tarea_creada["id"] for t in tareas_hoy)
    encontrada = next(t for t in tareas_hoy if t["id"] == tarea_creada["id"])
    assert encontrada["titulo"] == "Llamar al banco"
    assert encontrada["estado"] == "hoy"

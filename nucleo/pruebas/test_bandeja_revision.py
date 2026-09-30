"""GET /bandeja y POST /idea/{id}/revision (Fase 3, tarea 1).

Ley 6: una idea no se revisa antes de sus 48 h de enfriamiento — eso es el
409. Las tres decisiones (soltar, mantener, tarea) nunca borran la fila.
"""
import importlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "bandeja", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _crear_idea_fria(servidor, cliente: TestClient) -> str:
    """Guarda una idea y le corre `enfria_hasta` al pasado: ya está fría."""
    import db

    cliente.post("/mensaje", json={"texto": "se me ocurrió algo"}).json()
    conexion = db.conectar()
    try:
        fila = conexion.execute("SELECT id FROM ideas").fetchone()
        idea_id = fila["id"]
        ya_paso = datetime.now(timezone.utc) - timedelta(hours=1)
        conexion.execute(
            "UPDATE ideas SET enfria_hasta = ? WHERE id = ?",
            (ya_paso.isoformat(), idea_id),
        )
        conexion.commit()
    finally:
        conexion.close()
    return str(idea_id)


def test_bandeja_lista_lo_abierto_con_fria(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "recién se me ocurrió"})
    idea_id = _crear_idea_fria(servidor, cliente)

    bandeja_vista = cliente.get("/bandeja").json()
    assert len(bandeja_vista) == 2
    por_id = {f["idea"]["id"]: f["fria"] for f in bandeja_vista}
    assert por_id[idea_id] is True
    assert any(fria is False for fria in por_id.values())


def test_revisar_antes_de_tiempo_es_409(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.post("/mensaje", json={"texto": "recién se me ocurrió"}).json()
    import db

    conexion = db.conectar()
    idea_id = conexion.execute("SELECT id FROM ideas").fetchone()["id"]
    conexion.close()

    respuesta = cliente.post(f"/idea/{idea_id}/revision", json={"decision": "soltar"})
    assert respuesta.status_code == 409


def test_revisar_idea_que_no_existe_es_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    from uuid import uuid4

    respuesta = cliente.post(f"/idea/{uuid4()}/revision", json={"decision": "soltar"})
    assert respuesta.status_code == 404


def test_soltar_cierra_sin_borrar_la_fila(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    idea_id = _crear_idea_fria(servidor, cliente)

    respuesta = cliente.post(f"/idea/{idea_id}/revision", json={"decision": "soltar"})
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["idea"]["estado"] == "soltada"
    assert cuerpo["tarea"] is None

    import db

    conexion = db.conectar()
    assert conexion.execute("SELECT COUNT(*) c FROM ideas").fetchone()["c"] == 1
    conexion.close()
    # Ya cerrada, sale de la Bandeja.
    assert cliente.get("/bandeja").json() == []


def test_mantener_vuelve_a_enfriar_48_horas(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    idea_id = _crear_idea_fria(servidor, cliente)

    antes = datetime.now(timezone.utc)
    respuesta = cliente.post(f"/idea/{idea_id}/revision", json={"decision": "mantener"})
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["idea"]["estado"] == "enfriando"
    nueva_hasta = datetime.fromisoformat(cuerpo["idea"]["enfria_hasta"])
    assert timedelta(hours=47, minutes=59) < (nueva_hasta - antes) < timedelta(hours=48, minutes=1)
    # Sigue abierta, ya no está fría.
    bandeja_vista = cliente.get("/bandeja").json()
    assert len(bandeja_vista) == 1
    assert bandeja_vista[0]["fria"] is False


def test_tarea_crea_tarea_normal_y_cierra_la_idea_como_proyecto(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    idea_id = _crear_idea_fria(servidor, cliente)

    respuesta = cliente.post(f"/idea/{idea_id}/revision", json={"decision": "tarea"})
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["idea"]["estado"] == "proyecto"
    assert cuerpo["tarea"] is not None
    assert cuerpo["tarea"]["titulo"] == "se me ocurrió algo"
    assert cuerpo["tarea"]["estado"] == "hoy"

    hoy = cliente.get("/hoy").json()
    assert len(hoy) == 1
    assert hoy[0]["tarea"]["id"] == cuerpo["tarea"]["id"]
    # Ya no está en la Bandeja.
    assert cliente.get("/bandeja").json() == []

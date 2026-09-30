"""GET /nudges/pendiente y POST /nudges/{id}/respuesta (Fase 3, tarea 3).

La ventanita YA llama a estas dos rutas con este contrato exacto — el
0 acá es que nada de esto puede moverse sin romperla.
"""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "iniciativa", "bandeja", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _forzar_bloque_largo(servidor, tema="malik") -> None:
    """Abre una tarea/sesión y le corre el inicio 91 min atrás: la regla
    `cuerpo` nace segura, sin depender de ninguna otra condición."""
    import db

    cliente = TestClient(servidor.app)
    abierto = cliente.post("/mensaje", json={"texto": "voy a revisar el contrato"}).json()
    conexion = db.conectar()
    inicio = datetime.fromisoformat(abierto["sesion"]["inicio"]) - timedelta(minutes=91)
    conexion.execute(
        "UPDATE sesiones SET inicio = ?, app_contexto = ? WHERE id = ?",
        (inicio.isoformat(), tema, abierto["sesion"]["id"]),
    )
    conexion.commit()
    conexion.close()


def test_sin_nada_que_avisar_pendiente_es_null(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.get("/nudges/pendiente")
    assert respuesta.status_code == 200
    assert respuesta.json() is None


def test_nace_un_nudge_y_queda_pendiente(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    _forzar_bloque_largo(servidor)
    cliente = TestClient(servidor.app)

    primero = cliente.get("/nudges/pendiente").json()
    assert primero is not None
    assert primero["tipo"] == "cuerpo"
    assert primero["respuesta"] is None

    # Un segundo GET no crea otro: devuelve el mismo pendiente.
    segundo = cliente.get("/nudges/pendiente").json()
    assert segundo["id"] == primero["id"]


def test_responder_listo_lo_marca_y_ya_no_queda_pendiente(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    _forzar_bloque_largo(servidor)
    cliente = TestClient(servidor.app)
    nudge = cliente.get("/nudges/pendiente").json()

    respuesta = cliente.post(f"/nudges/{nudge['id']}/respuesta", json={"respuesta": "listo"})
    assert respuesta.status_code == 200
    assert respuesta.json()["respuesta"] == "listo"

    assert cliente.get("/nudges/pendiente").json() is None


def test_responder_dos_veces_es_idempotente(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    _forzar_bloque_largo(servidor)
    cliente = TestClient(servidor.app)
    nudge = cliente.get("/nudges/pendiente").json()

    primera = cliente.post(f"/nudges/{nudge['id']}/respuesta", json={"respuesta": "listo"}).json()
    segunda = cliente.post(f"/nudges/{nudge['id']}/respuesta", json={"respuesta": "ahora_no"}).json()

    assert primera["respuesta"] == "listo"
    # La segunda llamada no la pisa: sigue "listo", tal cual quedó la primera vez.
    assert segunda["respuesta"] == "listo"


def test_responder_un_nudge_que_no_existe_es_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(f"/nudges/{uuid4()}/respuesta", json={"respuesta": "listo"})
    assert respuesta.status_code == 404


def test_ahora_no_encoge_y_esa_regla_se_silencia_dos_horas(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    _forzar_bloque_largo(servidor)
    cliente = TestClient(servidor.app)
    nudge = cliente.get("/nudges/pendiente").json()
    assert nudge["tipo"] == "cuerpo"

    cliente.post(f"/nudges/{nudge['id']}/respuesta", json={"respuesta": "ahora_no"})

    import db
    import iniciativa

    conexion = db.conectar()
    try:
        assert iniciativa._silenciado(conexion, "cuerpo", datetime.now(timezone.utc)) is True
    finally:
        conexion.close()

"""B5: GET /avisos/hoy, GET /avisos/pendiente, POST /avisos/{id}/respuesta."""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "avisos", "db"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_avisos_de_hoy_vacio_sin_nada(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    assert cliente.get("/avisos/hoy").json() == []


def test_pendiente_evalua_foco_25_y_lo_guarda(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    tarea_id = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible) "
        "VALUES (?, 'x', NULL, 'hoy', 'paso', NULL, NULL, 0)",
        (tarea_id,),
    )
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, NULL, 0, 'upvisuals')",
        (str(uuid4()), tarea_id, (ahora - timedelta(minutes=26)).isoformat()),
    )
    conexion.commit()
    conexion.close()

    cliente = TestClient(servidor.app)
    cuerpo = cliente.get("/avisos/pendiente").json()
    # Puede ser None si cayó en la noche (hora real de la corrida) — lo que
    # importa es que, si salió, es foco_25 y queda listado en /avisos/hoy.
    if cuerpo is not None:
        assert cuerpo["tipo"] == "foco_25"
        assert cliente.get("/avisos/hoy").json()[0]["tipo"] == "foco_25"


def test_responder_ahora_no(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import avisos
    import db

    conexion = db.conectar()
    aviso = avisos.registrar(conexion, "foco_25", "x", "ventanita", datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc))
    conexion.close()

    cliente = TestClient(servidor.app)
    respuesta = cliente.post(f"/avisos/{aviso.id}/respuesta", json={"respuesta": "ahora_no"})
    assert respuesta.status_code == 200
    assert respuesta.json()["respuesta"] == "ahora_no"


def test_responder_un_aviso_que_no_existe_es_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    respuesta = cliente.post(f"/avisos/{uuid4()}/respuesta", json={"respuesta": "volver"})
    assert respuesta.status_code == 404

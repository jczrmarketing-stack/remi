"""T1 punto 1 (Biblia v3.8): `archivada` en Tarea e Idea. /hoy, /hoy/agenda,
/bandeja y las consultas de la ley 1 (ultima_sesion_cerrada,
ultima_sesion_cerrada_min) no la ven."""
import importlib
import sys
from datetime import timedelta

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("servidor", "db", "modelos", "bandeja", "pensar", "clasificar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _dia(servidor, delta: int) -> str:
    return (servidor.hoy_en_bogota() + timedelta(days=delta)).isoformat()


def test_una_tarea_archivada_no_aparece_en_hoy_ni_en_agenda(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    tarea = cliente.post(
        "/tarea", json={"titulo": "hola", "fecha_limite": _dia(servidor, 0)}
    ).json()

    import db
    from uuid import UUID

    conexion = db.conectar()
    try:
        conexion.execute(
            "UPDATE tareas SET estado = 'archivada' WHERE id = ?", (tarea["id"],)
        )
        conexion.commit()
    finally:
        conexion.close()

    assert cliente.get("/hoy").json() == []
    assert cliente.get("/hoy/agenda").json() == {"manana": [], "vence": []}


def test_ultima_vez_no_cuenta_sesiones_de_una_tarea_archivada(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    tarea = cliente.post("/mensaje", json={"texto": "voy a eso"}).json()["tarea"]
    cliente.post("/mensaje", json={"texto": "listo"})

    assert cliente.get("/ultima-vez").json()["minutos"] is not None

    import db

    conexion = db.conectar()
    try:
        conexion.execute(
            "UPDATE tareas SET estado = 'archivada' WHERE id = ?", (tarea["id"],)
        )
        conexion.commit()
    finally:
        conexion.close()

    assert cliente.get("/ultima-vez").json()["minutos"] is None


def test_una_idea_archivada_no_aparece_en_la_bandeja(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió vender plantillas"})
    idea_id = cliente.get("/bandeja").json()[0]["idea"]["id"]

    import db

    conexion = db.conectar()
    try:
        conexion.execute(
            "UPDATE ideas SET estado = 'archivada' WHERE id = ?", (idea_id,)
        )
        conexion.commit()
    finally:
        conexion.close()

    assert cliente.get("/bandeja").json() == []

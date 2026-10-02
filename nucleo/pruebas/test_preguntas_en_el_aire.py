"""T3.5: la pregunta «en el aire» al abrir un bloque — el mensaje siguiente
que no sea arranque, cierre ni pregunta es la respuesta."""
import importlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

SIN_TIPO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo.
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in (
        "servidor", "db", "modelos", "libros", "preguntas", "boveda_git", "iniciativa",
        "trabajo", "bandeja", "pensar", "clasificar",
    ):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor, db


def _marcar_malik_activo(db_mod) -> None:
    conexion = db_mod.conectar()
    try:
        conexion.execute(
            "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), "commit", "/tmp/malik", "malik", "{}", datetime.now(timezone.utc).isoformat()),
        )
        conexion.commit()
    finally:
        conexion.close()


def test_abrir_un_bloque_del_proyecto_deja_la_pregunta_en_el_aire(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    assert respuesta.status_code == 200
    assert "cliente o es tuyo" in respuesta.json()["voz"]


def test_la_siguiente_frase_normal_es_la_respuesta(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    respuesta = cliente.post("/mensaje", json={"texto": "es propio"})

    assert respuesta.json()["tipo"] == "pregunta_respondida"
    assert "tipo: propio" in (tmp_path / "libros" / "malik.md").read_text()


def test_un_arranque_no_se_toma_como_respuesta(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    respuesta = cliente.post("/mensaje", json={"texto": "voy a escribir el contrato"})

    assert respuesta.json()["tipo"] == "hoy"
    assert "tipo:" not in (tmp_path / "libros" / "malik.md").read_text()

    # La pregunta sigue en el aire: una frase normal más tarde la contesta.
    siguiente = cliente.post("/mensaje", json={"texto": "es de un cliente"})
    assert siguiente.json()["tipo"] == "pregunta_respondida"
    assert "tipo: cliente" in (tmp_path / "libros" / "malik.md").read_text()

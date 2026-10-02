"""T11.1: «Gracias.» no es una idea; mientras se charla con Remi, nada
abre idea salvo «anotá esto: …» explícito."""
import importlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar", "clasificar", "trabajo"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _ideas(servidor):
    conexion = servidor.db.conectar()
    try:
        return servidor.db.listar_ideas(conexion)
    finally:
        conexion.close()


def test_gracias_no_crea_idea(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "Gracias."}).json()

    assert respuesta["tipo"] == "pregunta"
    assert _ideas(servidor) == []


def test_dos_palabras_no_crea_idea(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "muy bien"})

    assert _ideas(servidor) == []


def test_una_idea_de_verdad_sigue_creando_idea(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió armar un curso de WhatsApp para Malik"})

    ideas = _ideas(servidor)
    assert len(ideas) == 1
    assert "curso de WhatsApp" in ideas[0].texto


def test_mitad_de_una_charla_una_frase_suelta_no_crea_idea(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    conexion = servidor.db.conectar()
    servidor.db.guardar_turno(conexion, "juan", "una frase cualquiera", datetime.now(timezone.utc))
    conexion.close()
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/mensaje", json={"texto": "se me ocurrió armar un curso de WhatsApp para Malik"}
    ).json()

    assert respuesta["tipo"] == "pregunta"
    assert _ideas(servidor) == []


def test_anota_esto_explicito_crea_idea_aunque_haya_charla(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    conexion = servidor.db.conectar()
    servidor.db.guardar_turno(conexion, "juan", "una frase cualquiera", datetime.now(timezone.utc))
    conexion.close()
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "anotá esto: comprar fideos"}).json()

    assert respuesta["tipo"] == "idea"
    ideas = _ideas(servidor)
    assert len(ideas) == 1
    assert ideas[0].texto == "comprar fideos"


def test_una_charla_vieja_de_mas_de_una_hora_no_cuenta_como_vigente(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    conexion = servidor.db.conectar()
    hace_rato = datetime.now(timezone.utc) - timedelta(hours=2)
    servidor.db.guardar_turno(conexion, "juan", "una frase cualquiera", hace_rato)
    conexion.close()
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió armar un curso de WhatsApp para Malik"})

    assert len(_ideas(servidor)) == 1

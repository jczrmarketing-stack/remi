"""T8.5 · Forma de /experiencia: la puerta para cualquier mano."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("servidor", "db", "experiencia", "episodios", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


CUERPO_VALIDO = {
    "titulo": "El 401 de malik por token vencido",
    "tema": "malik",
    "resumen": "El bot devolvía 401 porque el token de WhatsApp había vencido.",
    "clase": "error",
    "donde": "organic-cash-malik/nucleo/whatsapp.py",
    "secciones": {
        "Síntoma": "El bot contestaba 401 en cada mensaje.",
        "Lo que creímos": "",
        "Causa real": "El token de acceso de WhatsApp había vencido.",
        "Cura": "Se renovó el token.",
        "Cómo verlo antes": "Revisar la fecha de expiración del token.",
    },
    "fuente": "manual",
}


def test_post_experiencia_crea_la_leccion(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/experiencia", json=CUERPO_VALIDO)

    assert respuesta.status_code == 201
    assert respuesta.json()["es_nueva"] is True
    assert (tmp_path / "boveda" / "experiencia" / respuesta.json()["archivo"]).exists()


def test_post_experiencia_incompleta_es_422(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    incompleta = {**CUERPO_VALIDO, "secciones": {**CUERPO_VALIDO["secciones"], "Cura": ""}}

    respuesta = cliente.post("/experiencia", json=incompleta)

    assert respuesta.status_code == 422


def test_get_experiencia_lista_por_tema(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/experiencia", json=CUERPO_VALIDO)

    respuesta = cliente.get("/experiencia", params={"tema": "malik"})

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["tipo"] == "leccion"


def test_get_experiencia_de_otro_tema_viene_vacio(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/experiencia", json=CUERPO_VALIDO)

    respuesta = cliente.get("/experiencia", params={"tema": "beam"})

    assert respuesta.json() == []


def test_la_misma_leccion_dos_veces_no_duplica(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/experiencia", json=CUERPO_VALIDO)

    segunda = cliente.post("/experiencia", json=CUERPO_VALIDO)

    assert segunda.json()["es_nueva"] is False
    assert len(cliente.get("/experiencia", params={"tema": "malik"}).json()) == 1

"""T8.7: «anotá esta lección: …» en la charla."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("servidor", "db", "cierre", "experiencia", "clasificar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_anota_esta_leccion_escribe_el_archivo(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import cierre

    monkeypatch.setattr(
        cierre,
        "redactar_error",
        lambda _charla, _titulo: {
            "Síntoma": "El bot contestaba 401.",
            "Lo que creímos": "",
            "Causa real": "El token había vencido.",
            "Cura": "Se renovó el token.",
            "Cómo verlo antes": "Revisar la fecha de expiración.",
        },
    )
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/mensaje",
        json={"texto": "anotá esta lección: el 401 de malik era por el token vencido"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] == "leccion"
    assert "Anotada" in respuesta.json()["texto"]
    assert list((tmp_path / "boveda" / "experiencia").glob("*.md"))


def test_sin_nada_que_sacar_no_escribe_nada(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import cierre

    monkeypatch.setattr(cierre, "redactar_error", lambda *_a: None)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "anotá esta lección: no sé qué pasó"})

    assert "No saqué nada claro" in respuesta.json()["texto"]
    carpeta = tmp_path / "boveda" / "experiencia"
    assert not carpeta.exists() or list(carpeta.glob("*.md")) == []


def test_una_frase_normal_sigue_su_camino(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "se me ocurrió una idea"})

    assert respuesta.json()["tipo"] == "idea"

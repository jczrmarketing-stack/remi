"""3e · 4: /salud, lo que mira el vigía."""
from fastapi.testclient import TestClient

import db
import servidor


def test_sano_responde_200():
    respuesta = TestClient(servidor.app).get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "db": True}


def test_si_la_base_no_abre_es_503(monkeypatch):
    def rota(*_a, **_k):
        raise OSError("disco")

    monkeypatch.setattr(db, "conectar", rota)
    respuesta = TestClient(servidor.app).get("/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"ok": False, "db": False}

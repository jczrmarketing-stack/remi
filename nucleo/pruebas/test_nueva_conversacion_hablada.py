"""«Esta es una nueva conversación» empieza una de verdad (3-oct). Antes la
frase iba al modelo, que contestaba «Borro todo, empezamos de cero» sin poder
hacerlo: la conversación seguía igual."""
import importlib
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import clasificar


@pytest.mark.parametrize(
    "frase",
    [
        "olvida las tres preguntas esta es una nueva conversacion",
        "empecemos de cero",
        "nueva conversación",
        "Empezamos de cero, porfa",
    ],
)
def test_reconoce_el_pedido(frase):
    assert clasificar.pide_conversacion_nueva(frase)


@pytest.mark.parametrize("frase", ["la conversación de ayer con Alfonso", "¿cómo empiezo el proyecto de cero?", "hola"])
def test_lo_demas_no(frase):
    assert not clasificar.pide_conversacion_nueva(frase)


def test_cierra_la_vigente_y_la_siguiente_frase_cae_en_otra(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    monkeypatch.setattr(servidor.pensar, "pensar", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no va al modelo")))
    conexion = db.conectar()
    vieja = db.guardar_turno(conexion, "juan", "lo de antes", datetime.now(timezone.utc))
    conexion.close()

    respuesta = TestClient(servidor.app).post(
        "/mensaje", json={"texto": "olvida las tres preguntas esta es una nueva conversacion", "think": True}
    ).json()

    assert respuesta["tipo"] == "conversacion_nueva"
    assert "conversación nueva" in respuesta["voz"]
    conexion = db.conectar()
    try:
        assert db.conversacion_vigente(conexion, datetime.now(timezone.utc)) is None
        assert db.guardar_turno(conexion, "juan", "hola", datetime.now(timezone.utc)) != vieja
    finally:
        conexion.close()

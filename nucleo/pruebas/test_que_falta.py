"""T8: «qué te falta para que estés al 100% listo» no se guarda como idea
— es una pregunta de estado, sin modelo, sin inventar un número."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "trabajo", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_que_te_falta_no_crea_una_idea(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/mensaje", json={"texto": "que te falta para que estes al 100% listo"}
    )

    assert respuesta.json()["tipo"] == "pregunta"
    assert cliente.get("/bandeja").json() == []


def test_que_te_falta_ya_no_contesta_con_las_preguntas_pendientes(tmp_path, monkeypatch):
    """3-oct, Juan Camilo: «eso de que tengo preguntas pendientes no nos
    interesa»: va al modelo como cualquier mensaje del chat."""
    servidor = _arrancar(tmp_path, monkeypatch)
    llamadas = []
    monkeypatch.setattr(
        servidor.pensar, "pensar",
        lambda frase, *a, **k: llamadas.append(frase) or servidor.pensar.Pensado("Bien, sigo.", 1, 1, "haiku"),
    )
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "qué te falta?", "think": True})

    assert llamadas == ["qué te falta?"]
    assert "pregunta" not in respuesta.json()["texto"].lower() or respuesta.json()["texto"] == "Bien, sigo."


def test_una_frase_sin_que_falta_sigue_normal(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "se me ocurrió una idea"})

    assert respuesta.json()["tipo"] == "idea"

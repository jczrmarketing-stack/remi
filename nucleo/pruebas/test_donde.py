"""«¿Dónde quedé?» son tres líneas del libro, sin gastar un token."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_ESTADO", "0")
    monkeypatch.setenv("REMI_CIERRE", "0")
    for nombre in ("servidor", "db", "trabajo", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _libros(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir()
    (carpeta / "malik.md").write_text(
        "---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas.\nruta: /tmp/malik\n---\n\n"
        "## Estado\n\nQuedaste: en el mosaico.\nDecisiones: Reddit espera.\n"
        "Próximo paso: abrir la ficha, cinco minutos.\n"
    )
    (carpeta / "organic-cash.md").write_text(
        "---\ntitulo: Organic Cash\ntema: organic-cash\nresumen: La clínica.\nruta: /tmp/organic\n---\n\n"
        "## Estado\n\nQuedaste: en la ficha de Sofía.\nDecisiones: ninguna nueva.\n"
        "Próximo paso: revisar el mensaje de la clínica.\n"
    )


def test_tres_lineas_sin_pensar(tmp_path, monkeypatch) -> None:
    _libros(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    import pensar

    def no() -> None:
        raise AssertionError("no tenía que pensar")

    monkeypatch.setattr(pensar, "pensar", no)
    cliente = TestClient(servidor.app)
    cliente.post("/evento", json={"tipo": "commit", "ruta": "/tmp/malik", "datos": {}})

    respuesta = cliente.post("/mensaje", json={"texto": "¿Dónde quedé?", "think": True})

    assert respuesta.status_code == 200
    assert respuesta.json()["tokens"] is None
    lineas = [l for l in respuesta.json()["texto"].splitlines() if l.strip()]
    assert lineas == [
        "Quedaste: en el mosaico.",
        "Decisiones: Reddit espera.",
        "Próximo paso: abrir la ficha, cinco minutos.",
    ]


def test_si_nombra_el_proyecto_usa_ese_libro(tmp_path, monkeypatch) -> None:
    _libros(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/evento", json={"tipo": "commit", "ruta": "/tmp/malik", "datos": {}})

    respuesta = cliente.post("/mensaje", json={"texto": "¿dónde quedé en organic cash?"})

    assert "Sofía" in respuesta.json()["texto"]
    assert "mosaico" not in respuesta.json()["texto"]


def test_sin_proyecto_una_frase_calma(tmp_path, monkeypatch) -> None:
    _libros(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "¿dónde quedé?"})

    assert respuesta.json()["texto"] == "No tengo un proyecto abierto."


def test_al_abrir_calla_si_no_hay_proyecto_y_habla_si_lo_hay(tmp_path, monkeypatch) -> None:
    _libros(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    vacio = cliente.get("/donde-quede")
    assert vacio.json() == {"lineas": []}

    cliente.post("/evento", json={"tipo": "commit", "ruta": "/tmp/malik", "datos": {}})
    abierto = cliente.get("/donde-quede")
    assert abierto.json()["lineas"][2] == "Próximo paso: abrir la ficha, cinco minutos."

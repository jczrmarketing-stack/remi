"""B3.2: un encargo que puede cerrar un hito con evidencia de código lleva
`hito: <tema>#<n>` en su primera línea — nunca lo inventa el modelo."""
import importlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

LIBRO = """---
titulo: UpVisuals
tema: upvisuals
cliente: UpVisuals
tipo: cliente
resumen: El dashboard.
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [ ] Propuesta por fases
"""


def _libro(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("servidor", "trabajo", "caminos", "libros", "db", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _tocar_libro(servidor, tema: str) -> None:
    conexion = servidor.db.conectar()
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'commit', '', ?, '{}', ?)",
        (str(uuid4()), tema, datetime.now(timezone.utc).isoformat()),
    )
    conexion.commit()
    conexion.close()


def test_encargo_lleva_el_hito_cuando_el_proximo_paso_cierra_con_codigo(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    _tocar_libro(servidor, "upvisuals")
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda *a, **k: servidor.pensar.Pensado("QUÉ\nArreglar X.", 1, 1, "sonnet"),
    )
    cliente = TestClient(servidor.app)

    cuerpo = cliente.post("/mensaje", json={"texto": "algo", "think": True, "modo": "prompt"}).json()

    assert cuerpo["texto"].startswith("hito: upvisuals#3\n\n")
    assert "QUÉ" in cuerpo["texto"]


def test_sin_libro_activo_no_lleva_encabezado(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda *a, **k: servidor.pensar.Pensado("QUÉ\nArreglar X.", 1, 1, "sonnet"),
    )
    cliente = TestClient(servidor.app)

    cuerpo = cliente.post("/mensaje", json={"texto": "algo", "think": True, "modo": "prompt"}).json()

    assert cuerpo["texto"] == "QUÉ\nArreglar X."


def test_hito_que_cierra_con_pregunta_no_lleva_encabezado(tmp_path, monkeypatch):
    """«Intake» avanza por pregunta/conversación, no por código: un
    encargo nunca puede cerrarlo, así que no lleva header."""
    libro_en_intake = LIBRO.replace(
        "- [x] Intake\n- [x] Descubrimiento (5 preguntas)\n- [ ] Propuesta por fases",
        "- [ ] Intake\n- [ ] Descubrimiento (5 preguntas)\n- [ ] Propuesta por fases",
    )
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(libro_en_intake)
    servidor = _arrancar(tmp_path, monkeypatch)
    _tocar_libro(servidor, "upvisuals")
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda *a, **k: servidor.pensar.Pensado("QUÉ\nArreglar X.", 1, 1, "sonnet"),
    )
    cliente = TestClient(servidor.app)

    cuerpo = cliente.post("/mensaje", json={"texto": "algo", "think": True, "modo": "prompt"}).json()

    assert cuerpo["texto"] == "QUÉ\nArreglar X."

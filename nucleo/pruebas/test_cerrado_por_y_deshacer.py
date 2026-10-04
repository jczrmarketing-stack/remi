"""Forma K (B3.4): GET /libros/{tema} trae cerrado_por por hito, y
POST .../deshacer lo devuelve."""
import importlib
import sys
from datetime import datetime, timezone

from fastapi.testclient import TestClient

LIBRO = """---
titulo: UpVisuals
tema: upvisuals
cliente: Alfonso
tipo: cliente
resumen: El dashboard.
---

## Camino

- [x] Intake
- [ ] Descubrimiento (5 preguntas)
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "libros", "caminos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_hito_sin_cerrado_por_registrado_es_null(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/libros/upvisuals").json()

    assert cuerpo["hitos"][0]["hecho"] is True
    assert cuerpo["hitos"][0]["cerrado_por"] is None  # hecho a mano, antes de B3


def test_hito_cerrado_por_encargo_se_ve_en_el_libro(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    db.marcar_hito_cerrado(conexion, "upvisuals", 1, "encargo", "sess-1", datetime(2026, 10, 4, 12, tzinfo=timezone.utc))
    conexion.close()
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/libros/upvisuals").json()

    assert cuerpo["hitos"][0]["cerrado_por"] == {
        "tipo": "encargo", "ref": "sess-1", "en": "2026-10-04T12:00:00Z",
    }


def test_deshacer_vuelve_el_hito_y_quita_cerrado_por(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    db.marcar_hito_cerrado(conexion, "upvisuals", 1, "encargo", "sess-1", datetime.now(timezone.utc))
    conexion.close()
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/libros/upvisuals/camino/1/deshacer")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["hitos"][0]["hecho"] is False
    assert cuerpo["hitos"][0]["cerrado_por"] is None


def test_deshacer_con_n_fuera_de_rango_es_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/libros/upvisuals/camino/99/deshacer")

    assert respuesta.status_code == 404


def test_deshacer_de_tema_que_no_existe_es_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/libros/no-existe/camino/1/deshacer")

    assert respuesta.status_code == 404

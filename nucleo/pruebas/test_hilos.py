"""B7: hilos por tema — de la revisión R6. Sin IA: el salto se detecta
con `temas.tema_de_texto`."""
import importlib
import sys

from fastapi.testclient import TestClient

LIBRO_UPVISUALS = """---
titulo: UpVisuals
tema: upvisuals
resumen: Plataforma de Alfonso.
tipo: cliente
cliente: Alfonso
claves: [upvisuals]
---

Cuerpo.
"""

LIBRO_MALIK = """---
titulo: Malik
tema: malik
resumen: Gestión de Malik.
tipo: cliente
cliente: Malik
claves: [malik]
---

Cuerpo.
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_UPVISUALS)
    (carpeta / "malik.md").write_text(LIBRO_MALIK)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "modelos", "libros", "temas", "hilos", "clasificar", "trabajo"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_el_hilo_vuelve_una_sola_vez(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió armar un buscador para upvisuals"})
    r2 = cliente.post("/mensaje", json={"texto": "se me ocurrió mandar un informe de malik"}).json()
    r3 = cliente.post("/mensaje", json={"texto": "se me ocurrió revisar los filtros de upvisuals"}).json()
    r4 = cliente.post("/mensaje", json={"texto": "se me ocurrió otra cosa de upvisuals"}).json()

    # Al llegar a Malik, nada pendiente de Malik — el hilo es de UpVisuals.
    assert "upvisuals" not in r2["texto"].lower() or "quedaste" not in r2["texto"].lower()
    # Al volver a UpVisuals, el primer turno trae el hilo.
    assert "En upvisuals, quedaste en" in r3["texto"]
    assert "buscador para upvisuals" in r3["texto"]
    # El segundo turno en UpVisuals no lo repite.
    assert "quedaste en" not in r4["texto"]


def test_sin_salto_de_tema_no_hay_hilo(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió armar un buscador para upvisuals"})
    r2 = cliente.post("/mensaje", json={"texto": "se me ocurrió otra cosa de upvisuals"}).json()

    assert "quedaste en" not in r2["texto"]


def test_un_mensaje_sin_tema_no_registra_salto(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió armar un buscador para upvisuals"})
    cliente.post("/mensaje", json={"texto": "Gracias."})  # sin tema, no debería contar como salto
    r3 = cliente.post("/mensaje", json={"texto": "se me ocurrió mandar un informe de malik"}).json()
    r4 = cliente.post("/mensaje", json={"texto": "se me ocurrió revisar los filtros de upvisuals"}).json()

    assert "quedaste en" not in r3["texto"]
    assert "En upvisuals, quedaste en" in r4["texto"]
    assert "buscador para upvisuals" in r4["texto"]

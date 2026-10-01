"""T2.2 · Forma B: `POST /cobros {tema, monto, fecha?}` → 201 Entrega
pagada, con el cliente del libro y la línea de config/plata.json."""
from fastapi.testclient import TestClient

import servidor

LIBRO_CLIENTE = """---
titulo: UpVisuals
tema: upvisuals
resumen: r
tipo: cliente
cliente: Alfonso
---

Cuerpo.
"""

LIBRO_PROPIO = """---
titulo: Remi
tema: remi
resumen: r
tipo: propio
---

Cuerpo.
"""


def _boveda(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_CLIENTE)
    (carpeta / "remi.md").write_text(LIBRO_PROPIO)


def _cliente(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    return TestClient(servidor.app)


def test_cobro_crea_entrega_pagada_con_cliente_y_linea(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.post("/cobros", json={"tema": "upvisuals", "monto": 1500})

    assert respuesta.status_code == 201
    entrega = respuesta.json()
    assert entrega["estado"] == "pagada"
    assert entrega["cliente"] == "Alfonso"
    assert entrega["monto"] == 1500
    assert entrega["linea"] == "software"


def test_cobro_con_fecha_fija(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.post(
        "/cobros", json={"tema": "upvisuals", "monto": 1000, "fecha": "2026-10-15"}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["fecha"].startswith("2026-10-15")


def test_cobro_de_tema_inexistente_es_404(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.post("/cobros", json={"tema": "no-existe", "monto": 500})

    assert respuesta.status_code == 404


def test_cobro_de_un_libro_propio_usa_el_titulo_como_cliente(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.post("/cobros", json={"tema": "remi", "monto": 200})

    assert respuesta.status_code == 201
    assert respuesta.json()["cliente"] == "Remi"
    assert respuesta.json()["linea"] is None


def test_cobro_hace_que_el_siguiente_get_libros_muestre_cobrado(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    carpeta = tmp_path / "libros"
    (carpeta / "upvisuals.md").write_text(
        LIBRO_CLIENTE.replace(
            "---\n\nCuerpo.",
            "fases:\n  - nombre: Fase 1\n    alcance: a\n    monto: 5000\n"
            "    listo_cuando:\n    estado: pagando\n---\n\nCuerpo.",
        )
    )

    cliente.post("/cobros", json={"tema": "upvisuals", "monto": 1500})

    libro = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert libro["fases"][0]["cobrado"] == 1500.0

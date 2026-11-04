"""El núcleo sirve los pedidos y sus eventos al piso Ingeniería del panel."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fabrica import agentes, expediente, rutas


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(expediente, "RAIZ", tmp_path / "pedidos")
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    app = FastAPI()
    app.include_router(rutas.router)
    return TestClient(app)


@pytest.fixture
def pedido():
    id_ = expediente.crear("Arreglar X", "remi", "main")
    for i in range(3):
        agentes.anotar_evento(id_, {"rol": "tester", "tipo": "texto", "texto": f"paso {i}"})
    return id_


def test_lista_los_pedidos(cliente, pedido):
    respuesta = cliente.get("/fabrica/pedidos")
    assert respuesta.status_code == 200
    assert [p["pedido"] for p in respuesta.json()] == [pedido]


def test_detalle_trae_expediente_tokens_y_tope(cliente, pedido):
    datos = cliente.get(f"/fabrica/pedidos/{pedido}").json()
    assert datos["meta"]["estado"] == "idea"
    assert "Arreglar X" in datos["secciones"]["Contexto"]
    assert datos["tokens"] == 0
    assert datos["tope"] == agentes.config()["tope_tokens_pedido"]


def test_pedido_que_no_existe_da_404(cliente):
    assert cliente.get("/fabrica/pedidos/no-existe").status_code == 404
    assert cliente.get("/fabrica/pedidos/no-existe/eventos").status_code == 404


def test_eventos_desde_uno(cliente, pedido):
    datos = cliente.get(f"/fabrica/pedidos/{pedido}/eventos", params={"desde": 1}).json()
    assert [e["n"] for e in datos["eventos"]] == [1, 2]
    assert datos["siguiente"] == 3


def test_eventos_desde_mas_alla_del_final(cliente, pedido):
    datos = cliente.get(f"/fabrica/pedidos/{pedido}/eventos", params={"desde": 99}).json()
    assert datos == {"eventos": [], "siguiente": 3}


def test_eventos_desde_negativo_empieza_en_cero(cliente, pedido):
    datos = cliente.get(f"/fabrica/pedidos/{pedido}/eventos", params={"desde": -3}).json()
    assert [e["n"] for e in datos["eventos"]] == [0, 1, 2]


def test_pedido_sin_eventos_todavia(cliente):
    id_ = expediente.crear("Otra", "remi", "main")
    assert cliente.get(f"/fabrica/pedidos/{id_}/eventos").json() == {"eventos": [], "siguiente": 0}


def test_id_con_barras_no_sale_de_la_carpeta(cliente, pedido):
    assert cliente.get("/fabrica/pedidos/..%2F..%2Fetc").status_code == 404

"""Mejora 4 (6-nov): cola con estados en SQLite y una corrida de noche, un pedido a la vez."""

import pytest

from fabrica import cola, expediente, linea
from test_fabrica_linea import MundoFalso


@pytest.fixture(autouse=True)
def pedidos(tmp_path, monkeypatch):
    monkeypatch.setattr(expediente, "RAIZ", tmp_path / "pedidos")


def test_el_expediente_se_refleja_en_la_cola():
    id_ = expediente.crear("Arreglar X", "remi", "main")
    assert [(f["pedido"], f["estado"]) for f in cola.listar()] == [(id_, "idea")]
    expediente.cambiar_estado(id_, "spec")
    assert cola.listar()[0]["estado"] == "spec" and cola.listar()[0]["idea"] == "Arreglar X"


def test_reflejar_nunca_tumba_al_expediente(monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", "/no/existe/remi.db")
    id_ = expediente.crear("Arreglar X", "remi", "main")
    assert expediente.leer(id_)["meta"]["estado"] == "idea"


def test_encolar_no_llama_a_ningun_agente(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.encolar("Arreglar X", "main")
    meta = expediente.leer(id_)["meta"]
    assert meta["estado"] == "idea" and meta["noche"] == 1 and falso.llamadas == []


def test_la_noche_planea_lo_encolado_y_deja_la_spec_para_juan_camilo(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.encolar("Arreglar X", "main")
    assert linea.noche(falso.mundo()) == ("planear", id_)
    assert expediente.leer(id_)["meta"]["estado"] == "spec"
    assert falso.roles() == ["planificador"]
    assert f"aprobar {id_} --de-noche" in falso.avisos[-1]


def test_aprobar_de_noche_marca_sin_construir(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert linea.aprobar_de_noche(id_) == "aprobado"
    assert expediente.leer(id_)["meta"]["noche"] == 1 and falso.roles() == ["planificador"]
    assert "Spec aprobada" in expediente.leer(id_)["secciones"]["Decisión"]


def test_la_noche_construye_primero_lo_aprobado_y_solo_un_pedido(tmp_path):
    falso = MundoFalso(tmp_path)
    aprobado = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar_de_noche(aprobado)
    idea = linea.encolar("Arreglar Y", "main")
    assert linea.noche(falso.mundo()) == ("aprobar", aprobado)
    assert expediente.leer(aprobado)["meta"]["estado"] == "pr"
    assert expediente.leer(idea)["meta"]["estado"] == "idea"          # esta noche ya no


def test_sin_nada_en_la_cola_la_noche_no_gasta(tmp_path):
    falso = MundoFalso(tmp_path)
    linea.pedir("Arreglar X", "main", falso.mundo())   # en spec, sin aprobar: no es de la noche
    antes = list(falso.llamadas)
    assert linea.noche(falso.mundo()) == ("nada", "")
    assert falso.llamadas == antes


def test_un_pedido_que_no_se_marco_de_noche_no_lo_toma_la_noche(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    expediente.cambiar_estado(id_, "aprobado")        # aprobado a mano, para correr ahora: no es de la noche
    assert linea.noche(falso.mundo()) == ("nada", "")

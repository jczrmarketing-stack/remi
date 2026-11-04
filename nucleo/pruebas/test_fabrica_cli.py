"""python3 -m fabrica pedir | aprobar | ver"""

import pytest

from fabrica import __main__ as cli
from fabrica import expediente, linea


@pytest.fixture(autouse=True)
def pedidos(tmp_path, monkeypatch):
    monkeypatch.setattr(expediente, "RAIZ", tmp_path / "pedidos")


def test_ver_sin_pedidos(capsys):
    assert cli.main(["ver"]) == 0
    assert "No hay pedidos" in capsys.readouterr().out


def test_ver_pedido_inexistente_sale_1(capsys):
    assert cli.main(["ver", "no-existe"]) == 1
    assert "No encuentro el pedido no-existe." in capsys.readouterr().err


def test_aprobar_pedido_inexistente_sale_1(capsys):
    assert cli.main(["aprobar", "no-existe"]) == 1
    assert "No encuentro el pedido no-existe." in capsys.readouterr().err


def test_pedir_imprime_el_id_y_ver_lo_lista(monkeypatch, capsys):
    monkeypatch.setattr(linea, "pedir", lambda idea, base, mundo=None: expediente.crear(idea, "remi", base))
    assert cli.main(["pedir", "Arreglar X", "--base", "fabrica/verificador"]) == 0
    salida = capsys.readouterr().out
    id_ = expediente.listar()[0]["pedido"]
    assert id_ in salida
    assert cli.main(["ver"]) == 0
    assert f"{id_} · idea · Arreglar X" in capsys.readouterr().out
    assert cli.main(["ver", id_]) == 0
    assert "## Contexto" in capsys.readouterr().out


def test_ocupada_sale_1(monkeypatch, capsys):
    def ocupada(*a, **k):
        raise linea.Ocupada("Ya hay un pedido corriendo.")
    monkeypatch.setattr(linea, "pedir", ocupada)
    assert cli.main(["pedir", "Otro"]) == 1
    assert "Ya hay un pedido corriendo." in capsys.readouterr().err


def test_responder_pasa_la_respuesta(monkeypatch, capsys):
    visto = {}
    def responder(id_, texto, mundo=None):
        visto.update(id=id_, texto=texto)
        return "spec"
    monkeypatch.setattr(linea, "responder", responder)
    assert cli.main(["responder", "20261104-1200-x", "Sí, main."]) == 0
    assert visto == {"id": "20261104-1200-x", "texto": "Sí, main."}
    assert "spec" in capsys.readouterr().out

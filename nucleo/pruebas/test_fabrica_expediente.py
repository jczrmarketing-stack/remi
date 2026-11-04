"""El expediente de un pedido de la fábrica (SOP, Bloque 1)."""

import pytest

from fabrica import expediente


def test_crear_deja_estado_idea_y_las_ocho_secciones(tmp_path):
    id_ = expediente.crear("Arreglar los tests de oficios", "remi", "main", raiz=tmp_path)
    datos = expediente.leer(id_, raiz=tmp_path)
    meta = datos["meta"]
    assert meta["pedido"] == id_
    assert meta["estado"] == "idea"
    assert meta["vueltas"] == 0
    assert meta["rama"] == f"fabrica/pedido-{id_}"
    assert meta["base"] == "main"
    assert meta["repo"] == "remi"
    assert list(datos["secciones"]) == list(expediente.SECCIONES)
    assert "Arreglar los tests de oficios" in datos["secciones"]["Contexto"]
    assert (tmp_path / id_ / "expediente.md").exists()


def test_escribir_seccion_reemplaza_solo_esa(tmp_path):
    id_ = expediente.crear("Una idea", "remi", "main", raiz=tmp_path)
    expediente.escribir_seccion(id_, "Spec", "primera", raiz=tmp_path)
    expediente.escribir_seccion(id_, "Spec", "segunda", raiz=tmp_path)
    expediente.escribir_seccion(id_, "Tests", "un test", raiz=tmp_path)
    secciones = expediente.leer(id_, raiz=tmp_path)["secciones"]
    assert secciones["Spec"] == "segunda"
    assert secciones["Tests"] == "un test"
    assert "Una idea" in secciones["Contexto"]


def test_cambiar_estado_rechaza_uno_desconocido(tmp_path):
    id_ = expediente.crear("Una idea", "remi", "main", raiz=tmp_path)
    expediente.cambiar_estado(id_, "spec", raiz=tmp_path)
    assert expediente.leer(id_, raiz=tmp_path)["meta"]["estado"] == "spec"
    with pytest.raises(ValueError):
        expediente.cambiar_estado(id_, "produccion", raiz=tmp_path)


def test_leer_un_pedido_que_no_existe_da_keyerror(tmp_path):
    with pytest.raises(KeyError):
        expediente.leer("no-existe", raiz=tmp_path)


def test_toca_y_riesgo_viajan_ida_y_vuelta(tmp_path):
    id_ = expediente.crear("Una idea", "remi", "main", raiz=tmp_path)
    expediente.cambiar(id_, raiz=tmp_path, toca=["nucleo/consumo.py", "nucleo/coding.py"], riesgo="medio", vueltas=1)
    meta = expediente.leer(id_, raiz=tmp_path)["meta"]
    assert meta["toca"] == ["nucleo/consumo.py", "nucleo/coding.py"]
    assert meta["riesgo"] == "medio"
    assert meta["vueltas"] == 1


def test_listar_trae_el_mas_nuevo_primero(tmp_path):
    a = expediente.crear("Primera", "remi", "main", raiz=tmp_path)
    b = expediente.crear("Segunda", "remi", "main", raiz=tmp_path)
    ids = [m["pedido"] for m in expediente.listar(raiz=tmp_path)]
    assert set(ids) == {a, b}
    assert ids[0] == b


def test_dos_pedidos_iguales_el_mismo_minuto_no_chocan(tmp_path):
    a = expediente.crear("Misma idea", "remi", "main", raiz=tmp_path)
    b = expediente.crear("Misma idea", "remi", "main", raiz=tmp_path)
    assert a != b

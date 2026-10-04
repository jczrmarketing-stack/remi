"""B6.1: gastos.parsear — sin IA, nunca adivina de quién es un gasto."""
import sys


def _gastos(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(
        "---\ntitulo: UpVisuals\ntema: upvisuals\ncliente: Alfonso\ntipo: cliente\nresumen: x.\n---\n"
    )
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    sys.modules.pop("gastos", None)
    sys.modules.pop("temas", None)
    sys.modules.pop("libros", None)
    import gastos

    return gastos


def test_gasto_con_proyecto_reconocido(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("gasté 40 en el servidor de upvisuals")
    assert parseado is not None
    assert parseado.monto == 40.0
    assert parseado.tema == "upvisuals"
    assert parseado.claro is True


def test_gasto_comun_por_palabra_clave_sin_proyecto(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("pagué 20 del dominio")
    assert parseado is not None
    assert parseado.monto == 20.0
    assert parseado.tema is None
    assert parseado.claro is True
    assert parseado.concepto == "dominio"


def test_gasto_comun_con_dos_puntos_sin_verbo(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("la membresía de Claude: 100 al mes")
    assert parseado is not None
    assert parseado.monto == 100.0
    assert parseado.tema is None
    assert parseado.claro is True
    assert parseado.concepto == "la membresía de Claude"


def test_gasto_sin_proyecto_ni_comun_claro_queda_dudoso(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("gasté 15 en el almuerzo")
    assert parseado is not None
    assert parseado.claro is False
    assert parseado.tema is None


def test_alguien_pagandome_no_es_un_gasto(tmp_path, monkeypatch):
    """«pagó»/«pagaron» es alguien pagándoME — eso es un cobro
    (cobros.py), nunca un gasto, aunque no se reconozca el cliente."""
    gastos = _gastos(tmp_path, monkeypatch)
    assert gastos.parsear("Alfonso pagó 1500") is None
    assert gastos.parsear("me pagaron 1500") is None


def test_sin_verbo_ni_dos_puntos_no_es_un_gasto(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    assert gastos.parsear("el servidor cuesta 40 al mes") is None


def test_sin_monto_no_es_un_gasto(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    assert gastos.parsear("gasté en el servidor de upvisuals") is None

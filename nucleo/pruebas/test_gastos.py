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


# Hallazgo de revisión (grave, B6): "algo: número" sin palabra de gasto
# recurrente se leía como un gasto, sin preguntar nunca.
def test_dos_puntos_sin_palabra_de_gasto_no_es_un_gasto(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    assert gastos.parsear("llamo a Alfonso a las 10:30") is None
    assert gastos.parsear("Reunión: 3 pm con el equipo") is None
    assert gastos.parsear("UpVisuals: 3 bugs pendientes") is None


# Hallazgo de revisión (medio, B6): un punto decimal se leía como miles.
def test_monto_con_un_punto_y_dos_decimales_es_decimal(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("pagué 40.50 del dominio")
    assert parseado is not None
    assert parseado.monto == 40.50


def test_monto_con_puntos_de_miles_sigue_funcionando(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("pagué 1.500 del dominio")
    assert parseado is not None
    assert parseado.monto == 1500.0


# Hallazgo de revisión (medio, B6): el número de una fecha hablada se leía
# como el monto.
def test_fecha_hablada_no_se_confunde_con_el_monto(tmp_path, monkeypatch):
    gastos = _gastos(tmp_path, monkeypatch)
    parseado = gastos.parsear("pagué el 15 de octubre 40 del dominio")
    assert parseado is not None
    assert parseado.monto == 40.0

"""B1 (docs/PLAN-FINAL.md): tope de gasto en los motores pagados. Sin IA:
todo acá es código puro con un reloj y una base de prueba, nunca la real."""
import json
import sys
from datetime import datetime, timezone

import pytest

import gasto


def _config(tmp_path, monkeypatch, tope_dia=5.0, tope_mes=50.0, activo=True):
    ruta = tmp_path / "gasto.json"
    ruta.write_text(json.dumps({"tope_dia_usd": tope_dia, "tope_mes_usd": tope_mes, "activo": activo}))
    monkeypatch.setenv("REMI_GASTO", str(ruta))
    return ruta


def _motores(tmp_path, monkeypatch, precios):
    ruta = tmp_path / "motores.json"
    ruta.write_text(json.dumps({"precios": precios}))
    monkeypatch.setenv("REMI_MOTORES", str(ruta))
    return ruta


def _arrancar_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sys.modules.pop("db", None)
    sys.modules.pop("gasto", None)
    import gasto as _gasto

    return _gasto


def test_sin_config_usa_los_valores_por_defecto(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_GASTO", str(tmp_path / "no-existe.json"))
    config = gasto.leer_config()
    assert config.tope_dia_usd == gasto.CONFIG_POR_DEFECTO.tope_dia_usd
    assert config.activo is True


def test_calcular_usd_sin_precio_es_cero_nunca_inventa(tmp_path, monkeypatch):
    _motores(tmp_path, monkeypatch, precios={})
    assert gasto.calcular_usd("venice", "un-modelo-sin-precio", 1000, 1000) == 0.0


def test_calcular_usd_con_precio(tmp_path, monkeypatch):
    _motores(
        tmp_path,
        monkeypatch,
        precios={"venice": {"modelo-x": {"usd_1k_entrada": 0.01, "usd_1k_salida": 0.02}}},
    )
    usd = gasto.calcular_usd("venice", "modelo-x", 2000, 1000)
    assert usd == pytest.approx(0.02 + 0.02)


def test_registrar_y_sumar_del_dia(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch)
    hoy = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=0.03, ahora=hoy)
    modulo.registrar("openrouter", "modelo-y", 500, 500, usd=0.01, ahora=hoy)
    assert modulo.gasto_dia_usd(hoy.date()) == pytest.approx(0.04)


def test_gasto_de_ayer_no_cuenta_en_el_dia_de_hoy(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch)
    ayer = datetime(2026, 10, 3, 23, tzinfo=timezone.utc)
    hoy = datetime(2026, 10, 4, 1, tzinfo=timezone.utc)
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=0.09, ahora=ayer)
    assert modulo.gasto_dia_usd(hoy.date()) == 0.0
    assert modulo.gasto_mes_usd(hoy.date()) == pytest.approx(0.09)


def test_gasto_del_mes_pasado_no_cuenta_en_el_mes_de_hoy(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch)
    mes_pasado = datetime(2026, 9, 30, 23, tzinfo=timezone.utc)
    hoy = datetime(2026, 10, 4, 1, tzinfo=timezone.utc)
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=0.5, ahora=mes_pasado)
    assert modulo.gasto_mes_usd(hoy.date()) == 0.0


def test_excede_tope_del_dia(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, tope_dia=0.01, tope_mes=50.0)
    hoy = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    assert modulo.excede_tope(hoy.date()) is False
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=0.02, ahora=hoy)
    assert modulo.excede_tope(hoy.date()) is True


def test_excede_tope_del_mes(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, tope_dia=100.0, tope_mes=0.01)
    hoy = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    modulo.registrar("openrouter", "modelo-y", 1000, 1000, usd=0.02, ahora=hoy)
    assert modulo.excede_tope(hoy.date()) is True


def test_tope_apagado_nunca_excede(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, tope_dia=0.0, tope_mes=0.0, activo=False)
    hoy = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=5.0, ahora=hoy)
    assert modulo.excede_tope(hoy.date()) is False


def test_fraccion_usada_para_el_aviso_del_80_por_ciento(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, tope_dia=10.0, tope_mes=100.0)
    hoy = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=8.5, ahora=hoy)
    assert modulo.fraccion_usada(hoy.date()) == pytest.approx(0.85)


def test_fraccion_usada_con_tope_apagado_es_cero(tmp_path, monkeypatch):
    modulo = _arrancar_db(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, activo=False)
    hoy = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    modulo.registrar("venice", "modelo-x", 1000, 1000, usd=5.0, ahora=hoy)
    assert modulo.fraccion_usada(hoy.date()) == 0.0


def test_escribir_config_y_releer(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch)
    nueva = gasto.ConfigGasto(tope_dia_usd=1.5, tope_mes_usd=20.0, activo=False)
    gasto.escribir_config(nueva)
    assert gasto.leer_config() == nueva

"""suite.py pasa mypy y sigue devolviendo lo mismo."""
from __future__ import annotations

from datetime import date

import suite

FIJAS = dict(hoy=date(2026, 11, 6), ficha={"pisos": {"inteligencia": {"paso": {"titulo": "Ficha", "contexto": "", "accion": "x"}}}},
             boveda={"leyendo": False, "agenda": {}}, agentes={}, cobros=[], pisos_publicados={}, cajones={}, norte={}, fabrica={})


def _inteligencia(temas):
    return next(p for p in suite.armar(temas=temas, **FIJAS)["pisos"] if p["id"] == "inteligencia")


def test_temas_con_datos_llenan_el_piso():
    p = _inteligencia(([{"tema": "X", "accion": "hoy", "para_ti": "Y"}], "2026-11-06"))
    assert p["paso"]["titulo"] == "X" and p["paso"]["contexto"] == "Para ti: Y"
    assert next(e for e in p["entra"] if e["titulo"] == "Temas del Editor")["fuente"] == "de hoy"


def test_temas_de_otro_dia_dicen_su_fecha():
    p = _inteligencia(([{"tema": "X", "accion": "hoy", "para_ti": "Y"}], "2026-11-05"))
    assert next(e for e in p["entra"] if e["titulo"] == "Temas del Editor")["fuente"] == "del 2026-11-05"


def test_temas_vacios_mantienen_el_paso_de_la_ficha():
    p = _inteligencia(([], ""))
    assert p["paso"]["titulo"] == "Ficha"
    t = next(e for e in p["entra"] if e["titulo"] == "Temas del Editor")
    assert t["filas"] == [] and t["vacio"] == "El Editor publica a las 11:00."


def test_boveda_sin_raiz_devuelve_el_dict_exacto(monkeypatch):
    monkeypatch.setattr(suite.donde_boveda, "ubicar", lambda *a, **k: None)
    esperado = {"leyendo": False, "calificados": None, "leidos_hoy": None, "agenda": {}, "enfriando_hasta": None}
    assert suite.boveda_en_vivo(raiz=None) == esperado

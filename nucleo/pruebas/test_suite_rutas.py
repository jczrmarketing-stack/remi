"""Suite: mandar ideas entre pisos (cajón) y el Norte guiado. La mente siempre en tmp_path."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import suite
import suite_rutas


@pytest.fixture
def mente(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_MENTE", str(tmp_path))
    monkeypatch.setattr(suite, "MENTE", tmp_path)
    return tmp_path


@pytest.fixture
def cliente(mente):
    app = FastAPI()
    app.include_router(suite_rutas.router)
    return TestClient(app)


def _armar(**k):
    base = dict(hoy=date(2026, 11, 4), ficha={"pisos": {"oferta": {"entra": [
        {"titulo": "Ideas guardadas", "fuente": "desde Inteligencia", "filas": [], "vacio": "Ninguna todavía."},
        {"titulo": "Prueba real", "fuente": "", "filas": [["UpVisuals", "US$3.000"]]}]},
        "direccion": {"paso": {"titulo": "Escribir el Norte de INV3RZA.", "contexto": "Misión.", "accion": "Empezar con Remi"}}}},
        boveda={"leyendo": False, "agenda": {}}, temas=([], ""), agentes={}, cobros=[], pisos_publicados={})
    base.update(k)
    return {p["id"]: p for p in suite.armar(**base)["pisos"]}


def test_guardar_crea_el_cajon_y_agrega_lineas(cliente, mente):
    r = cliente.post("/suite/guardar", json={"piso": "marketing", "texto": "Wispr Flow · 50 creadores", "fuente": "Inteligencia"})
    assert r.status_code == 200 and r.json()["nombre"] == "Marketing"
    cliente.post("/suite/guardar", json={"piso": "marketing", "texto": "Segunda\nidea", "fuente": "Inteligencia"})
    texto = (mente / "negocio" / "cajon" / "marketing.md").read_text(encoding="utf-8")
    assert texto.startswith("---\ntipo: cajon\npiso: marketing\n")
    lineas = [l for l in texto.splitlines() if l.startswith("- ")]
    assert lineas[0].endswith(" · Wispr Flow, 50 creadores (desde Inteligencia)")
    assert lineas[1].endswith(" · Segunda idea (desde Inteligencia)")


def test_guardar_valida_el_piso_y_el_texto(cliente, mente):
    assert cliente.post("/suite/guardar", json={"piso": "cocina", "texto": "x"}).status_code == 422
    assert cliente.post("/suite/guardar", json={"piso": "ventas", "texto": "   "}).status_code == 422
    assert not (mente / "negocio" / "cajon" / "cocina.md").exists()


def test_cajon_las_cinco_mas_nuevas_primero(mente):
    for i in range(7):
        suite_rutas.guardar_en_cajon("oferta", f"Idea {i}", "Inteligencia", hoy=date(2026, 11, 4))
    filas = suite_rutas.leer_cajon("oferta")
    assert [f[0] for f in filas] == ["Idea 6", "Idea 5", "Idea 4", "Idea 3", "Idea 2"]
    assert filas[0][1] == "4 nov, desde Inteligencia"


def test_ideas_guardadas_en_la_suite(mente):
    suite_rutas.guardar_en_cajon("oferta", "Precio por proyecto", "Inteligencia", hoy=date(2026, 11, 4))
    suite_rutas.guardar_en_cajon("ventas", "Seguir a Alfonso", "Inteligencia", hoy=date(2026, 11, 4))
    pisos = _armar(norte={})
    assert [e["titulo"] for e in pisos["oferta"]["entra"]] == ["Ideas guardadas", "Prueba real"]
    assert pisos["oferta"]["entra"][0]["filas"] == [["Precio por proyecto", "4 nov, desde Inteligencia"]]
    assert pisos["ventas"]["entra"][-1]["titulo"] == "Ideas guardadas"
    assert all(e["titulo"] != "Ideas guardadas" for e in pisos["marketing"]["entra"])


def test_cajon_vacio_deja_el_mensaje_de_la_ficha(mente):
    lista = _armar(norte={})["oferta"]["entra"][0]
    assert lista["filas"] == [] and lista["vacio"] == "Ninguna todavía."


def test_norte_se_guarda_y_se_retoma(cliente, mente):
    r = cliente.get("/suite/norte").json()
    assert r["existe"] is False and r["siguiente"] == 1 and len(r["preguntas"]) == 6
    r = cliente.post("/suite/norte", json={"n": 1, "respuesta": "A dueños de negocios pequeños"}).json()
    assert r["siguiente"] == 2 and r["completo"] is False
    texto = (mente / "negocio" / "norte.md").read_text(encoding="utf-8")
    assert "tipo: negocio" in texto and "estatus: borrador" in texto and "## 1. ¿A quién le sirves?" in texto
    r = cliente.get("/suite/norte").json()
    assert r["preguntas"][0]["respuesta"] == "A dueños de negocios pequeños" and r["siguiente"] == 2


def test_norte_completo_queda_confirmado(cliente, mente):
    for n in range(1, 7):
        r = cliente.post("/suite/norte", json={"n": n, "respuesta": f"Respuesta {n}\n\ncon dos párrafos"}).json()
    assert r["completo"] is True and r["siguiente"] is None
    assert "estatus: confirmado" in (mente / "negocio" / "norte.md").read_text(encoding="utf-8")
    assert r["preguntas"][5]["respuesta"] == "Respuesta 6\n\ncon dos párrafos"


def test_norte_valida(cliente):
    assert cliente.post("/suite/norte", json={"n": 7, "respuesta": "x"}).status_code == 422
    assert cliente.post("/suite/norte", json={"n": 1, "respuesta": "  "}).status_code == 422


def test_direccion_sin_norte_lleva_al_flujo(mente):
    d = _armar()["direccion"]
    assert d["paso"]["ruta"] == "/d/direccion/norte" and d["paso"]["accion"] == "Empezar con Remi"
    assert all(e["titulo"] != "Tu Norte" for e in d["entra"])


def test_direccion_con_norte_a_medias_y_completo(mente):
    suite_rutas.guardar_norte(1, "A dueños de negocios pequeños")
    d = _armar()["direccion"]
    assert d["paso"]["ruta"] == "/d/direccion/norte" and "pregunta 2 de 6" in d["paso"]["contexto"]
    assert d["entra"][0]["titulo"] == "Tu Norte" and d["entra"][0]["filas"] == [["A dueños de negocios pequeños", "A quién"]]
    for n in range(2, 7):
        suite_rutas.guardar_norte(n, "x " * 80)
    d = _armar()["direccion"]
    assert d["paso"]["accion"] == "Revisar el Norte con Remi" and "ruta" not in d["paso"]
    assert len(d["entra"][0]["filas"]) == 6 and d["entra"][0]["filas"][1][0].endswith("…")

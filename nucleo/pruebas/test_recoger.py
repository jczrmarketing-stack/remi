from datetime import datetime
from pathlib import Path

import pytest

import recoger as r


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    boveda = tmp_path / "boveda"
    boveda.mkdir()
    monkeypatch.setenv("REMI_BOVEDA", str(boveda))
    lanzados = []
    avisos = []
    return boveda, lanzados, avisos


def _m(texto, entorno, chat=1):
    boveda, lanzados, avisos = entorno
    return r.manejar(chat, texto, avisos.append, lanzar=lambda b, a, av: lanzados.append((b, a)), ahora=datetime(2026, 10, 29, 19, 30, 0))


def test_charla_normal_pasa_de_largo(entorno):
    assert _m("hola, ¿cómo vamos?", entorno) is None
    assert _m("https://a.com/x", entorno) is None  # sin /info no recoge
    assert "Manda /info" in _m("/listo", entorno)


def test_flujo_completo(entorno):
    boveda, lanzados, _ = entorno
    assert "Abierto" in _m("/info", entorno)
    assert "+2 · 2 en total" in _m("mira https://youtu.be/abc12345678 y https://tiktok.com/@a/video/1", entorno)
    assert "+1 · 3 en total" in _m("https://blog.com/post, https://youtu.be/abc12345678", entorno)
    assert "No vi links" in _m("ok ya", entorno)
    assert "Van 3" in _m("/estado", entorno)
    assert "3 link(s) en la bóveda" in _m("/listo", entorno)
    archivo = lanzados[0][1]
    assert archivo == boveda / "00_inbox" / "_telegram" / "lote-20261029-193000.txt"
    assert archivo.read_text().splitlines() == ["https://youtu.be/abc12345678", "https://tiktok.com/@a/video/1", "https://blog.com/post"]
    assert _m("hola", entorno) is None  # ya cerró: vuelve la charla normal


def test_info_con_links_en_el_mismo_mensaje_y_reabrir(entorno):
    assert "1 link" in _m("/info https://a.com/1", entorno)
    assert "Ya está abierto: 1" in _m("/info", entorno)


def test_cancelar_y_vacio(entorno):
    _m("/info", entorno)
    assert "Todavía no hay links" in _m("/listo", entorno)
    _m("https://a.com/1", entorno)
    assert "descarté 1" in _m("/cancelar", entorno)
    assert "No había nada" in _m("/cancelar", entorno)


def test_el_estado_sobrevive_a_un_reinicio_y_es_por_chat(entorno):
    _m("/info", entorno)
    _m("https://a.com/1", entorno)
    assert "Van 1" in _m("/estado", entorno)          # relee del archivo
    assert "No hay nada abierto" in _m("/estado", entorno, chat=2)


def test_sin_boveda_conserva_los_links(entorno, monkeypatch):
    monkeypatch.setenv("REMI_BOVEDA", "/no/existe")
    monkeypatch.setattr(r, "_boveda", lambda: None)
    _m("/info https://a.com/1", entorno)
    assert "No encuentro la bóveda" in _m("/listo", entorno)
    assert "Van 1" in _m("/estado", entorno)


def test_comando_con_arroba_del_bot(entorno):
    assert "Abierto" in _m("/info@remi_bot", entorno)


def test_resumen_corto():
    md = "# Último lote\n\n8 entraron, 2 fallaron.\n\n## Fallaron\n- https://a.com — 404\n- https://b.com — 429\n\n## Entraron\n- x → y\n"
    t = r.resumen_corto(md)
    assert "8 entraron, 2 fallaron" in t and "• https://a.com — 404" in t
    assert r.resumen_corto("8 entraron, 0 fallaron.\n").startswith("✔ 8 entraron")

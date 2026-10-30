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
    assert "Anotado" in _m("https://a.com/x", entorno)  # un link solo entra aunque no haya /info
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


# — Compartir desde el celular: links sueltos entran solos —

class _Temp:
    def __init__(self):
        self.cancelado = False

    def cancel(self):
        self.cancelado = True


_PENDIENTES: list = []


def _auto(texto, entorno, chat=1):
    boveda, lanzados, avisos = entorno
    r._TEMPORIZADORES.clear()
    pendientes = _PENDIENTES
    return r.manejar(chat, texto, avisos.append, lanzar=lambda b, a, av: lanzados.append((b, a)),
                     ahora=datetime(2026, 10, 29, 20, 0, 0), programar=lambda s, f: (pendientes.append(f), _Temp())[1], espera=45)




def test_link_suelto_de_youtube_o_instagram_entra_solo(entorno):
    boveda, lanzados, avisos = entorno
    _PENDIENTES.clear()
    assert "Anotado" in _auto("https://www.instagram.com/reel/Xy12/", entorno)
    assert not lanzados                      # espera la calma
    _PENDIENTES[-1]()                         # pasan los 45 s
    assert [p.name for p in [lanzados[0][1]]] == ["auto-20261029-200000.txt"]
    assert lanzados[0][1].read_text().strip() == "https://www.instagram.com/reel/Xy12/"
    assert any("Leyendo 1 link" in a for a in avisos)


def test_varios_seguidos_se_juntan_en_un_solo_lote(entorno):
    boveda, lanzados, _ = entorno
    _PENDIENTES.clear()
    r._TEMPORIZADORES.clear()
    kw = dict(lanzar=lambda b, a, av: lanzados.append((b, a)), ahora=datetime(2026, 10, 29, 20, 0, 0), espera=45)
    temps = []
    prog = lambda s, f: (_PENDIENTES.append(f), temps.append(_Temp()), temps[-1])[-1]
    for u in ("https://youtu.be/abc12345678", "https://www.tiktok.com/@a/video/1", "https://youtu.be/abc12345678"):
        r.manejar(1, u, lambda t: None, programar=prog, **kw)
    assert temps[0].cancelado and temps[1].cancelado and not temps[2].cancelado  # cada link reinicia la espera
    _PENDIENTES[-1]()
    _PENDIENTES[0]()                           # un temporizador viejo no duplica nada
    assert len(lanzados) == 1 and lanzados[0][1].read_text().splitlines() == ["https://youtu.be/abc12345678", "https://www.tiktok.com/@a/video/1"]


def test_cualquier_link_suelto_entra_pero_una_frase_no(entorno):
    _PENDIENTES.clear()
    assert "Anotado" in _auto("https://miblog.com/post", entorno)            # blogs y repos también
    assert "Anotado" in _auto("https://github.com/adbar/trafilatura", entorno)
    assert _m("oye mira este video que me mandó un cliente sobre precios https://youtu.be/abc12345678", entorno) is None
    assert _m("https://t.me/algunbot", entorno) is None                        # links de chat no son contenido


def test_pendientes_se_retoman_al_arrancar(entorno):
    boveda, lanzados, avisos = entorno
    _PENDIENTES.clear()
    _auto("https://youtu.be/abc12345678", entorno, chat=7)   # queda guardado, el temporizador "se pierde"
    _PENDIENTES.clear()
    prog = []
    assert r.reanudar(lambda c, t: avisos.append((c, t)), programar=lambda s, f: prog.append(f), lanzar=lambda b, a, av: lanzados.append((b, a))) == 1
    prog[0]()
    assert lanzados and "https://youtu.be/abc12345678" in lanzados[-1][1].read_text()

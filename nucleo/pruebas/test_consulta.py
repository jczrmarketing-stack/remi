"""B4: preguntar (MCP) y /p (Telegram) comparten una sola búsqueda; videos sin leer; leer_video."""
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import catalogo_puente as cp
import consulta
import telegram


def _h(i="mundo/fuentes/web/vieja.md", titulo="Precios de Supabase", resumen="El plan Pro cuesta $25 por mes"):
    return SimpleNamespace(id=i, tipo="fuente", titulo=titulo, resumen=resumen, fecha="2026-09-20", estatus="sin_verificar", confianza="oro")


def _falsos(monkeypatch, hallazgos, estado="", videos=""):
    registradas = []
    monkeypatch.setattr(consulta.indexar, "conectar", lambda: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(consulta.indexar, "actualizar", lambda *a, **k: {})
    monkeypatch.setattr(consulta.indexar, "buscar", lambda *a, **k: hallazgos)
    monkeypatch.setattr(consulta.metricas, "registrar_consulta", lambda origen, sesion, q, ids, n: registradas.append((origen, q, ids)))
    monkeypatch.setattr(consulta.afirmaciones_puente, "estado_de", lambda nota, mente=None: estado)
    monkeypatch.setattr(consulta.catalogo_puente, "aviso", lambda q, ruta=None: videos)
    return registradas


def test_la_ficha_trae_la_caducidad_si_la_hay_y_queda_igual_si_no(monkeypatch):
    _falsos(monkeypatch, [_h()], estado="afirmaciones: 1 caducada (venció 2026-10-20)")
    assert "Precios de Supabase" in consulta.responder("plan Pro Supabase precio") and "afirmaciones: 1 caducada (venció 2026-10-20)" in consulta.responder("plan Pro Supabase precio")
    _falsos(monkeypatch, [_h()], estado="")
    assert "afirmaciones:" not in consulta.responder("plan Pro Supabase precio")


def test_sugiere_videos_sin_leer_al_final(monkeypatch):
    _falsos(monkeypatch, [_h()], videos="Videos sin leer sobre esto (pídelos con `leer_video`):\n- «Tokens» (c1) · id aaaaaaaaaaa")
    r = consulta.responder("plan Pro Supabase precio")
    assert r.rstrip().endswith("id aaaaaaaaaaa") and "Precios de Supabase" in r
    _falsos(monkeypatch, [], videos="Videos sin leer sobre esto (pídelos con `leer_video`):\n- «T» (c) · id bbbbbbbbbbb")
    assert consulta.responder("zzz yyy").startswith("Videos sin leer")     # aunque la mente no tenga nada, el video se ofrece


def test_sin_nada_lo_dice(monkeypatch):
    _falsos(monkeypatch, [])
    assert consulta.responder("tema inexistente") == "No hay nada sobre «tema inexistente» en la mente."


def test_slash_p_de_telegram_responde_corto_y_registra_el_origen(monkeypatch):
    reg = _falsos(monkeypatch, [_h(f"n{i}.md", f"Supabase precio {i}", "plan Pro precio") for i in range(6)])
    r = consulta.manejar_comando("/p plan Pro Supabase precio")
    assert r.count("[n") == 3                                              # máximo 3 en el teléfono
    assert reg[-1][0] == "telegram"
    assert consulta.manejar_comando("/P@remi_bot plan precio") is not None
    assert consulta.manejar_comando("hola, cómo vas") is None and consulta.manejar_comando("/pagar") is None
    assert "Escribe la pregunta" in consulta.manejar_comando("/p")


def test_slash_p_recorta_lo_largo_y_nunca_levanta(monkeypatch):
    _falsos(monkeypatch, [_h(f"n{i}.md", "T", "x" * 400) for i in range(3)])
    monkeypatch.setattr(consulta, "responder", lambda *a, **k: "linea\n" * 2000)
    r = consulta.manejar_comando("/p algo")
    assert len(r) <= consulta.MAXIMO_TELEGRAM + 20 and r.endswith("(recortado)")
    monkeypatch.setattr(consulta, "responder", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("índice roto")))
    assert "No pude buscar" in consulta.manejar_comando("/p algo")


def test_el_bot_contesta_slash_p_sin_pasar_por_la_charla(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(consulta, "responder", lambda q, origen="mcp", maximo=None: f"respuesta a {q}")
    monkeypatch.setattr(telegram, "_procesar_texto", lambda t: (_ for _ in ()).throw(AssertionError("no debía llegar a la charla")))
    enviados = []
    transporte = SimpleNamespace(enviar_mensaje=lambda c, t: enviados.append((c, t)))
    telegram._manejar_actualizacion(transporte, {"update_id": 1, "message": {"chat": {"id": 123}, "text": "/p cómo ahorrar tokens"}})
    assert enviados == [(123, "respuesta a cómo ahorrar tokens")]


def _catalogo(tmp: Path) -> Path:
    ruta = tmp / "c.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE videos (id TEXT PRIMARY KEY, canal TEXT, titulo TEXT, puntaje REAL, relevancia INTEGER, estado TEXT)")
    con.executemany("INSERT INTO videos VALUES (?,?,?,?,?,?)", [
        ("aaaaaaaaaaa", "c1", "Cómo ahorrar tokens en Claude Code con hooks", 5.0, 3, "pendiente"),
        ("bbbbbbbbbbb", "c1", "Recetas de cocina italiana clásicas", 9.0, 3, "pendiente"),
        ("ccccccccccc", "c2", "Tokens y contexto en Claude Code explicado", 2.0, None, "pendiente"),
        ("ddddddddddd", "c2", "Claude Code tokens ya leído", 9.0, 3, "ingerido"),
        ("eeeeeeeeeee", "c2", "Claude Code tokens ruido", 9.0, 1, "pendiente")])
    con.commit(); con.close()
    return ruta


def test_sugeridos_solo_pendientes_utiles_que_hablan_de_lo_preguntado(tmp_path):
    ruta = _catalogo(tmp_path)
    s = cp.sugeridos("cómo ahorrar tokens con Claude Code", ruta=ruta)
    assert [v["id"] for v in s] == ["aaaaaaaaaaa", "ccccccccccc"]
    assert cp.sugeridos("paella valenciana", ruta=ruta) == [] and cp.sugeridos("", ruta=ruta) == []
    assert cp.sugeridos("tokens", ruta=tmp_path / "no-existe.db") == []
    assert "id aaaaaaaaaaa" in cp.aviso("ahorrar tokens Claude Code", ruta=ruta)


def test_leer_video_valida_el_id_antes_de_correr_nada(tmp_path):
    llamadas = []
    for malo in ("; rm -rf /", "../../x", "corto", "x" * 40, ""):
        assert "no es válido" in cp.leer_video(malo, correr=lambda *a, **k: llamadas.append(a), raiz=tmp_path)
    assert llamadas == []


def test_leer_video_corre_en_el_entorno_de_la_boveda_y_devuelve_la_ultima_linea(tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True); (tmp_path / ".venv" / "bin" / "python").write_text("")
    visto = {}
    def correr(cmd, **k):
        visto["cmd"], visto["cwd"] = cmd, k["cwd"]
        return SimpleNamespace(stdout="algo de ruido\nleído: nota para el video", stderr="")
    r = cp.leer_video("aaaaaaaaaaa", correr=correr, raiz=tmp_path)
    assert visto["cmd"][-3:] == ["youtube_catalogo.py", "--leer", "aaaaaaaaaaa"] and visto["cwd"] == tmp_path
    assert r.startswith("leído: nota para el video")
    sin = cp.leer_video("aaaaaaaaaaa", correr=correr, raiz=tmp_path / "no")
    assert "no está montada" in sin
    def lento(cmd, **k): raise subprocess.TimeoutExpired(cmd, 170)
    assert "tiempo" in cp.leer_video("aaaaaaaaaaa", correr=lento, raiz=tmp_path)


def test_el_servidor_mcp_expone_leer_video_y_contradice():
    try:
        import remi_mcp
    except ModuleNotFoundError:
        return
    assert callable(remi_mcp.leer_video) and callable(remi_mcp.contradice) and callable(remi_mcp.preguntar)

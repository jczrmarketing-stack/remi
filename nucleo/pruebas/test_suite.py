"""INV3RZA Suite: /suite arma los pisos con datos reales y nunca inventa."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import agentes_estado
import suite

FICHA = {"norte": {"actual": 3000, "escalon": 5000, "meta": 20000},
         "foco": {"titulo": "Entregar la Fase 1", "contexto": "Hoy solo esto"},
         "pisos": {"ventas": {"paso": {"titulo": "Cobrar", "contexto": "", "accion": "Preparar"},
                              "entra": [{"titulo": "Cobros", "fuente": "ficha", "filas": [["UpVisuals", "US$2.000"]]}]}}}
AGENTES = {"remi": {"id": "remi", "piso": None, "estado": "trabajando"},
           "editor": {"id": "editor", "piso": "inteligencia", "estado": "durmiendo"},
           "programador": {"id": "programador", "piso": "ingenieria", "estado": "trabajando"}}


def _armar(**k):
    base = dict(hoy=date(2026, 11, 3), ficha=FICHA, boveda={"leyendo": False, "agenda": {}}, temas=([], ""), agentes=AGENTES, cobros=[], pisos_publicados={}, cajones={}, norte={}, fabrica={})
    base.update(k)
    return suite.armar(**base)


def test_siete_pisos_en_orden_y_foco_de_la_ficha():
    r = _armar()
    assert [p["id"] for p in r["pisos"]] == ["direccion", "inteligencia", "oferta", "marketing", "ventas", "ingenieria", "administracion"]
    assert r["foco"]["titulo"] == "Entregar la Fase 1"
    assert r["norte"]["escalon"] == 5000


def test_la_tarea_de_hoy_manda_sobre_la_ficha():
    r = _armar(foco_de_hoy={"titulo": "Tarea real", "contexto": ""})
    assert r["foco"]["titulo"] == "Tarea real"


def test_luz_solo_donde_hay_trabajo():
    luz = {p["id"]: p["luz"] for p in _armar()["pisos"]}
    assert luz["ingenieria"] is True and luz["inteligencia"] is False and luz["ventas"] is False
    luz = {p["id"]: p["luz"] for p in _armar(boveda={"leyendo": True, "agenda": {}})["pisos"]}
    assert luz["inteligencia"] is True


def test_temas_del_editor_llenan_inteligencia():
    temas = [{"titular": "Wispr Flow", "para_ti": "copiable", "accion": "hoy"}, {"titular": "OpenAI", "accion": "solo saber"}]
    p = next(p for p in _armar(temas=(temas, "2026-11-03"))["pisos"] if p["id"] == "inteligencia")
    assert p["paso"]["titulo"] == "Wispr Flow" and p["paso"]["contexto"] == "Para ti: copiable"
    assert p["entra"][0]["filas"] == [["Wispr Flow", "Hoy"], ["OpenAI", "Solo saber"]]


def test_sin_editor_no_se_inventa_nada():
    p = next(p for p in _armar()["pisos"] if p["id"] == "inteligencia")
    assert p["entra"][0]["filas"] == [] and p["entra"][0]["vacio"]


def test_temas_viejos_dicen_su_fecha(tmp_path):
    (tmp_path / "_editor-2026-11-02.json").write_text(json.dumps([{"titular": "A"}]), encoding="utf-8")
    (tmp_path / "_editor-2026-11-09.json").write_text(json.dumps([{"titular": "Futuro"}]), encoding="utf-8")
    temas, fecha = suite.temas_del_editor(date(2026, 11, 3), tmp_path)
    assert temas[0]["titular"] == "A" and fecha == "2026-11-02"


def test_ficha_sin_frontmatter_es_vacia(tmp_path):
    f = tmp_path / "suite.md"
    f.write_text("sin frontmatter", encoding="utf-8")
    assert suite.leer_ficha(f) == {}


def test_estado_de_agentes(tmp_path, monkeypatch):
    monkeypatch.setattr(agentes_estado, "RAIZ", tmp_path)
    ficha = {"nombre": "Editor", "piso": "inteligencia", "existe": True}
    assert agentes_estado.vivo("editor", ficha)["estado"] == "esperando"
    assert agentes_estado.vivo("x", {"existe": False})["estado"] == "por_crear"
    agentes_estado.reportar("editor", "trabajando", "Leyendo 12 temas")
    v = agentes_estado.vivo("editor", ficha)
    assert v["estado"] == "trabajando" and v["ahora"] == "Leyendo 12 temas"
    agentes_estado.reportar("editor", "durmiendo", "", ultimo="Publicó 3 temas")
    agentes_estado.reportar("editor", "trabajando", "Otra vez")
    assert agentes_estado.leer("editor")["ultimo"] == "Publicó 3 temas"
    tarde = datetime.now(timezone.utc) + timedelta(hours=7)
    assert agentes_estado.vivo("editor", ficha, ahora=tarde)["estado"] == "error"


def test_catalogo_tiene_remi_y_formas_validas():
    cat = agentes_estado.catalogo()
    assert cat["remi"]["existe"] is True
    assert {a["forma"] for a in cat.values()} <= {"orbe", "tri", "glifo", "cuadro", "rombo", "media", "hex", "pildora"}


def test_bloqueo_de_youtube_se_dice_con_la_hora():
    p = next(p for p in _armar(boveda={"leyendo": False, "agenda": {}, "enfriando_hasta": "17:30"})["pisos"] if p["id"] == "inteligencia")
    assert p["entra"][1]["filas"][0] == ["YouTube", "YouTube bloqueó; vuelve a las 17:30"]


def test_cobros_de_remi_mandan_sobre_la_ficha():
    p = next(p for p in _armar(cobros=[["Alfonso", "Pagada · US$2.000"]])["pisos"] if p["id"] == "ventas")
    assert p["entra"][0] == {"titulo": "Entregas y cobros", "fuente": "de Remi", "filas": [["Alfonso", "Pagada · US$2.000"]]}
    p = next(p for p in _armar()["pisos"] if p["id"] == "ventas")
    assert p["entra"][0]["filas"] == [["UpVisuals", "US$2.000"]]


def test_lo_que_publica_un_agente_manda_en_su_piso(tmp_path, monkeypatch):
    monkeypatch.setattr(agentes_estado, "PISOS_RAIZ", tmp_path)
    agentes_estado.publicar_piso("ventas", "vendedor", paso={"titulo": "Mandar el cobro", "contexto": "", "accion": "Ver borrador"},
                                 entra=[{"titulo": "Cobros", "fuente": "del Vendedor", "filas": [["Alfonso", "Borrador listo"]]}])
    agentes_estado.publicar_piso("ventas", "otro", entra=[{"titulo": "Seguimiento", "fuente": "", "filas": []}])
    pub = {"ventas": agentes_estado.leer_piso("ventas")}
    p = next(p for p in _armar(pisos_publicados=pub)["pisos"] if p["id"] == "ventas")
    assert p["paso"]["titulo"] == "Mandar el cobro"
    assert [e["titulo"] for e in p["entra"]] == ["Cobros", "Seguimiento"] and p["entra"][0]["fuente"] == "del Vendedor"


def test_temas_con_formato_real_del_editor():
    temas = [{"tema": "Falla de PHP", "para_ti": "revisa", "accion": "tener en cuenta"}]
    p = next(p for p in _armar(temas=(temas, "2026-11-04"))["pisos"] if p["id"] == "inteligencia")
    assert p["paso"]["titulo"] == "Falla de PHP" and p["entra"][0]["filas"] == [["Falla de PHP", "Tener en cuenta"]]

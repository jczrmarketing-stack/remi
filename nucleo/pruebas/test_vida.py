from datetime import date
from pathlib import Path

import vida as r


def _montar(tmp_path: Path, monkeypatch, estado_fecha="2026-10-27"):
    mente = tmp_path / "mente"
    for carpeta in ("yo", "negocio", "aprendido", "bandeja"):
        (mente / carpeta).mkdir(parents=True)
    (mente / "yo" / "metas.md").write_text("---\ntipo: yo\n---\n# Qué busca\n- Vender high ticket (27-oct).\n", encoding="utf-8")
    (mente / "negocio" / "frentes.md").write_text(f"---\nactualizado: {estado_fecha}\n---\n# Frentes\n- Fiverr: oferta abierta a eltondz\n", encoding="utf-8")
    (mente / "aprendido" / "supuestos.md").write_text("- [ ] eltondz no respondió · desde 2026-10-20 · revisar 2026-10-25\n- [ ] futuro · desde 2026-10-20 · revisar 2026-12-01\n", encoding="utf-8")
    (mente / "bandeja" / "bandeja.md").write_text("# Bandeja\n", encoding="utf-8")
    monkeypatch.setattr(r, "MENTE", mente)
    monkeypatch.setattr(r, "_boveda", lambda: None)
    return mente


def test_estado_sale_de_yo_y_negocio_sin_estado_md(tmp_path, monkeypatch):
    mente = _montar(tmp_path, monkeypatch)
    t = r.construir_estado(date(2026, 10, 27))
    assert "Vender high ticket" in t and "oferta abierta a eltondz" in t
    assert "tipo: yo" not in t and t.index("Qué busca") < t.index("# Frentes")
    assert not (mente / "vida").exists()


def test_estado_avisa_si_quedan_notas_en_rutas_viejas(tmp_path, monkeypatch):
    mente = _montar(tmp_path, monkeypatch)
    (mente / "vida").mkdir()
    assert "rutas viejas" in r.construir_estado(date(2026, 10, 27))


def test_buscar_no_entra_a_plantillas_ni_obsidian(tmp_path, monkeypatch):
    mente = _montar(tmp_path, monkeypatch)
    for carpeta in ("plantillas", ".obsidian"):
        (mente / carpeta).mkdir()
        (mente / carpeta / "x.md").write_text("zanahoria", encoding="utf-8")
    (mente / "aprendido" / "nota.md").write_text("zanahoria", encoding="utf-8")
    assert [ruta for ruta, _ in r.buscar("zanahoria")] == ["aprendido/nota.md"]


def test_estado_dice_la_edad_y_trae_supuestos_vencidos(tmp_path, monkeypatch):
    _montar(tmp_path, monkeypatch, "2026-10-20")
    t = r.construir_estado(date(2026, 10, 27))
    assert "tiene 7 día" in t and "eltondz no respondió" in t and "futuro" not in t


def test_estado_respeta_presupuesto(tmp_path, monkeypatch):
    vida = _montar(tmp_path, monkeypatch)
    (vida / "negocio" / "frentes.md").write_text("---\nactualizado: 2026-10-27\n---\n" + ("linea larga de relleno\n" * 600), encoding="utf-8")
    t = r.construir_estado(date(2026, 10, 27))
    assert len(t) <= r.PRESUPUESTO_CARACTERES + 120 and ("sigue en" in t or "no cupo" in t or "recortado" in t)


def test_anotar_supuesto_y_bandeja(tmp_path, monkeypatch):
    vida = _montar(tmp_path, monkeypatch)
    monkeypatch.setenv("REMI_HOY", "2026-10-27")
    assert "revisaré" in r.agregar("UpVisuals pagó", "supuesto", 3) or "revis" in r.agregar("otro", "supuesto", 3)
    assert "UpVisuals pagó" in (vida / "aprendido" / "supuestos.md").read_text(encoding="utf-8")
    assert "[decision]" in (r.agregar("vamos con el MCP", "decision") and (vida / "bandeja" / "bandeja.md").read_text(encoding="utf-8"))
    assert "no existe" in r.agregar("x", "inventado")
    assert "vacío" in r.agregar("   ", "hecho")


def test_buscar_con_acentos(tmp_path, monkeypatch):
    vida = _montar(tmp_path, monkeypatch)
    (vida / "nota.md").write_text("La oferta de eltondz por FletApp es de 1700 dólares", encoding="utf-8")
    res = r.buscar("oferta FletApp")
    assert res and "nota.md" in res[0][0]
    assert r.buscar("") == []

from datetime import date
from pathlib import Path

import remi_mcp as r


def _montar(tmp_path: Path, monkeypatch, estado_fecha="2026-10-27"):
    vida = tmp_path / "conocimiento" / "vida"
    vida.mkdir(parents=True)
    (vida / "estado.md").write_text(f"---\nactualizado: {estado_fecha}\n---\n# Frentes\n- Fiverr: oferta abierta a eltondz\n", encoding="utf-8")
    (vida / "supuestos.md").write_text("- [ ] eltondz no respondió · desde 2026-10-20 · revisar 2026-10-25\n- [ ] futuro · desde 2026-10-20 · revisar 2026-12-01\n", encoding="utf-8")
    (vida / "bandeja.md").write_text("# Bandeja\n", encoding="utf-8")
    monkeypatch.setattr(r, "RAIZ", tmp_path)
    monkeypatch.setattr(r, "VIDA", vida)
    monkeypatch.setattr(r, "_boveda", lambda: None)
    return vida


def test_estado_dice_la_edad_y_trae_supuestos_vencidos(tmp_path, monkeypatch):
    _montar(tmp_path, monkeypatch, "2026-10-20")
    t = r.construir_estado(date(2026, 10, 27))
    assert "tiene 7 día" in t and "eltondz no respondió" in t and "futuro" not in t


def test_estado_respeta_presupuesto(tmp_path, monkeypatch):
    vida = _montar(tmp_path, monkeypatch)
    (vida / "estado.md").write_text("---\nactualizado: 2026-10-27\n---\n" + ("linea larga de relleno\n" * 600), encoding="utf-8")
    t = r.construir_estado(date(2026, 10, 27))
    assert len(t) <= r.PRESUPUESTO_CARACTERES + 120 and "recortado" in t


def test_anotar_supuesto_y_bandeja(tmp_path, monkeypatch):
    vida = _montar(tmp_path, monkeypatch)
    monkeypatch.setenv("REMI_HOY", "2026-10-27")
    assert "revisaré" in r.agregar("UpVisuals pagó", "supuesto", 3) or "revis" in r.agregar("otro", "supuesto", 3)
    assert "UpVisuals pagó" in (vida / "supuestos.md").read_text(encoding="utf-8")
    assert "[decision]" in (r.agregar("vamos con el MCP", "decision") and (vida / "bandeja.md").read_text(encoding="utf-8"))
    assert "no existe" in r.agregar("x", "inventado")
    assert "vacío" in r.agregar("   ", "hecho")


def test_buscar_con_acentos(tmp_path, monkeypatch):
    vida = _montar(tmp_path, monkeypatch)
    (tmp_path / "conocimiento" / "nota.md").write_text("La oferta de eltondz por FletApp es de 1700 dólares", encoding="utf-8")
    res = r.buscar("oferta FletApp")
    assert res and "nota.md" in res[0][0]
    assert r.buscar("") == []

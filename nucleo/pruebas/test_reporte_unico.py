"""El reporte de la noche ya no sale a las 4:00: queda escrito para el mensaje único de las 11."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import noche
import vida


def _mente(monkeypatch, tmp_path):
    monkeypatch.setattr(vida, "MENTE", tmp_path)
    enviados = []
    monkeypatch.setattr(noche, "enviar_reporte_de_la_noche", lambda cambios, extra="": enviados.append(extra))
    return enviados


def test_normal_se_guarda_y_no_se_envia(tmp_path, monkeypatch):
    enviados = _mente(monkeypatch, tmp_path)
    noche.guardar_reporte_de_la_noche([("Malik", "d")], "Catálogo: 3 ok, 0 fallan")
    f = tmp_path / "mundo" / "newsletter" / f"_mensaje-noche-{date.today().isoformat()}.txt"
    assert enviados == [] and f.read_text(encoding="utf-8").startswith("Anoche cambié 1 libro: Malik.")
    assert "fallan" not in f.read_text(encoding="utf-8")   # los conteos no suben al teléfono


def test_una_contradiccion_si_sube(tmp_path, monkeypatch):
    _mente(monkeypatch, tmp_path)
    noche.guardar_reporte_de_la_noche([], "x: 1 ok; Esto cambia lo que creías: A dice 10 y B dice 20")
    f = tmp_path / "mundo" / "newsletter" / f"_mensaje-noche-{date.today().isoformat()}.txt"
    assert f.read_text(encoding="utf-8") == "Anoche no toqué nada\nEsto cambia lo que creías: A dice 10 y B dice 20\n"


def test_si_la_boveda_fallo_avisa_ya(tmp_path, monkeypatch):
    enviados = _mente(monkeypatch, tmp_path)
    noche.guardar_reporte_de_la_noche([], "bóveda no disponible")
    noche.guardar_reporte_de_la_noche([], "error OSError")
    assert len(enviados) == 2 and "No encontré la bóveda" in enviados[0]
    assert not (tmp_path / "mundo").exists()


def test_lo_personal_del_reporte_se_limpia_antes_de_ir_al_mensaje_publico(tmp_path, monkeypatch):
    _mente(monkeypatch, tmp_path)
    noche.guardar_reporte_de_la_noche([("Cobros de Malik", "d")], "x: 1 ok")
    f = tmp_path / "mundo" / "newsletter" / f"_mensaje-noche-{date.today().isoformat()}.txt"
    assert f.read_text(encoding="utf-8") == "Anoche cambié 1 libro. Lo vemos en el Mac.\n"


def test_un_aviso_publico_no_pasa_por_el_filtro_y_uno_normal_si(monkeypatch):
    import telegram
    enviados = []
    monkeypatch.setattr(telegram, "en_silencio", lambda: False)
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "1")
    monkeypatch.setattr(telegram, "token", lambda: "t")
    monkeypatch.setattr(telegram, "_transporte_para_avisar", lambda tok: None)
    monkeypatch.setattr(telegram, "_enviar_con_reintento", lambda tr, chat, texto: enviados.append(texto))
    class HiloYa:
        def __init__(self, target, args, daemon): self.f, self.a = target, args
        def start(self): self.f(*self.a)
    monkeypatch.setattr(telegram.threading, "Thread", HiloYa)
    telegram.avisar(telegram.AvisoSaliente(texto="Claude Ultra cuesta $200/mes", publico=True))
    telegram.avisar(telegram.AvisoSaliente(texto="te pagaron $200"))
    assert enviados == ["Claude Ultra cuesta $200/mes", telegram.AVISO_PRIVADO]

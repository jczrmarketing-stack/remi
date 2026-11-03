"""Las fallas de Remi van al bot de alertas de INV3RZA, nunca al chat de Remi (3-nov)."""
from __future__ import annotations

import alertas


def test_la_alerta_usa_el_bot_de_alertas(monkeypatch):
    monkeypatch.setattr(alertas, "credenciales", lambda: ("123:abc", "999"))
    vistos = []
    assert alertas.enviar("la noche se cayó", post=lambda url, json, timeout: vistos.append((url, json))) is True
    url, cuerpo = vistos[0]
    assert "bot123:abc/sendMessage" in url and cuerpo["chat_id"] == "999" and "la noche se cayó" in cuerpo["text"]


def test_sin_llave_no_revienta(monkeypatch):
    monkeypatch.setattr(alertas, "credenciales", lambda: ("", ""))
    assert alertas.enviar("x") is False


def test_vida_ya_no_pregunta_por_telegram(tmp_path, monkeypatch):
    import vida
    monkeypatch.setattr(vida, "MENTE", tmp_path)
    monkeypatch.setattr(vida, "_avisar_telegram", lambda texto: (_ for _ in ()).throw(AssertionError("no debía avisar")))
    import inspect
    assert "_avisar_telegram(f\"¿Guardo" not in inspect.getsource(vida)

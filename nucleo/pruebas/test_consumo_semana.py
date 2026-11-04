"""`python3 nucleo/consumo.py --semana`: el total por agente de los últimos 7 días.

Base temporal siempre; nunca el remi.db real."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import consumo


@pytest.fixture
def base(tmp_path: Path) -> Path:
    return tmp_path / "consumo.db"


def _respuesta(entrada=10, salida=5) -> str:
    return json.dumps({"type": "result", "result": "hola", "usage": {"input_tokens": entrada, "output_tokens": salida}})


def test_suma_por_agente_en_los_ultimos_7_dias(base):
    ahora = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    consumo.registrar("editor", "sonnet", 1.0, _respuesta(entrada=10, salida=1), ruta=base, ahora=ahora)
    consumo.registrar("editor", "sonnet", 3.0, _respuesta(entrada=20, salida=2), ruta=base, ahora=ahora - timedelta(days=2))
    consumo.registrar("editor", "sonnet", 1.0, "", returncode=1, ruta=base, ahora=ahora - timedelta(days=1))
    consumo.registrar("vendedor", "sonnet", 2.0, _respuesta(entrada=5, salida=5), ruta=base, ahora=ahora)
    # Fuera de la ventana: no cuenta.
    consumo.registrar("editor", "sonnet", 9.0, _respuesta(entrada=999, salida=999), ruta=base, ahora=ahora - timedelta(days=8))

    resumen = {r["agente"]: r for r in consumo.resumen_semana(ruta=base, ahora=ahora)}
    assert set(resumen) == {"editor", "vendedor"}
    editor = resumen["editor"]
    assert editor["llamadas"] == 3
    assert editor["fallos"] == 1
    assert editor["tokens_entrada"] == 30
    assert editor["tokens_salida"] == 3
    assert editor["duracion_ms"] == 5000
    assert resumen["vendedor"]["llamadas"] == 1 and resumen["vendedor"]["fallos"] == 0


def test_si_la_base_no_se_puede_abrir_el_resumen_viene_vacio(tmp_path):
    assert consumo.resumen_semana(ruta=tmp_path / "no" / "existe" / "x.db") == []


def test_sin_base_creada_el_resumen_viene_vacio(base):
    assert consumo.resumen_semana(ruta=base) == []


def test_semana_imprime_el_total_por_agente(base, capsys, monkeypatch):
    consumo.registrar("editor", "sonnet", 90.0, _respuesta(entrada=1200, salida=300), ruta=base)
    consumo.registrar("vendedor", "sonnet", 30.0, "", returncode=1, ruta=base)
    monkeypatch.setenv("REMI_DB_PATH", str(base))
    assert consumo.main(["--semana"]) == 0
    salida = capsys.readouterr().out
    assert "editor" in salida and "vendedor" in salida
    assert "1200" in salida.replace(".", "").replace(",", "")


def test_semana_sin_datos_lo_dice(base, capsys, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(base))
    assert consumo.main(["--semana"]) == 0
    assert "nada" in capsys.readouterr().out.lower()

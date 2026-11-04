"""El registro de consumo de `claude -p` (Bloque 0 de la fábrica).

Todas las pruebas usan una base temporal: ninguna toca el remi.db real."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

import consumo


@pytest.fixture
def base(tmp_path: Path) -> Path:
    return tmp_path / "consumo.db"


def _filas(base: Path) -> list[sqlite3.Row]:
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT * FROM consumo_claude ORDER BY id").fetchall()
    finally:
        con.close()


def _respuesta(entrada=10, salida=5, leida=0, escrita=0, **extra) -> str:
    datos = {
        "type": "result",
        "result": "hola",
        "is_error": False,
        "usage": {
            "input_tokens": entrada,
            "output_tokens": salida,
            "cache_read_input_tokens": leida,
            "cache_creation_input_tokens": escrita,
        },
    }
    datos.update(extra)
    return json.dumps(datos)


def test_guarda_agente_fecha_duracion_tokens_y_ok(base):
    ahora = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    consumo.registrar("editor", "sonnet", 2.5, _respuesta(entrada=10, salida=5, leida=100, escrita=20), ruta=base, ahora=ahora)
    (fila,) = _filas(base)
    assert fila["agente"] == "editor"
    assert fila["modelo"] == "sonnet"
    assert fila["fecha"] == ahora.isoformat()
    assert fila["duracion_ms"] == 2500
    # La caché también es entrada: sin eso se vería 10 donde Claude leyó 130.
    assert fila["tokens_entrada"] == 130
    assert fila["tokens_salida"] == 5
    assert fila["ok"] == 1


def test_acepta_el_resultado_ya_leido_del_stream(base):
    consumo.registrar("pensar", "haiku", 1.0, json.loads(_respuesta(entrada=3, salida=4)), ruta=base)
    (fila,) = _filas(base)
    assert (fila["tokens_entrada"], fila["tokens_salida"], fila["ok"]) == (3, 4, 1)


def test_acepta_stream_json_con_la_linea_result_al_final(base):
    stream = "\n".join([json.dumps({"type": "system"}), "no es json", _respuesta(entrada=7, salida=8)])
    consumo.registrar("pensar", "haiku", 1.0, stream, ruta=base)
    (fila,) = _filas(base)
    assert (fila["tokens_entrada"], fila["tokens_salida"], fila["ok"]) == (7, 8, 1)


@pytest.mark.parametrize("salida", ["", "   ", "no es json", "{roto", "[]", "null", "42", None, {}, []])
def test_respuesta_vacia_o_rota_no_rompe_y_queda_como_fallo(base, salida):
    consumo.registrar("clasificador", "haiku", 1.0, salida, ruta=base)
    (fila,) = _filas(base)
    assert fila["ok"] == 0
    assert fila["tokens_entrada"] == 0 and fila["tokens_salida"] == 0


def test_un_resultado_con_is_error_cuenta_como_fallo_pero_guarda_los_tokens(base):
    consumo.registrar("vendedor", "sonnet", 1.0, _respuesta(entrada=4, salida=0, is_error=True), ruta=base)
    (fila,) = _filas(base)
    assert fila["ok"] == 0 and fila["tokens_entrada"] == 4


def test_un_resultado_sin_texto_cuenta_como_fallo(base):
    consumo.registrar("vendedor", "sonnet", 1.0, _respuesta(result="  "), ruta=base)
    assert _filas(base)[0]["ok"] == 0


def test_timeout_o_error_explicito_se_guarda_como_fallo_con_el_motivo(base):
    consumo.registrar("coding", "opus", 600.0, "", error="timeout", ruta=base)
    (fila,) = _filas(base)
    assert fila["ok"] == 0 and fila["error"] == "timeout"


def test_tokens_raros_no_rompen(base):
    consumo.registrar("pensar", "haiku", 1.0, json.dumps({"result": "x", "usage": {"input_tokens": "mil", "output_tokens": None}}), ruta=base)
    (fila,) = _filas(base)
    assert (fila["tokens_entrada"], fila["tokens_salida"], fila["ok"]) == (0, 0, 1)


def test_si_la_base_no_se_puede_abrir_no_levanta(tmp_path):
    # Una carpeta que no existe: sqlite no puede crear el archivo.
    consumo.registrar("editor", "sonnet", 1.0, _respuesta(), ruta=tmp_path / "no" / "existe" / "x.db")


# — En una llamada de verdad (con la CLI simulada) —


def _cli_simulada(stdout: str, returncode: int = 0):
    import subprocess

    return subprocess.CompletedProcess(args=["claude"], returncode=returncode, stdout=stdout, stderr="")


def test_pensar_deja_su_fila_y_cierre_la_deja_con_su_nombre(base, monkeypatch):
    import pensar

    monkeypatch.setenv("REMI_DB_PATH", str(base))
    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: _cli_simulada(_respuesta(entrada=11, salida=7)))
    assert pensar._una_llamada_claude(pensar.MODOS["rapido"], "hola", "instr", []) is not None
    assert pensar._una_llamada_claude(pensar.MODOS["rapido"], "hola", "instr", [], agente="cierre") is not None
    filas = _filas(base)
    assert [f["agente"] for f in filas] == ["pensar", "cierre"]
    assert (filas[0]["tokens_entrada"], filas[0]["tokens_salida"], filas[0]["ok"]) == (11, 7, 1)


def test_pensar_registra_el_fallo_de_la_cli(base, monkeypatch):
    import pensar

    monkeypatch.setenv("REMI_DB_PATH", str(base))
    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: _cli_simulada("", returncode=1))
    assert pensar._una_llamada_claude(pensar.MODOS["rapido"], "hola", "instr", []) is None
    (fila,) = _filas(base)
    assert fila["ok"] == 0 and "1" in fila["error"]


def test_si_el_registro_falla_la_llamada_a_claude_sigue_igual(tmp_path, monkeypatch):
    import pensar

    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "no" / "existe" / "x.db"))
    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: _cli_simulada(_respuesta()))
    pensado = pensar._una_llamada_claude(pensar.MODOS["rapido"], "hola", "instr", [])
    assert pensado is not None and pensado.paso_minimo == "hola"

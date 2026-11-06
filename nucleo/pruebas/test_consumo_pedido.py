"""Traza por pedido de la fábrica (Bloque 1): cada fila sabe de qué pedido es."""

import sqlite3

import consumo

SALIDA = {"result": "ok", "usage": {"input_tokens": 10, "output_tokens": 5}}

ESQUEMA_VIEJO = """
CREATE TABLE consumo_claude (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agente TEXT NOT NULL,
    fecha TEXT NOT NULL,
    duracion_ms INTEGER NOT NULL DEFAULT 0,
    tokens_entrada INTEGER NOT NULL DEFAULT 0,
    tokens_salida INTEGER NOT NULL DEFAULT 0,
    ok INTEGER NOT NULL DEFAULT 0,
    modelo TEXT,
    error TEXT
);
"""


def test_registrar_guarda_el_pedido(tmp_path):
    ruta = tmp_path / "r.db"
    consumo.registrar("planificador", "opus", 1.0, SALIDA, ruta=ruta, pedido="p1")
    assert consumo.tokens_del_pedido("p1", ruta) == 15
    assert consumo.tokens_del_pedido("otro", ruta) == 0


def test_migra_una_tabla_vieja_sin_columna_pedido(tmp_path):
    ruta = tmp_path / "r.db"
    con = sqlite3.connect(ruta)
    con.executescript(ESQUEMA_VIEJO)
    con.execute("INSERT INTO consumo_claude (agente, fecha) VALUES ('coding', '2026-11-01')")
    con.commit()
    con.close()
    consumo.registrar("tester", "sonnet", 1.0, SALIDA, ruta=ruta, pedido="p2")
    con = sqlite3.connect(ruta)
    filas = con.execute("SELECT agente, pedido FROM consumo_claude ORDER BY id").fetchall()
    con.close()
    assert filas == [("coding", None), ("tester", "p2")]
    assert consumo.tokens_del_pedido("p2", ruta) == 15


def test_sin_base_tokens_del_pedido_es_cero(tmp_path):
    assert consumo.tokens_del_pedido("p1", tmp_path / "no-existe.db") == 0


def test_semana_muestra_por_pedido(tmp_path):
    ruta = tmp_path / "r.db"
    consumo.registrar("planificador", "opus", 1.0, SALIDA, ruta=ruta, pedido="p1")
    consumo.registrar("tester", "sonnet", 1.0, SALIDA, ruta=ruta, pedido="p1")
    consumo.registrar("coding", "sonnet", 1.0, SALIDA, ruta=ruta)
    por_pedido = consumo.resumen_por_pedido(ruta)
    assert por_pedido == [{"pedido": "p1", "llamadas": 2, "tokens": 30}]
    texto = consumo.texto_semana(consumo.resumen_semana(ruta), por_pedido)
    assert "por pedido" in texto
    assert "p1" in texto

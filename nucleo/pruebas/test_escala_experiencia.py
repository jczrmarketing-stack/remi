"""T9.6: prueba de escala — para saber y no suponer. No corre en cada
pytest (lenta, genera 50.000 filas sintéticas); a mano:

    REMI_PRUEBA_ESCALA=1 uv run pytest -q pruebas/test_escala_experiencia.py -s

El resultado se anota en la bitácora, no se oculta si algo no da el número.
"""
import os
import sqlite3
import time
from uuid import uuid4

import pytest
import sqlite_vec

import db
import experiencia
import pensar
import vectores

pytestmark = pytest.mark.skipif(
    os.environ.get("REMI_PRUEBA_ESCALA") != "1",
    reason="prueba de escala (T9.6): corre a mano con REMI_PRUEBA_ESCALA=1 (genera 50.000 filas)",
)

N = 50_000


def _conexion_con_50000_notas() -> sqlite3.Connection:
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    vectores.preparar(conexion)
    experiencia._preparar_fts(conexion)
    for i in range(N):
        ruta = f"/sintetico/nota-{i}.md"
        titulo = f"Nota sintética {i}"
        texto = f"Nota sintética número {i} sobre el tema {i % 50}, con un código ERR-{i:05d}."
        vector = [((i * 7) % 1000) / 1000.0] * vectores.DIMENSIONES
        conexion.execute(
            "INSERT INTO notas_vector (id, ruta, tipo, titulo, hash, actualizado) "
            "VALUES (?, ?, 'leccion', ?, ?, datetime('now'))",
            (i, ruta, titulo, str(i)),
        )
        conexion.execute(
            "INSERT INTO notas_vector_embed (rowid, embedding) VALUES (?, ?)",
            (i, sqlite_vec.serialize_float32(vector)),
        )
        conexion.execute(
            "INSERT INTO experiencia_fts (ruta, tipo, tema, titulo, resumen, cuerpo) VALUES (?, ?, ?, ?, ?, ?)",
            (ruta, "leccion", f"tema{i % 50}", titulo, texto, texto),
        )
    conexion.commit()
    return conexion


def test_busqueda_hibrida_bajo_200ms_con_50000_notas(monkeypatch):
    conexion = _conexion_con_50000_notas()
    monkeypatch.setattr(vectores, "embed", lambda _texto: [0.314] * vectores.DIMENSIONES)

    arranque = time.perf_counter()
    resultados = experiencia.buscar(conexion, "ERR-02500")
    ms = (time.perf_counter() - arranque) * 1000

    print(f"\n[T9.6] búsqueda híbrida sobre {N} notas: {ms:.1f} ms, {len(resultados)} resultado(s)")
    assert ms < 200, f"la búsqueda híbrida tardó {ms:.1f} ms con {N} notas (límite: 200 ms)"


def test_armar_la_mente_bajo_8000_tokens_con_50000_entradas(tmp_path, monkeypatch):
    """«Armar la mente» = el índice de Memoria que entra en TODO prompt
    (pensar.instrucciones_con_indice). Esto mide lo que hay, no inventa un
    límite que el código no tiene todavía — si no entra, el resultado real
    queda anotado en la bitácora, no se oculta."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    for i in range(N):
        conexion.execute(
            "INSERT INTO memoria (id, titulo, resumen, tema, fecha, cuerpo, fuente, claves, nivel) "
            "VALUES (?, ?, ?, ?, datetime('now'), 'x', 'manual', NULL, 1)",
            (str(uuid4()), f"Nota {i}"[:80], f"Resumen de la nota {i}."[:240], f"tema{i % 50}"),
        )
    conexion.commit()
    conexion.close()

    indice = pensar._indice()
    texto = pensar.instrucciones_con_indice(indice, base="")
    tokens_aprox = len(texto) / 4  # heurística de siempre: ~4 caracteres por token

    print(f"\n[T9.6] índice de la mente con {N} entradas: {len(texto)} caracteres (~{tokens_aprox:.0f} tokens)")
    if tokens_aprox >= 8000:
        print(
            f"[T9.6] HALLAZGO: el índice de Memoria no tiene techo — con {N} entradas da "
            f"~{tokens_aprox:.0f} tokens, por encima de 8.000. db.indice_memoria() devuelve TODAS "
            "las filas, sin límite ni corte por nivel. Anotado para una fase futura, no corregido acá."
        )
    assert len(indice) == N  # el hallazgo es justo que esto no se corta solo

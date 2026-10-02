"""T9.6 + T10: prueba de escala — para saber y no suponer. No corre en cada
pytest (lenta, genera 50.000 filas sintéticas); a mano:

    REMI_PRUEBA_ESCALA=1 uv run pytest -q pruebas/test_escala_experiencia.py -s

El resultado se anota en la bitácora, no se oculta si algo no da el número.
T9.6 encontró que armar la mente no tenía techo; T10 le puso presupuesto.
"""
import os
import sqlite3
import time
from uuid import UUID, uuid4

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
    """T10: el hallazgo de T9.6 era real (el índice no tenía techo). Con el
    presupuesto de T10.2, 50.000 entradas (nivel 2, como una sesión real de
    cierre.py) se muestran recortadas bajo 8.000 tokens — y la que quedó
    afuera (la más vieja) sigue encontrable con buscar_memoria. Ninguna fila
    se borra: siguen las 50.000 en remi.db."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    mas_vieja_id = str(uuid4())
    conexion.execute(
        "INSERT INTO memoria (id, titulo, resumen, tema, fecha, cuerpo, fuente, claves, nivel) "
        "VALUES (?, 'La más vieja de todas', 'palabra-unica-rara', 'tema0', '2000-01-01T00:00:00+00:00', "
        "'x', 'manual', NULL, 2)",
        (mas_vieja_id,),
    )
    for i in range(N):
        conexion.execute(
            "INSERT INTO memoria (id, titulo, resumen, tema, fecha, cuerpo, fuente, claves, nivel) "
            "VALUES (?, ?, ?, ?, datetime('now'), 'x', 'manual', NULL, 2)",
            (str(uuid4()), f"Nota {i}"[:80], f"Resumen de la nota {i}."[:240], f"tema{i % 50}"),
        )
    conexion.commit()

    arranque = time.perf_counter()
    indice = pensar._indice()
    texto = pensar.instrucciones_con_indice(indice, base="")
    ms_armar = (time.perf_counter() - arranque) * 1000
    tokens_aprox = len(texto) / 4  # heurística de siempre: ~4 caracteres por token

    arranque = time.perf_counter()
    encontrada = db.buscar_memoria(conexion, "palabra-unica-rara")
    ms_buscar = (time.perf_counter() - arranque) * 1000
    conexion.close()

    print(
        f"\n[T10] armar la mente con {N + 1} entradas: {ms_armar:.1f} ms, "
        f"{len(texto)} caracteres (~{tokens_aprox:.0f} tokens); buscar_memoria: {ms_buscar:.1f} ms"
    )
    assert len(indice) == N + 1  # nada se borró de la base
    assert tokens_aprox < 8000, f"el índice renderizado dio ~{tokens_aprox:.0f} tokens (límite: 8.000)"
    assert "La más vieja de todas" not in texto  # quedó afuera del presupuesto
    assert [e.id for e in encontrada] == [UUID(mas_vieja_id)]  # pero sigue encontrable

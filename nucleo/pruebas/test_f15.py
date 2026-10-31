"""F1.5: embeddings configurables con reconstrucción, reordenador opcional, evaluación.
Corre con pytest o con `python3 nucleo/pruebas/test_f15.py` (necesita sqlite-vec, httpx, pyyaml)."""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import evaluar  # noqa: E402
import indexar  # noqa: E402
import reordenar  # noqa: E402
import vectores  # noqa: E402
import vida  # noqa: E402


def test_config_por_defecto_y_entorno():
    assert vectores.MODELO_EMBEDDINGS and vectores.DIMENSIONES > 0
    os.environ["REMI_EMBED_MODELO"], os.environ["REMI_EMBED_DIM"] = "otro-modelo", "384"
    try:
        c = vectores._configuracion()
        assert c["modelo"] == "otro-modelo" and c["dimensiones"] == 384
    finally:
        del os.environ["REMI_EMBED_MODELO"], os.environ["REMI_EMBED_DIM"]


def test_embed_consulta_lleva_prefijo_y_las_notas_no():
    vistos = []
    original = vectores.embed
    vectores.embed = lambda t: vistos.append(t) or [0.0] * vectores.DIMENSIONES
    try:
        vectores.embed_consulta("¿qué es graphify?")
    finally:
        vectores.embed = original
    assert vistos[0].endswith("¿qué es graphify?") and vistos[0].startswith(vectores.PREFIJO_CONSULTA)


def test_cambio_de_modelo_reconstruye_los_vectores():
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "indice.db"
        con = indexar.conectar(ruta)
        con.execute("INSERT INTO notas VALUES (1,'a','/x','fuente','t','r','2026-10-31','activa','media','h1','h1')")
        con.execute("INSERT INTO notas_vec (rowid, embedding) VALUES (1, ?)",
                    (__import__("sqlite_vec").serialize_float32([0.1] * vectores.DIMENSIONES),))
        con.commit()
        assert indexar.alinear(con) is False  # mismo modelo: no toca nada
        assert con.execute("SELECT COUNT(*) FROM notas_vec").fetchone()[0] == 1
        con.close()
        viejo = (vectores.MODELO_EMBEDDINGS, vectores.DIMENSIONES)
        vectores.MODELO_EMBEDDINGS, vectores.DIMENSIONES = "modelo-nuevo", 16
        try:
            con = indexar.conectar(ruta)  # conectar alinea solo
            assert con.execute("SELECT COUNT(*) FROM notas_vec").fetchone()[0] == 0
            assert con.execute("SELECT hash_vector FROM notas WHERE rowid=1").fetchone()[0] is None
            assert con.execute("SELECT valor FROM meta WHERE clave='embeddings'").fetchone()[0] == "modelo-nuevo|16"
            con.execute("INSERT INTO notas_vec (rowid, embedding) VALUES (1, ?)",
                        (__import__("sqlite_vec").serialize_float32([0.2] * 16),))  # acepta la dimensión nueva
            con.close()
        finally:
            vectores.MODELO_EMBEDDINGS, vectores.DIMENSIONES = viejo


def test_indice_sin_registro_con_vectores_se_asume_modelo_anterior():
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "indice.db"
        con = indexar.conectar(ruta)
        con.execute("INSERT INTO notas VALUES (1,'a','/x','fuente','t','r','2026-10-31','activa','media','h1','h1')")
        con.execute("DELETE FROM meta")  # índice de antes de F1.5
        con.commit()
        assert indexar.alinear(con) is (vectores.firma_modelo() != vectores.firma_modelo(*vectores.MODELO_ANTERIOR))
        con.close()


def test_reordenar_sin_modelo_devuelve_none_y_con_modelo_ordena():
    assert reordenar.reordenar("x", [(1, "a")], modelo="no-existe-/-sin-libreria") is None
    original = reordenar.puntuar
    reordenar.puntuar = lambda q, textos, modelo=None: [0.1, 0.9, 0.5]
    try:
        assert reordenar.reordenar("q", [(10, "a"), (20, "b"), (30, "c")]) == [20, 30, 10]
    finally:
        reordenar.puntuar = original


def test_buscar_rerank_cae_a_hibrida_si_el_reordenador_falla():
    with tempfile.TemporaryDirectory() as d:
        con = indexar.conectar(Path(d) / "indice.db")
        for i, (t, r) in enumerate([("Graphify grafo de código", "ahorra tokens"), ("Otra cosa", "nada que ver")], start=1):
            con.execute("INSERT INTO notas VALUES (?,?,?,?,?,?,?,?,?,?,NULL)", (i, f"n{i}", "/x", "fuente", t, r, "2026-10-31", "activa", "media", f"h{i}"))
            con.execute("INSERT INTO notas_fts (rowid, titulo, resumen, cuerpo) VALUES (?,?,?,?)", (i, t, r, r))
        con.commit()
        original, original_puntuar = vectores.embed, reordenar.puntuar
        vectores.embed = lambda t: (_ for _ in ()).throw(ValueError("sin ollama"))
        reordenar.puntuar = lambda *a, **k: None
        try:
            a = [h.id for h in indexar.buscar(con, "graphify tokens", modo="hibrida")]
            b = [h.id for h in indexar.buscar(con, "graphify tokens", modo="rerank")]
        finally:
            vectores.embed, reordenar.puntuar = original, original_puntuar
        assert a == b == ["n1"]
        con.close()


def test_metricas_y_decision():
    assert evaluar.recall_en_k(["a", "b", "c"], ["c"], 5) == 1.0
    assert evaluar.recall_en_k(["a", "b", "c"], ["c"], 2) == 0.0
    assert evaluar.rr(["a", "b", "c"], ["b", "c"]) == 0.5 and evaluar.rr(["a"], ["z"]) == 0.0
    base = {"casos": 10, "recall5": 0.6, "mrr": 0.4, "tokens": 300}
    assert evaluar.decidir(base, {"casos": 10, "recall5": 0.8, "mrr": 0.5, "tokens": 310}) == "ADOPTAR"
    assert evaluar.decidir(base, {"casos": 10, "recall5": 0.8, "mrr": 0.5, "tokens": 500}) == "no adoptar"
    assert evaluar.decidir(base, {"casos": 0, "recall5": 0, "mrr": 0, "tokens": 0}) == "sin casos"


def test_casos_semilla_y_reales():
    assert len(evaluar.casos_semilla()) >= 4
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "metricas.db"
        con = sqlite3.connect(db)
        con.executescript("CREATE TABLE consultas (id INTEGER PRIMARY KEY, ts TEXT, origen TEXT, sesion TEXT, consulta TEXT, n INT, chars INT, ids TEXT, acierto INT, web_despues INT);"
                          "CREATE TABLE eventos (id INTEGER PRIMARY KEY, ts TEXT, sesion TEXT, tipo TEXT, detalle TEXT);")
        from datetime import datetime, timedelta
        ahora = datetime.now()
        con.execute("INSERT INTO consultas (ts,origen,sesion,consulta,n,chars,ids) VALUES (?,?,?,?,?,?,?)", (ahora.isoformat(timespec="seconds"), "hook", "s1", "cómo ahorrar tokens con claude", 3, 100, "[]"))
        con.execute("INSERT INTO consultas (ts,origen,sesion,consulta,n,chars,ids) VALUES (?,?,?,?,?,?,?)", (ahora.isoformat(timespec="seconds"), "hook", "s2", "sin lectura posterior aquí", 3, 100, "[]"))
        con.execute("INSERT INTO eventos (ts,sesion,tipo,detalle) VALUES (?,?,?,?)", ((ahora + timedelta(minutes=2)).isoformat(timespec="seconds"), "s1", "acierto", "mcp__remi__leer:Dc0wusZtJK3"))
        con.commit(); con.close()
        reales = evaluar.casos_reales(db)
        assert reales == [{"consulta": "cómo ahorrar tokens con claude", "esperados": ["Dc0wusZtJK3"], "origen": "real"}]


def test_informe_incluye_veredicto():
    r = {"hibrida": {"todos": {"casos": 4, "recall5": 0.5, "mrr": 0.3, "tokens": 200}},
         "rerank": {"todos": {"casos": 4, "recall5": 0.75, "mrr": 0.5, "tokens": 205}}}
    texto = evaluar.informe(r, "qwen3-embedding:0.6b|1024")
    assert "ADOPTAR" in texto and "| hibrida | 0.50" in texto


if __name__ == "__main__":
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith("test_") and callable(f):
            try:
                f(); print("ok  ", nombre)
            except Exception as exc:  # noqa: BLE001
                fallos += 1; print("FALLA", nombre, "→", type(exc).__name__, exc)
    sys.exit(1 if fallos else 0)

"""F1.3: router del hook, métricas, anotar con tipos, instalador de hooks.
Solo stdlib; corre con pytest o con `python3 nucleo/pruebas/test_f13.py`."""
from __future__ import annotations

import importlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parent.parent / "scripts"))

import metricas  # noqa: E402
import vida  # noqa: E402


@contextmanager
def mente_temporal():
    with tempfile.TemporaryDirectory() as d:
        vieja = vida.MENTE
        vida.MENTE = Path(d)
        os.environ["REMI_HOY"] = "2026-10-30"
        os.environ["REMI_AHORA"] = "2026-10-30T10:00:00"
        try:
            yield Path(d)
        finally:
            vida.MENTE = vieja
            os.environ.pop("REMI_HOY", None)
            os.environ.pop("REMI_AHORA", None)


def _indice_falso(ruta: Path) -> None:
    con = sqlite3.connect(ruta)
    con.executescript(
        "CREATE TABLE notas (rowid INTEGER PRIMARY KEY, id TEXT, ruta TEXT, tipo TEXT, titulo TEXT, resumen TEXT, fecha TEXT, estatus TEXT, confianza TEXT, hash TEXT, hash_vector TEXT);"
        "CREATE VIRTUAL TABLE notas_fts USING fts5(titulo, resumen, cuerpo, tokenize='unicode61 remove_diacritics 2');"
    )
    filas = [
        (1, "mundo/fuentes/graphify.md", "fuente", "Graphify: ahorra tokens en Claude Code", "Mapa del proyecto para no releerlo", "2026-10-30", "hipotesis", "media", "Graphify crea un mapa completo del proyecto y reduce tokens en Claude Code"),
        (2, "mundo/fuentes/colores.md", "fuente", "Colores y engagement", "Azul con rosa se ve mejor", "2026-10-30", "hipotesis", "baja", "Azul y blanco se ven bien pero con rosa mejor"),
        (3, "aprendido/lecciones/fts.md", "leccion", "La noche no reindexaba el FTS", "Reindexar experiencia cada noche", "2026-10-26", "leccion", "alta", "La noche no reindexaba el FTS de experiencia y las lecciones nuevas no salían"),
    ]
    for rowid, id_, tipo, titulo, resumen, fecha, estatus, confianza, cuerpo in filas:
        con.execute("INSERT INTO notas VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rowid, id_, id_, tipo, titulo, resumen, fecha, estatus, confianza, "h", None))
        con.execute("INSERT INTO notas_fts (rowid, titulo, resumen, cuerpo) VALUES (?,?,?,?)", (rowid, titulo, resumen, cuerpo))
    # El índice real tiene una tabla vec0 que el python del sistema no sabe abrir: simularla.
    con.execute("PRAGMA writable_schema=ON")
    con.execute("INSERT INTO sqlite_master (type, name, tbl_name, rootpage, sql) VALUES ('table','notas_vec','notas_vec',0,'CREATE VIRTUAL TABLE notas_vec USING vec0(embedding float[768])')")
    con.execute("PRAGMA writable_schema=OFF")
    con.commit()
    con.close()


def test_buscar_indice_con_umbral_y_sin_sqlite_vec():
    with mente_temporal() as m:
        _indice_falso(m / "indice.db")
        fichas = vida.buscar_indice("cómo ahorrar tokens en Claude Code con un mapa del proyecto")
        assert [f["id"] for f in fichas] == ["mundo/fuentes/graphify.md"], fichas
        assert vida.buscar_indice("receta de arepas con queso") == []
        assert vida.buscar_indice("tokens") == []  # un solo término no basta
        ctx = vida.fichas_para_contexto(fichas)
        assert ctx.startswith("LA MENTE YA TIENE ALGO") and "[mundo/fuentes/graphify.md]" in ctx and len(ctx) <= vida.PRESUPUESTO_HOOK


def test_metricas_consulta_acierto_web():
    with mente_temporal():
        metricas.registrar_consulta("hook", "s1", "ahorrar tokens", ["a"], 400)
        metricas.marcar("s1", "acierto", "mcp__remi__leer")
        metricas.registrar_consulta("hook", "s2", "otra cosa", ["b"], 300)
        metricas.marcar("s2", "web", "WebSearch")
        metricas.registrar_consulta("hook", "s3", "nada", [], 0)
        metricas.marcar("s3", "web", "WebSearch")  # sin fichas antes: no cuenta como web_despues
        r = metricas.resumen(7)
        assert (r["consultas"], r["con_algo"], r["aciertos"], r["web_despues"], r["web_evitadas"]) == (3, 2, 1, 1, 1), r
        assert "Webs evitadas | 1" in metricas.texto_uso(7)


def test_anotar_tipos_y_compuerta():
    with mente_temporal() as m:
        r = vida.anotar("Subir el precio del software de WhatsApp a 1.200 USD. Razón: techo de horas.", "decision")
        assert "aprendido/decisiones/2026-10-30-subir-el-precio" in r
        ruta = next((m / "aprendido" / "decisiones").glob("*.md"))
        assert "tipo: decision" in ruta.read_text() and "estatus: decidido" in ruta.read_text()
        r = vida.anotar("Graphify ahorra 1x-3x en repos chicos", "investigacion")
        assert "necesita al menos una URL" in r
        r = vida.anotar("Graphify ahorra 1x-3x en repos chicos", "investigacion", fuentes="https://www.roborhythms.com/graphify-review/")
        assert "mundo/investigaciones/" in r
        assert 'fuentes: ["https://www.roborhythms.com/graphify-review/"]' in next((m / "mundo" / "investigaciones").glob("*.md")).read_text()
        r = vida.anotar("Prefiere trabajar de noche", "hecho_sobre_mi")
        assert "por confirmar" in r and "- [ ] Prefiere trabajar de noche" in (m / "bandeja" / "por-confirmar.md").read_text()
        r = vida.anotar("Las agencias contestan en menos de 2 h", "hipotesis")
        assert "[hipotesis]" in (m / "bandeja" / "bandeja.md").read_text()
        r = vida.anotar("Predije 3 respuestas y llegaron 1", "resultado")
        assert (m / "aprendido" / "diario" / "2026-10-30.md").exists()
        assert "no existe" in vida.anotar("x", "cualquiera")
        assert "supuesto" in vida.anotar("Cree que Fiverr paga en 14 días", "supuesto")


def test_hook_post_marca_acierto():
    with mente_temporal():
        metricas.registrar_consulta("hook", "s9", "mapa del repo", ["x"], 200)
        hook = importlib.import_module("hook_post_herramienta")
        sys.stdin = io.StringIO(json.dumps({"tool_name": "mcp__remi__leer", "session_id": "s9", "tool_input": {"id": "x"}}))
        try:
            with redirect_stdout(io.StringIO()):
                assert hook.main() == 0
        finally:
            sys.stdin = sys.__stdin__
        assert metricas.resumen(7)["aciertos"] == 1


def test_instalador_agrega_y_quita_post_tool_use():
    inst = importlib.import_module("instalar_hook_claude")
    nuevo = inst.transformar({"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo"}]}]}})
    post = nuevo["hooks"]["PostToolUse"]
    assert len(post) == 2 and "hook_post_herramienta.py" in post[1]["hooks"][0]["command"] and "mcp__remi__leer" in post[1]["matcher"]
    assert len(nuevo["hooks"]["SessionStart"]) == 1 and len(nuevo["hooks"]["UserPromptSubmit"]) == 1
    quitado = inst.transformar(nuevo, quitar=True)
    assert quitado["hooks"]["PostToolUse"] == [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo"}]}]
    assert "SessionStart" not in quitado["hooks"]


if __name__ == "__main__":
    fallas = 0
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok", nombre)
            except Exception as error:  # noqa: BLE001
                fallas += 1
                print("FALLA", nombre, type(error).__name__, error)
    sys.exit(1 if fallas else 0)

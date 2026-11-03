"""El agente Editor: valida lo que escribe Claude, publica estilo Jarvis y nunca deja a JC sin mensaje."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("BOVEDA_SIN_LOG", "1")
import editor  # noqa: E402

HOY = date(2026, 11, 3)


def _bd():
    con = sqlite3.connect(":memory:"); con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE items (id TEXT, fuente TEXT, nombre TEXT, nivel TEXT, tema TEXT, titulo TEXT, link TEXT, fecha TEXT, extracto TEXT, "
                "visto_en TEXT, relevancia INTEGER, resumen_es TEXT, tema_ia TEXT, cambia_rumbo INTEGER, verificable TEXT, profundo TEXT, dia TEXT, "
                "similitud REAL, grupo TEXT, corroboracion INTEGER, descartado_por TEXT)")
    textos = ["Google pierde quince por ciento de búsquedas por culpa del modo IA.",
              "IBM publica un armazón abierto para agentes empresariales con reglas.",
              "OpenAI junta las cuotas de ChatGPT y Codex desde diciembre próximo."]
    for i in range(3):
        con.execute("INSERT INTO items (id, fuente, nombre, nivel, tema, tema_ia, titulo, link, relevancia, cambia_rumbo, resumen_es, profundo, dia) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"t{i}", "hn", "Hacker News", "T2", "ia", "ia", f"Título {i}", f"https://x.com/{i}", 3, 1,
                     textos[i], json.dumps({"resumen": f"fondo {i}", "cifras": ["1"]}), HOY.isoformat()))
    con.commit()
    return con


RESPUESTA = json.dumps({"temas": [
    {"id": "t1", "titular": "El armazón pesa más que el modelo: de 30 % a 81 %", "cuerpo": "IBM lo midió.", "para_ti": "Úsalo al diseñar los agentes de INV3RZA.", "accion": "tener en cuenta", "nota": ""},
    {"id": "inventado", "titular": "No existe", "cuerpo": "x", "para_ti": "x", "accion": "hoy"},
    {"id": "t0", "titular": "Algo para hoy", "cuerpo": "Dos frases.", "para_ti": "Cámbialo hoy en tu plan.", "accion": "HOY", "nota": "La cifra no se pudo verificar."}]})


def test_leer_respuesta_valida_ids_y_normaliza():
    import newsletter_notion as nn
    cand = nn.del_dia(_bd(), HOY, mente=Path(tempfile.mkdtemp()))
    temas = editor.leer_respuesta(f"```json\n{RESPUESTA}\n```", cand)
    assert [t["id"] for t in temas] == ["t1", "t0"]
    assert temas[1]["accion"] == "hoy" and temas[1]["nota"] and temas[0]["esencial"] == ["IBM lo midió."] and temas[0]["datos"] == []


def test_corrida_con_editor_publica_y_manda_estilo_jarvis():
    enviados, publicados = [], []
    texto = editor.correr(HOY, claude=lambda s, m: RESPUESTA, publicar=lambda con, temas, hoy: publicados.extend(temas) or len(temas),
                          enviar=lambda t: enviados.append(t) or True, preparar=False, con=_bd())
    assert [t["id"] for t in publicados] == ["t1", "t0"] and enviados == [texto]
    assert "1. El armazón pesa más que el modelo" in texto and "👉 Hoy: Cámbialo hoy en tu plan." in texto and "x.com" not in texto


def test_si_el_editor_falla_sale_la_version_automatica_y_avisa():
    avisos, enviados = [], []
    def falla(s, m):
        raise RuntimeError("límite de uso")
    texto = editor.correr(HOY, claude=falla, publicar=lambda con, temas, hoy: 0, enviar=lambda t: enviados.append(t) or True,
                          avisar=avisos.append, preparar=False, con=_bd())
    assert len(avisos) == 1 and "versión automática" in avisos[0] and enviados and "Google pierde" in texto


def test_encuentra_la_cli_fuera_del_path():
    assert editor.binario_claude() is None or Path(editor.binario_claude()).name == "claude"


if __name__ == "__main__":
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith("test_") and callable(f):
            try:
                f(); print("ok  ", nombre)
            except Exception as exc:  # noqa: BLE001
                import traceback; fallos += 1; print("FALLA", nombre, "→", type(exc).__name__, exc); traceback.print_exc()
    sys.exit(1 if fallos else 0)

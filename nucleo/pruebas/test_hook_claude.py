import importlib.util
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _instalador():
    spec = importlib.util.spec_from_file_location("inst", RAIZ / "scripts" / "instalar_hook_claude.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_el_hook_entrega_json_valido_con_el_estado(tmp_path):
    import os
    (tmp_path / "yo").mkdir()
    (tmp_path / "negocio").mkdir()
    (tmp_path / "yo" / "perfil.md").write_text("---\ntipo: yo\n---\n# Quién es\n- prueba\n", encoding="utf-8")
    (tmp_path / "negocio" / "frentes.md").write_text("---\nactualizado: 2026-10-30\n---\n# Frentes\n- uno\n", encoding="utf-8")
    env = dict(os.environ, REMI_MENTE=str(tmp_path))
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "hook_sesion_inicio.py")], capture_output=True, text=True, timeout=5, env=env)
    assert r.returncode == 0
    datos = json.loads(r.stdout)["hookSpecificOutput"]
    assert datos["hookEventName"] == "SessionStart" and "Hoy es" in datos["additionalContext"]


def test_instalar_conserva_lo_ajeno_es_idempotente_y_se_quita(tmp_path):
    m = _instalador()
    ruta = tmp_path / "settings.json"
    ruta.write_text(json.dumps({"model": "opus", "hooks": {"SessionStart": [{"matcher": "startup", "hooks": [{"type": "command", "command": "echo hola"}]}], "Stop": [{"hooks": []}]}}))
    assert m.main([], ruta) == 0 and "remi" not in ruta.read_text().lower()  # sin --aplicar no toca
    m.main(["--aplicar"], ruta)
    m.main(["--aplicar"], ruta)
    d = json.loads(ruta.read_text())
    assert d["model"] == "opus" and "Stop" in d["hooks"]
    assert len(d["hooks"]["SessionStart"]) == 2 and ruta.with_suffix(".json.bak-remi").exists()
    assert len(d["hooks"]["UserPromptSubmit"]) == 1 and "hook_prompt_boveda" in d["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    m.main(["--quitar"], ruta)
    d = json.loads(ruta.read_text())
    assert d["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "echo hola" and len(d["hooks"]["SessionStart"]) == 1
    assert "UserPromptSubmit" not in d["hooks"]


def test_hook_prompt_responde_desde_la_boveda_y_calla_si_no_hay_nada(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("hp", RAIZ / "scripts" / "hook_prompt_boveda.py")
    hp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hp)
    (tmp_path / "03_oro" / "repos").mkdir(parents=True)
    (tmp_path / "03_oro" / "repos" / "adbar-trafilatura.md").write_text("---\nveredicto: adoptar\n---\n")
    buscar = lambda q, n=4: [("03_oro/ai-tools/nota.md", "trafilatura saca el texto limpio de blogs"), ("01_raw/otra.md", "nada que ver")] if "trafilatura" in q else []
    ctx = hp.contexto("¿sirve trafilatura para leer blogs? mira https://github.com/adbar/trafilatura", buscar, tmp_path)
    assert "adbar/trafilatura: ya tiene ficha" in ctx and "veredicto: adoptar" in ctx and "nota.md" in ctx and ctx.startswith("LA BÓVEDA")
    assert "otra.md" not in ctx  # un hallazgo con una sola palabra suelta no entra
    assert hp.contexto("hola, ¿cómo vas?", buscar, tmp_path) is None
    q = hp.consulta_de("quiero que revises el repo de trafilatura para los blogs https://github.com/adbar/trafilatura")
    assert "trafilatura" in q and "blogs" in q and "quiero" not in q and "https" not in q and "github.com" not in q

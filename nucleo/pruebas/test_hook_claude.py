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


def test_el_hook_entrega_json_valido_con_el_estado():
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "hook_sesion_inicio.py")], capture_output=True, text=True, timeout=5)
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
    m.main(["--quitar"], ruta)
    d = json.loads(ruta.read_text())
    assert d["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "echo hola" and len(d["hooks"]["SessionStart"]) == 1

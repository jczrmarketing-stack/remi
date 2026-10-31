"""La app de escritorio gana el servidor remi, pierde memoria y no pierde los demás."""
import json
import os
import subprocess
from pathlib import Path

INSTALAR = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "instalar-mcp.py"


def test_suma_remi_saca_memoria_y_deja_el_calendario(tmp_path: Path) -> None:
    destino = tmp_path / "claude_desktop_config.json"
    destino.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "malik-calendario": {"command": "node", "args": ["mcp-calendario.mts"]},
                    "memoria": {"command": "uv", "args": ["memoria_mcp.py"]},
                },
                "preferences": {"sidebarMode": "chat"},
            }
        )
    )
    subprocess.run(
        ["python3", str(INSTALAR)],
        check=True,
        env={**os.environ, "REMI_DESKTOP_CONFIG": str(destino), "REMI_SIN_CLAUDE": "1"},
        timeout=60,
    )
    datos = json.loads(destino.read_text())
    assert datos["preferences"]["sidebarMode"] == "chat"
    assert datos["mcpServers"]["malik-calendario"]["command"] == "node"
    remi = datos["mcpServers"]["remi"]
    assert remi["command"].endswith("/uv")
    assert "remi_mcp.py" in remi["args"]
    assert "memoria" not in datos["mcpServers"]
    subprocess.run(
        ["python3", str(INSTALAR)],
        check=True,
        env={**os.environ, "REMI_DESKTOP_CONFIG": str(destino), "REMI_SIN_CLAUDE": "1"},
        timeout=60,
    )
    otra = json.loads(destino.read_text())
    assert list(otra["mcpServers"]).count("remi") == 1 and "memoria" not in otra["mcpServers"]

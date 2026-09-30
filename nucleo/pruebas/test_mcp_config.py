"""La app de escritorio gana el servidor memoria sin perder los que ya tenía."""
import json
import os
import subprocess
from pathlib import Path

INSTALAR = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "instalar-mcp.py"


def test_suma_memoria_y_deja_el_calendario(tmp_path: Path) -> None:
    destino = tmp_path / "claude_desktop_config.json"
    destino.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "malik-calendario": {"command": "node", "args": ["mcp-calendario.mts"]}
                },
                "preferences": {"sidebarMode": "chat"},
            }
        )
    )
    subprocess.run(
        ["python3", str(INSTALAR)],
        check=True,
        env={**os.environ, "REMI_DESKTOP_CONFIG": str(destino), "REMI_SIN_CLAUDE": "1"},
    )
    datos = json.loads(destino.read_text())
    assert datos["preferences"]["sidebarMode"] == "chat"
    assert datos["mcpServers"]["malik-calendario"]["command"] == "node"
    memoria = datos["mcpServers"]["memoria"]
    assert memoria["command"].endswith("/uv")
    assert "memoria_mcp.py" in memoria["args"]
    subprocess.run(
        ["python3", str(INSTALAR)],
        check=True,
        env={**os.environ, "REMI_DESKTOP_CONFIG": str(destino), "REMI_SIN_CLAUDE": "1"},
    )
    otra = json.loads(destino.read_text())
    assert list(otra["mcpServers"]).count("memoria") == 1

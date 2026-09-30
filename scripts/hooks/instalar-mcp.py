#!/usr/bin/env python3
"""Registra el MCP de memoria en Claude Code (scope user) y en la app de escritorio.

No saca los servidores que ya están. Idempotente.
REMI_DESKTOP_CONFIG cambia el json de la app (las pruebas).
REMI_SIN_CLAUDE=1 no llama a la CLI.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

UV = Path.home() / ".local" / "bin" / "uv"
NUCLEO = Path.home() / "proyectos" / "remi" / "nucleo"
DESKTOP = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
ARGS = ["run", "--directory", str(NUCLEO), "python", "memoria_mcp.py"]


def entrada() -> dict[str, object]:
    return {"command": str(UV), "args": ARGS}


def configurar_escritorio(ruta: Path) -> None:
    datos: dict[str, object] = {}
    if ruta.is_file():
        cargado = json.loads(ruta.read_text())
        if isinstance(cargado, dict):
            datos = cargado
    servidores = datos.get("mcpServers")
    if not isinstance(servidores, dict):
        servidores = {}
        datos["mcpServers"] = servidores
    servidores["memoria"] = entrada()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")


def registrar_claude_code() -> None:
    if os.environ.get("REMI_SIN_CLAUDE") == "1":
        return
    subprocess.run(
        ["claude", "mcp", "remove", "--scope", "user", "memoria"],
        check=False,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["claude", "mcp", "add", "--scope", "user", "memoria", "--", str(UV), *ARGS],
        check=True,
    )


def main() -> None:
    registrar_claude_code()
    destino = Path(os.environ.get("REMI_DESKTOP_CONFIG") or DESKTOP)
    configurar_escritorio(destino)
    print(f"memoria en Claude Code (user) y en {destino}")


if __name__ == "__main__":
    main()

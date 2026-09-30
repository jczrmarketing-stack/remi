#!/usr/bin/env python3
"""Suma SessionStart y SessionEnd al settings.json de Claude Code.

No pisa lo que ya hay: el PreToolUse de malik sigue. Idempotente.
REMI_CLAUDE_SETTINGS cambia el archivo (las pruebas).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

COMANDO = 'python3 "$HOME/proyectos/remi/scripts/hooks/claude-sesion.py"'


def _ya_esta(lista: list[object]) -> bool:
    for grupo in lista:
        if not isinstance(grupo, dict):
            continue
        ganchos = grupo.get("hooks")
        if not isinstance(ganchos, list):
            continue
        for gancho in ganchos:
            if isinstance(gancho, dict) and gancho.get("command") == COMANDO:
                return True
    return False


def _grupo(timeout: int) -> dict[str, object]:
    return {
        "hooks": [
            {"type": "command", "command": COMANDO, "timeout": timeout},
        ]
    }


def instalar(ruta: Path) -> None:
    datos: dict[str, object] = {}
    if ruta.is_file():
        cargado = json.loads(ruta.read_text())
        if isinstance(cargado, dict):
            datos = cargado
    hooks = datos.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
        datos["hooks"] = hooks
    for nombre, timeout in (("SessionStart", 8), ("SessionEnd", 5)):
        lista = hooks.get(nombre)
        if not isinstance(lista, list):
            lista = []
            hooks[nombre] = lista
        if _ya_esta(lista):
            continue
        lista.append(_grupo(timeout))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    destino = Path(
        os.environ.get("REMI_CLAUDE_SETTINGS")
        or Path.home() / ".claude" / "settings.json"
    )
    instalar(destino)
    print(f"hooks de sesión en {destino}")


if __name__ == "__main__":
    main()

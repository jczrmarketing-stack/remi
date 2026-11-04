"""El Portero de la fábrica (Bloque 1): hook PreToolUse de cada agente, 0 tokens.

Lo carga `--settings fabrica/portero/settings.json`. Lee el evento del hook por
stdin y, si la acción está prohibida, responde `permissionDecision: deny` con
el motivo. Los agentes no hacen commit ni push (eso lo hace la línea), no
borran, no despliegan y no escriben fuera del worktree de su pedido
(`FABRICA_WORKTREE`). Sin esa variable, todo lo que escribe se niega.
Solo stdlib: corre con el python3 del sistema.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

ESCRIBEN = ("Edit", "Write", "MultiEdit", "NotebookEdit")

PROHIBIDOS = (
    (re.compile(r"\bgit\s+(push|commit|merge|rebase|tag)\b"), "La línea hace commit y push, no el agente."),
    (re.compile(r"\bgit\s+(branch\s+-D|reset\s+--hard|clean\b|checkout\s+(main|master)\b|switch\b|worktree\b)"),
     "No se tocan ramas ni se descarta trabajo."),
    (re.compile(r"--force\b|\s-f\s+origin\b"), "Nada a la fuerza."),
    (re.compile(r"\brm\s+(-[a-zA-Z]*[rR]|--recursive)"), "No se borran carpetas."),
    (re.compile(r"\b(deploy|publish)\b|\bgh\s+(pr|release|repo)\b"), "No se despliega ni se publica."),
    (re.compile(r"\bsudo\b"), "Sin sudo."),
)


def _dentro(ruta: str, base: Path, worktree: Path) -> bool:
    destino = Path(ruta).expanduser()
    if not destino.is_absolute():
        destino = base / destino
    return destino.resolve().is_relative_to(worktree.resolve())


def _rutas_que_toca(comando: str) -> list[str]:
    """Destinos de `cd` y de redirecciones `>`/`>>`."""
    try:
        partes = shlex.split(comando, posix=True)
    except ValueError:
        return [comando]
    rutas = []
    for i, parte in enumerate(partes):
        if parte in ("cd", ">", ">>") and i + 1 < len(partes):
            rutas.append(partes[i + 1])
        elif parte.startswith(">") and len(parte.lstrip(">")) > 0:
            rutas.append(parte.lstrip(">"))
    return rutas


def decidir(evento: dict, worktree: Path) -> str | None:
    """El motivo si se niega; None si pasa."""
    herramienta = evento.get("tool_name", "")
    entrada = evento.get("tool_input") or {}
    base = Path(evento.get("cwd") or worktree)
    if herramienta == "Bash":
        comando = str(entrada.get("command", ""))
        for patron, motivo in PROHIBIDOS:
            if patron.search(comando):
                return motivo
        for ruta in _rutas_que_toca(comando):
            if not _dentro(ruta, base, worktree):
                return f"Fuera del worktree del pedido: {ruta}"
        return None
    if herramienta in ESCRIBEN:
        ruta = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
        if not ruta or not _dentro(ruta, base, worktree):
            return f"Solo se escribe dentro del worktree del pedido: {ruta or '(sin ruta)'}"
    return None


def main() -> int:
    try:
        evento = json.load(sys.stdin)
    except ValueError:
        evento = {}
    worktree = os.environ.get("FABRICA_WORKTREE")
    if worktree:
        motivo = decidir(evento, Path(worktree))
    elif evento.get("tool_name") in (*ESCRIBEN, "Bash"):
        motivo = "Sin FABRICA_WORKTREE el Portero no deja escribir ni ejecutar."
    else:
        motivo = None
    if motivo:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"Portero: {motivo}"}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

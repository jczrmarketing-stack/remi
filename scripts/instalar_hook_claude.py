#!/usr/bin/env python3
"""Pone los hooks de Remi en ~/.claude/settings.json: inicio de sesión (estado vivo y mapas),
prompt (fichas de la mente) y post-herramienta (métricas de acierto).

Sin argumentos solo MUESTRA el diff y no toca nada.
Con --aplicar guarda una copia (.bak-remi) y escribe. Idempotente.
Con --quitar saca solo lo que puso Remi.
"""
import json
import shutil
import sys
from difflib import unified_diff
from pathlib import Path

MARCA = "hook_sesion_inicio.py"
MARCA_PROMPT = "hook_prompt_boveda.py"
MARCA_POST = "hook_post_herramienta.py"
MARCAS = (MARCA, MARCA_PROMPT, MARCA_POST)
AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI / MARCA
SCRIPT_PROMPT = AQUI / MARCA_PROMPT
SCRIPT_POST = AQUI / MARCA_POST
EVENTOS = ("startup", "clear", "compact")


def _entrada() -> dict:
    return {"matcher": "|".join(EVENTOS), "hooks": [{"type": "command", "command": f"python3 {SCRIPT}", "timeout": 5}]}


def _entrada_prompt() -> dict:
    # Sin matcher: cada mensaje pasa por la bóveda (FTS local, milisegundos).
    return {"hooks": [{"type": "command", "command": f"python3 {SCRIPT_PROMPT}", "timeout": 5}]}


def _entrada_post() -> dict:
    # Solo las herramientas que dicen si la mente sirvió: leer/preguntar del MCP y la web.
    return {"matcher": "WebSearch|WebFetch|mcp__remi__leer|mcp__remi__preguntar",
            "hooks": [{"type": "command", "command": f"python3 {SCRIPT_POST}", "timeout": 5}]}


def _sin_remi(lista: list) -> list:
    return [e for e in lista if not any(any(m in h.get("command", "") for m in MARCAS) for h in e.get("hooks", []))]


def transformar(ajustes: dict, quitar: bool = False) -> dict:
    nuevo = json.loads(json.dumps(ajustes))
    hooks = nuevo.setdefault("hooks", {})
    for evento, nueva in (("SessionStart", _entrada()), ("UserPromptSubmit", _entrada_prompt()), ("PostToolUse", _entrada_post())):
        resto = _sin_remi(hooks.get(evento, []))
        if quitar:
            if resto:
                hooks[evento] = resto
            else:
                hooks.pop(evento, None)
        else:
            hooks[evento] = resto + [nueva]
    if not hooks:
        nuevo.pop("hooks", None)
    return nuevo


def main(argv: list[str], ruta: Path | None = None) -> int:
    ruta = ruta or Path.home() / ".claude" / "settings.json"
    actual = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    nuevo = transformar(actual, quitar="--quitar" in argv)
    a, b = json.dumps(actual, indent=2, ensure_ascii=False), json.dumps(nuevo, indent=2, ensure_ascii=False)
    if a == b:
        print("Sin cambios: ya estaba así.")
        return 0
    print("".join(unified_diff(a.splitlines(True), b.splitlines(True), "antes", "después")))
    if "--aplicar" not in argv and "--quitar" not in argv:
        print("\nNo toqué nada. Para aplicar: python3 scripts/instalar_hook_claude.py --aplicar")
        return 0
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        shutil.copy2(ruta, ruta.with_suffix(".json.bak-remi"))
    ruta.write_text(b + "\n", encoding="utf-8")
    print(f"\nListo. Copia en {ruta.with_suffix('.json.bak-remi')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

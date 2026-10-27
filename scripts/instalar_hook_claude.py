#!/usr/bin/env python3
"""Pone el hook de inicio de sesión de Remi en ~/.claude/settings.json.

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
SCRIPT = Path(__file__).resolve().parent / MARCA
EVENTOS = ("startup", "clear", "compact")


def _entrada() -> dict:
    return {"matcher": "|".join(EVENTOS), "hooks": [{"type": "command", "command": f"python3 {SCRIPT}", "timeout": 5}]}


def _sin_remi(lista: list) -> list:
    return [e for e in lista if not any(MARCA in h.get("command", "") for h in e.get("hooks", []))]


def transformar(ajustes: dict, quitar: bool = False) -> dict:
    nuevo = json.loads(json.dumps(ajustes))
    hooks = nuevo.setdefault("hooks", {})
    resto = _sin_remi(hooks.get("SessionStart", []))
    if quitar:
        if resto:
            hooks["SessionStart"] = resto
        else:
            hooks.pop("SessionStart", None)
        if not hooks:
            nuevo.pop("hooks", None)
    else:
        hooks["SessionStart"] = resto + [_entrada()]
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

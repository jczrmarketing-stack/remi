#!/usr/bin/env python3
"""Hook SessionStart de Claude Code: mete el estado vivo de Juan Camilo en el
contexto de cualquier sesión. Solo stdlib, sin red, sin modelo. Si algo falla
no imprime nada y sale 0: una sesión nunca se rompe por esto.
"""
import json
import sys
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))
    import vida

    texto = vida.construir_estado()
    # Mapas (idea de Graphify: un mapa precalculado antes de explorar). Solo el
    # puntero, nunca el contenido: se abre si hace falta.
    try:
        entrada = json.loads(sys.stdin.read() or "{}")
    except Exception:
        entrada = {}
    cwd = Path(str(entrada.get("cwd") or "")).resolve() if entrada.get("cwd") else None
    repo = Path(__file__).resolve().parent.parent
    mapas = []
    if cwd and (cwd == repo or repo in cwd.parents) and (repo / "docs" / "MAPA.md").exists():
        mapas.append(f"Mapa del repo (una línea por archivo, léelo antes de grep/glob): {repo / 'docs' / 'MAPA.md'}")
    if (vida.MENTE / "MAPA.md").exists():
        mapas.append(f"Mapa de la mente: {vida.MENTE / 'MAPA.md'}. Antes de buscar en la web, usa `preguntar` del MCP remi; al terminar, `anotar` lo investigado con fuentes.")
    if mapas:
        texto += "\n\n" + "\n".join(mapas)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "ESTADO VIVO DE JUAN CAMILO (Remi)\n\n" + texto}}, ensure_ascii=False))
except Exception:
    pass
sys.exit(0)

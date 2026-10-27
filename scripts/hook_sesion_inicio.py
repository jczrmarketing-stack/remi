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
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "ESTADO VIVO DE JUAN CAMILO (Remi)\n\n" + texto}}, ensure_ascii=False))
except Exception:
    pass
sys.exit(0)

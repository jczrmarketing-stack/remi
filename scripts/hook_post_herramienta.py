#!/usr/bin/env python3
"""Hook PostToolUse de Claude Code: mide si la mente sirvió.

- `mcp__remi__leer`      → acierto: Claude usó una ficha que recibió.
- `mcp__remi__preguntar` → profundizó (evento).
- `WebSearch`/`WebFetch` → buscó en la web igual: la mente no bastó (si hubo fichas antes).

No imprime nada, no bloquea nada, nunca falla hacia afuera.
"""
import json
import sys
from pathlib import Path


def main() -> int:
    try:
        datos = json.load(sys.stdin)
        herramienta = str(datos.get("tool_name") or "")
        sesion = str(datos.get("session_id") or "-")
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))
        import metricas

        if herramienta.endswith("remi__leer"):
            metricas.marcar(sesion, "acierto", herramienta)
        elif herramienta.endswith("remi__preguntar"):
            metricas.marcar(sesion, "profundizo", herramienta)
        elif herramienta in {"WebSearch", "WebFetch"}:
            entrada = datos.get("tool_input") or {}
            metricas.marcar(sesion, "web", str(entrada.get("query") or entrada.get("url") or herramienta))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

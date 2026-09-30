#!/usr/bin/env python3
"""SessionStart y SessionEnd de Claude Code, hacia el núcleo de Remi.

Al abrir, imprime el contexto del proyecto para que Claude lo reciba.
Al cerrar, manda la sesión. Si el núcleo no está, no imprime nada y sale 0:
abrir o cerrar Claude no depende de Remi.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _post(tipo: str, ruta: str, datos: dict[str, object]) -> dict[str, object] | None:
    base = os.environ.get("REMI_NUCLEO_URL", "http://127.0.0.1:4400").rstrip("/")
    url = base if base.endswith("/evento") else f"{base}/evento"
    cuerpo = json.dumps({"tipo": tipo, "ruta": ruta, "datos": datos}, ensure_ascii=False).encode()
    pedido = urllib.request.Request(
        url, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(pedido, timeout=2) as respuesta:
            crudo = respuesta.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    try:
        datos_respuesta = json.loads(crudo) if crudo.strip() else {}
    except json.JSONDecodeError:
        return None
    return datos_respuesta if isinstance(datos_respuesta, dict) else None


def main() -> int:
    try:
        crudo = sys.stdin.read()
        evento = json.loads(crudo) if crudo.strip() else {}
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(evento, dict):
        return 0
    nombre = str(evento.get("hook_event_name") or "")
    ruta = str(evento.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "")
    datos = {
        "session_id": str(evento.get("session_id") or ""),
        "transcript_path": str(evento.get("transcript_path") or ""),
        "source": str(evento.get("source") or ""),
    }
    if nombre == "SessionStart":
        respuesta = _post("sesion_inicio", ruta, datos)
        contexto = (respuesta or {}).get("contexto")
        if isinstance(contexto, str) and contexto.strip():
            json.dump(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": contexto.strip(),
                    }
                },
                sys.stdout,
                ensure_ascii=False,
            )
            sys.stdout.write("\n")
        return 0
    if nombre == "SessionEnd":
        _post("sesion_fin", ruta, datos)
        return 0
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)

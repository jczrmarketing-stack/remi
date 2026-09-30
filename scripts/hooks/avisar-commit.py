#!/usr/bin/env python3
"""Avisa al núcleo que hubo un commit. Si no está, se calla.

Corre después del commit, así que no puede deshacerlo. Igual sale siempre
con 0: un núcleo apagado no es un commit roto.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], text=True, stderr=subprocess.DEVNULL
    )


def main() -> int:
    try:
        repo = _git("rev-parse", "--show-toplevel").strip()
        rama = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
        mensaje = _git("log", "-1", "--pretty=%B").strip()
        crudo = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD")
        archivos = [linea for linea in crudo.splitlines() if linea.strip()]
    except (subprocess.CalledProcessError, OSError):
        return 0

    base = os.environ.get("REMI_NUCLEO_URL", "http://127.0.0.1:4400").rstrip("/")
    url = base if base.endswith("/evento") else f"{base}/evento"
    cuerpo = json.dumps(
        {
            "tipo": "commit",
            "ruta": repo,
            "datos": {
                "repo": repo,
                "rama": rama,
                "mensaje": mensaje,
                "archivos": archivos,
            },
        },
        ensure_ascii=False,
    ).encode()
    pedido = urllib.request.Request(
        url,
        data=cuerpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=2) as respuesta:
            respuesta.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)

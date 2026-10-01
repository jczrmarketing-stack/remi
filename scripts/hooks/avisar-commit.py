#!/usr/bin/env python3
"""Avisa al núcleo que hubo un commit. Si no está, se calla.

Corre después del commit, así que no puede deshacerlo. Igual sale siempre
con 0: un núcleo apagado no es un commit roto.

Nunca avisa por un commit de prueba (1-oct): ni con REMI_SIN_HOOKS=1 puesto
a mano, ni si el repo vive bajo una carpeta temporal de pytest — aunque el
.gitconfig de pruebas fallara en copiar este hook, esto es la segunda
guarda. Sin dependencias de nucleo/ a propósito: este archivo corre con
cualquier Python del sistema, en cualquier repo de la máquina.

REMI_PRUEBA_FORZAR_AVISO=1 salta la guarda de carpeta — solo para que
test_gancho_git.py pueda probar el aviso de verdad sin que el repo de
fixture (bajo tmp_path, o sea bajo una carpeta de pruebas de pytest) quede
atrapado por la misma guarda que está probando otra cosa.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

_CARPETAS_DE_PRUEBAS = ("/private/var/folders", "/private/tmp", "/tmp")


def _es_repo_de_pruebas(repo: str) -> bool:
    if "pytest-of-" in repo:
        return True
    tmpdir = os.environ.get("TMPDIR", "").rstrip("/")
    if tmpdir and (repo == tmpdir or repo.startswith(tmpdir + "/")):
        return True
    return any(repo == base or repo.startswith(base + "/") for base in _CARPETAS_DE_PRUEBAS)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], text=True, stderr=subprocess.DEVNULL
    )


def main() -> int:
    if os.environ.get("REMI_SIN_HOOKS") == "1":
        return 0
    try:
        repo = _git("rev-parse", "--show-toplevel").strip()
        rama = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
        mensaje = _git("log", "-1", "--pretty=%B").strip()
        crudo = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD")
        archivos = [linea for linea in crudo.splitlines() if linea.strip()]
    except (subprocess.CalledProcessError, OSError):
        return 0
    if os.environ.get("REMI_PRUEBA_FORZAR_AVISO") != "1" and _es_repo_de_pruebas(repo):
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

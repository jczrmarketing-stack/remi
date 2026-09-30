"""El gancho global avisa el commit y deja correr el del repo."""
from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
AVISAR = RAIZ / "scripts" / "hooks" / "avisar-commit.py"
GANCHO = RAIZ / "scripts" / "hooks" / "git-gancho"
INSTALAR = RAIZ / "scripts" / "hooks" / "instalar-git.sh"


def _repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    ambiente = {**os.environ, "GIT_CONFIG_COUNT": "0"}
    correr = ["git", "-c", "core.hooksPath=/dev/null"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run([*correr, "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run([*correr, "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "a.txt").write_text("hola\n")
    subprocess.run([*correr, "add", "a.txt"], cwd=repo, check=True)
    subprocess.run([*correr, "commit", "-q", "-m", "el mosaico"], cwd=repo, check=True)
    return repo


class _Anota(BaseHTTPRequestHandler):
    cuerpo: bytes = b""
    veces: int = 0

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length", "0"))
        type(self).cuerpo = self.rfile.read(n)
        type(self).veces += 1
        self.send_response(200)
        self.end_headers()

    def log_message(self, formato: str, *args: object) -> None:
        return


def _servidor() -> tuple[ThreadingHTTPServer, str]:
    _Anota.cuerpo = b""
    _Anota.veces = 0
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Anota)
    import threading

    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    puerto = servidor.server_address[1]
    return servidor, f"http://127.0.0.1:{puerto}"


def test_un_commit_avisa_repo_rama_mensaje_y_archivos(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    servidor, url = _servidor()
    try:
        hecho = subprocess.run(
            ["python3", str(AVISAR)],
            cwd=repo,
            env={**os.environ, "REMI_NUCLEO_URL": url},
            check=False,
        )
    finally:
        servidor.shutdown()
    assert hecho.returncode == 0
    cuerpo = json.loads(_Anota.cuerpo)
    assert cuerpo["tipo"] == "commit"
    assert cuerpo["ruta"] == str(repo)
    assert cuerpo["datos"]["rama"] in {"main", "master"}
    assert cuerpo["datos"]["mensaje"] == "el mosaico"
    assert cuerpo["datos"]["archivos"] == ["a.txt"]
    assert cuerpo["datos"]["repo"] == str(repo)


def test_nucleo_apagado_no_frena(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    hecho = subprocess.run(
        ["python3", str(AVISAR)],
        cwd=repo,
        env={**os.environ, "REMI_NUCLEO_URL": "http://127.0.0.1:9"},
        check=False,
    )
    assert hecho.returncode == 0


def test_encadena_el_gancho_local_y_no_se_llama_a_si_mismo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    marca = tmp_path / "marca"
    local = repo / ".git" / "hooks" / "post-commit"
    local.write_text(f'#!/bin/sh\necho local >> "{marca}"\n')
    local.chmod(0o755)
    enlace = tmp_path / "post-commit"
    enlace.symlink_to(GANCHO)
    servidor, url = _servidor()
    try:
        hecho = subprocess.run(
            [str(enlace)],
            cwd=repo,
            env={**os.environ, "REMI_NUCLEO_URL": url},
            check=False,
            timeout=5,
        )
    finally:
        servidor.shutdown()
    assert hecho.returncode == 0
    assert marca.read_text().strip() == "local"
    assert _Anota.veces == 1

    # El gancho del repo ES este mismo archivo: no hay bucle.
    local.unlink()
    local.symlink_to(GANCHO)
    _Anota.veces = 0
    servidor2, url2 = _servidor()
    try:
        hecho2 = subprocess.run(
            [str(enlace)],
            cwd=repo,
            env={**os.environ, "REMI_NUCLEO_URL": url2},
            check=False,
            timeout=5,
        )
    finally:
        servidor2.shutdown()
    assert hecho2.returncode == 0
    assert _Anota.veces == 1


def test_otro_nombre_solo_encadena(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    marca = tmp_path / "pre"
    local = repo / ".git" / "hooks" / "pre-commit"
    local.write_text(f'#!/bin/sh\necho pre >> "{marca}"\n')
    local.chmod(0o755)
    enlace = tmp_path / "pre-commit"
    enlace.symlink_to(GANCHO)
    servidor, url = _servidor()
    try:
        subprocess.run(
            [str(enlace)],
            cwd=repo,
            env={**os.environ, "REMI_NUCLEO_URL": url},
            check=False,
            timeout=5,
        )
    finally:
        servidor.shutdown()
    assert marca.read_text().strip() == "pre"
    assert _Anota.veces == 0


def test_instalar_enlaza_sin_tocar_la_config(tmp_path: Path) -> None:
    destino = tmp_path / "hooks"
    subprocess.run(
        ["sh", str(INSTALAR)],
        check=True,
        env={
            **os.environ,
            "REMI_HOOKS_DEST": str(destino),
            "REMI_NO_CONFIGURAR_GIT": "1",
        },
    )
    enlace = destino / "post-commit"
    assert enlace.is_symlink()
    assert enlace.resolve() == GANCHO.resolve()
    assert (destino / "pre-push").resolve() == GANCHO.resolve()

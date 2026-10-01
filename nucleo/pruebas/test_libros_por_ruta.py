"""T1 punto 3: una carpeta que es un worktree de git resuelve al repo
principal — un commit hecho en el worktree cae en el mismo libro."""
import subprocess

import libros

LIBRO = """---
titulo: Remi
tema: remi
resumen: El asistente.
ruta: {ruta}
---

Cuerpo.
"""


def _git(args: list[str], cwd) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _repo_con_worktree(tmp_path):
    principal = tmp_path / "repo"
    principal.mkdir()
    _git(["init", "-q"], principal)
    _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "--allow-empty", "-q", "-m", "inicial"], principal)
    worktree = tmp_path / "repo-worktree"
    _git(["worktree", "add", "-q", str(worktree), "-b", "f-prueba"], principal)
    return principal, worktree


def _boveda(tmp_path, ruta_libro):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "remi.md").write_text(LIBRO.format(ruta=ruta_libro))
    return carpeta


def test_un_commit_en_el_worktree_cae_en_el_libro_del_repo_principal(tmp_path, monkeypatch):
    principal, worktree = _repo_con_worktree(tmp_path)
    boveda = _boveda(tmp_path, str(principal))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(boveda))

    carpeta_dentro = worktree / "nucleo"
    carpeta_dentro.mkdir()

    libro = libros.por_ruta(str(carpeta_dentro))

    assert libro is not None and libro.tema == "remi"


def test_una_carpeta_sin_worktree_no_cambia(tmp_path, monkeypatch):
    boveda = _boveda(tmp_path, str(tmp_path / "otra-cosa"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(boveda))

    assert libros.por_ruta(str(tmp_path)) is None

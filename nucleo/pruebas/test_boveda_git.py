"""La bóveda con git: cada escritura de Remi queda con revert real.

Incidente del 30-sep (docs/BITACORA.md): un pisón sin respaldo perdió texto
real porque la bóveda no tenía git. Estas pruebas corren git de verdad
(subprocess), no lo simulan.
"""
import subprocess

import boveda_git


def _git(carpeta, *args):
    return subprocess.run(
        ["git", "-C", str(carpeta), *args],
        capture_output=True, text=True, check=True,
    )


def _preparar_repo(tmp_path, monkeypatch):
    boveda = tmp_path / "boveda"
    (boveda / "proyectos").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(boveda)], check=True)
    subprocess.run(["git", "-C", str(boveda), "config", "user.email", "remi@local"], check=True)
    subprocess.run(["git", "-C", str(boveda), "config", "user.name", "Remi"], check=True)
    (boveda / "proyectos" / "malik.md").write_text("contenido inicial\n")
    subprocess.run(["git", "-C", str(boveda), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(boveda), "commit", "-q", "-m", "inicial"], check=True)
    monkeypatch.setattr(boveda_git.libros, "carpeta", lambda: boveda / "proyectos")
    return boveda


def test_snapshot_antes_y_despues_dejan_dos_commits_reales(tmp_path, monkeypatch) -> None:
    boveda = _preparar_repo(tmp_path, monkeypatch)

    boveda_git.snapshot_antes("el Estado de malik.md")
    (boveda / "proyectos" / "malik.md").write_text("contenido pisado por Remi\n")
    boveda_git.snapshot_despues("bóveda: Estado de malik.md actualizado por commit de prueba")

    log = _git(boveda, "log", "--oneline").stdout.strip().splitlines()
    # inicial + snapshot-antes (nada que commitear todavía) + snapshot-después
    assert any("Estado de malik.md actualizado" in linea for linea in log)
    diff = _git(boveda, "show", "HEAD", "--", "proyectos/malik.md").stdout
    assert "contenido pisado por Remi" in diff

    # revert real: el pisón se puede deshacer
    _git(boveda, "revert", "--no-edit", "HEAD")
    assert (boveda / "proyectos" / "malik.md").read_text() == "contenido inicial\n"


def test_snapshot_antes_solo_commitea_si_hay_algo_pendiente(tmp_path, monkeypatch) -> None:
    boveda = _preparar_repo(tmp_path, monkeypatch)
    antes = _git(boveda, "log", "--oneline").stdout

    boveda_git.snapshot_antes("nada que tocar todavía")

    despues = _git(boveda, "log", "--oneline").stdout
    assert antes == despues  # sin cambios pendientes, no hay commit vacío


def test_sin_repo_git_no_rompe_nada(tmp_path, monkeypatch) -> None:
    boveda = tmp_path / "sin-git"
    (boveda / "proyectos").mkdir(parents=True)
    monkeypatch.setattr(boveda_git.libros, "carpeta", lambda: boveda / "proyectos")

    boveda_git.snapshot_antes("algo")
    boveda_git.snapshot_despues("algo más")  # no debe levantar ninguna excepción


def test_una_prueba_que_intenta_commitear_la_boveda_real_revienta(monkeypatch):
    """F3.5: la suite falla en rojo si una prueba llega al git de remi-mente."""
    import pytest

    import boveda_git

    monkeypatch.setenv("REMI_CONOCIMIENTO", str(boveda_git.BOVEDA_REAL / "proyectos"))
    with pytest.raises(RuntimeError, match="una prueba intentó commitear la bóveda real"):
        boveda_git.snapshot_antes("algo")

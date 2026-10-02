"""T8.5: un commit que toca docs/BITACORA.md de un repo con libro deja la
entrada nueva como episodio."""
import importlib
import subprocess
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_ESTADO", "0")
    for nombre in ("servidor", "db", "trabajo", "libros", "episodios"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _repo_con_bitacora(tmp_path):
    repo = tmp_path / "upvisuals"
    repo.mkdir()
    (repo / "docs").mkdir()
    (repo / "docs" / "BITACORA.md").write_text("# Bitácora\n\n")
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "inicial")
    (repo / "docs" / "BITACORA.md").write_text(
        "# Bitácora\n\n## Se arregló el webhook del 401\n\n- La causa era el token vencido.\n\n"
    )
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "docs: bitacora")
    return repo


def _libro(tmp_path, nombre, cuerpo):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_text(cuerpo)


def test_el_commit_que_toca_bitacora_deja_episodio(tmp_path, monkeypatch):
    repo = _repo_con_bitacora(tmp_path)
    _libro(
        tmp_path, "upvisuals.md",
        f"---\ntitulo: UpVisuals\ntema: upvisuals\nresumen: r.\nruta: {repo}\n---\n",
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/evento",
        json={
            "tipo": "commit",
            "ruta": str(repo),
            "datos": {"mensaje": "docs: bitacora", "archivos": ["docs/BITACORA.md"]},
        },
    )

    assert respuesta.status_code == 200
    episodios = list((tmp_path / "boveda" / "episodios").glob("*bitacora*.md"))
    assert len(episodios) == 1
    texto = episodios[0].read_text()
    assert "fuente: bitacora" in texto
    assert "webhook" in texto.lower()


def test_un_commit_que_no_toca_bitacora_no_deja_episodio_de_bitacora(tmp_path, monkeypatch):
    repo = _repo_con_bitacora(tmp_path)
    _libro(
        tmp_path, "upvisuals.md",
        f"---\ntitulo: UpVisuals\ntema: upvisuals\nresumen: r.\nruta: {repo}\n---\n",
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "fix: x", "archivos": ["x.py"]}},
    )

    boveda_episodios = tmp_path / "boveda" / "episodios"
    assert not boveda_episodios.exists() or list(boveda_episodios.glob("*.md")) == []

from pathlib import Path
"""POST /evento: la carpeta elige el libro. Sin libro, una nota en la Bandeja."""
import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    # Este archivo prueba a qué libro cae el evento, no la redacción del Estado.
    monkeypatch.setenv("REMI_ESTADO", "0")
    for nombre in ("servidor", "db", "trabajo", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _libro(tmp_path, nombre, cuerpo):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_text(cuerpo)


def test_un_commit_en_la_carpeta_cae_en_su_libro(tmp_path, monkeypatch):
    repo = tmp_path / "malik"
    (repo / "src").mkdir(parents=True)
    _libro(
        tmp_path,
        "malik.md",
        f"---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas.\nruta: {repo}\n---\n",
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo / "src"), "datos": {"mensaje": "el mosaico"}},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["proyecto"] == "malik"
    assert respuesta.json()["anotado"] is False


def test_sin_ficha_se_detecta_pero_no_crea_ninguna_idea(tmp_path, monkeypatch):
    """T8: «proyecto sin ficha: …» era ruido en la Bandeja — ya no se crea
    ninguna Idea; trabajo_eventos sigue guardando el evento con su ruta."""
    servidor = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(servidor.trabajo, "_es_carpeta_de_pruebas", lambda carpeta: False)
    cliente = TestClient(servidor.app)
    # Un proyecto sin libro es un repo de git de verdad.
    repo = tmp_path / "desconocido"
    (repo / ".git").mkdir(parents=True)
    cuerpo = {"tipo": "commit", "ruta": str(repo), "datos": {}}

    primera = cliente.post("/evento", json=cuerpo)
    segunda = cliente.post("/evento", json=cuerpo)

    assert primera.json()["proyecto"] is None
    assert primera.json()["anotado"] is True
    assert segunda.json()["anotado"] is True
    import db

    conexion = db.conectar()
    try:
        assert conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == 0
        rutas = [fila["ruta"] for fila in conexion.execute("SELECT ruta FROM trabajo_eventos")]
    finally:
        conexion.close()
    assert rutas == [str(repo), str(repo)]


def test_la_carpeta_personal_y_una_sin_git_no_son_proyectos(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    suelta = tmp_path / "suelta"
    suelta.mkdir()
    for ruta in (str(Path.home()), str(suelta)):
        for tipo in ("sesion_inicio", "sesion_fin", "commit"):
            respuesta = cliente.post("/evento", json={"tipo": tipo, "ruta": ruta, "datos": {}})
            assert respuesta.json()["anotado"] is False
    import db

    conexion = db.conectar()
    try:
        assert conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == 0
    finally:
        conexion.close()
    assert not (tmp_path / "boveda" / "episodios").exists() or list((tmp_path / "boveda" / "episodios").glob("*.md")) == []


def test_un_commit_en_un_repo_temporal_no_crea_idea(tmp_path, monkeypatch):
    """1-oct: cientos de «proyecto sin ficha: /private/var/folders/.../
    pytest-of-…» en la Bandeja real, una por corrida de pytest — un repo de
    verdad (con .git) pero bajo una carpeta de pruebas nunca debe anotarse."""
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    repo = tmp_path / "pytest-of-juancamilo" / "pytest-123" / "test_algo0" / "repo"
    (repo / ".git").mkdir(parents=True)

    respuesta = cliente.post("/evento", json={"tipo": "commit", "ruta": str(repo), "datos": {}})

    assert respuesta.json()["anotado"] is False
    import db

    conexion = db.conectar()
    try:
        assert conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == 0
    finally:
        conexion.close()

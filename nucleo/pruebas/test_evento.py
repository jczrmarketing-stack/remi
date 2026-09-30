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


def test_sin_ficha_entra_a_la_bandeja_una_sola_vez(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cuerpo = {"tipo": "commit", "ruta": "/Users/juan/projects/desconocido", "datos": {}}

    primera = cliente.post("/evento", json=cuerpo)
    segunda = cliente.post("/evento", json=cuerpo)

    assert primera.json()["proyecto"] is None
    assert primera.json()["anotado"] is True
    assert segunda.json()["anotado"] is False
    import db

    conexion = db.conectar()
    try:
        textos = [fila["texto"] for fila in conexion.execute("SELECT texto FROM ideas")]
    finally:
        conexion.close()
    assert textos == ["proyecto sin ficha: /Users/juan/projects/desconocido"]

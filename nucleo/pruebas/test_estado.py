"""Un commit reescribe ## Estado. Dentro de 10 min, los siguientes esperan."""
import importlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import estado_libro


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_ESTADO", "1")
    monkeypatch.setenv("REMI_TRABAJO_EN_LINEA", "1")
    for nombre in ("servidor", "db", "trabajo", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _libro(tmp_path, cuerpo: str) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(cuerpo)


LIBRO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
ruta: {repo}
---

- Prioridad baja.

## Notas

Nada de borrar esto.
"""


def _falso(vistos: list[str]):
    def redactar(pedido: str) -> str:
        vistos.append(pedido)
        return (
            "Quedaste: en el mosaico.\n"
            "Decisiones: ninguna nueva.\n"
            "Próximo paso: abrir la ficha, cinco minutos."
        )

    return redactar


def test_el_primer_commit_cambia_el_estado_y_deja_el_resto(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    vistos: list[str] = []
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", _falso(vistos))
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/evento",
        json={
            "tipo": "commit",
            "ruta": str(repo),
            "datos": {"mensaje": "el mosaico", "rama": "main", "archivos": ["a.ts"]},
        },
    )

    assert respuesta.status_code == 200
    texto = (tmp_path / "libros" / "malik.md").read_text()
    assert "Prioridad baja." in texto
    assert "## Notas" in texto
    assert "Nada de borrar esto." in texto
    assert "## Estado" in texto
    assert "Quedaste: en el mosaico." in texto
    assert "Próximo paso: abrir la ficha, cinco minutos." in texto
    assert len(vistos) == 1
    assert "el mosaico" in vistos[0]


def test_dentro_de_diez_minutos_no_redacta_de_nuevo(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    vistos: list[str] = []
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", _falso(vistos))
    cliente = TestClient(servidor.app)
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "primero", "rama": "main", "archivos": []}},
    )
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "segundo", "rama": "main", "archivos": []}},
    )

    assert len(vistos) == 1
    assert "segundo" not in (tmp_path / "libros" / "malik.md").read_text()


def test_la_tanda_siguiente_incluye_los_que_esperaron(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    vistos: list[str] = []
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", _falso(vistos))
    cliente = TestClient(servidor.app)
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "primero", "rama": "main", "archivos": []}},
    )
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "segundo", "rama": "main", "archivos": []}},
    )
    import db

    hace = datetime.now(timezone.utc) - timedelta(minutes=11)
    conexion = db.conectar()
    try:
        conexion.execute("UPDATE trabajo_estado_en SET fecha = ? WHERE tema = 'malik'", (hace.isoformat(),))
        conexion.commit()
    finally:
        conexion.close()
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "tercero", "rama": "main", "archivos": []}},
    )

    assert len(vistos) == 2
    assert "segundo" in vistos[1]
    assert "tercero" in vistos[1]
    assert "primero" not in vistos[1]


def test_sin_modelo_el_libro_igual_cambia(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", lambda _pedido: None)
    cliente = TestClient(servidor.app)

    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "el mosaico", "rama": "main", "archivos": []}},
    )

    texto = (tmp_path / "libros" / "malik.md").read_text()
    assert "Quedaste en «el mosaico», rama main." in texto
    assert "Próximo paso: retomar desde ese commit, cinco minutos." in texto


def test_normalizar_acepta_las_tres_lineas() -> None:
    assert estado_libro.normalizar(
        "Quedaste: ahí.\nDecisiones: ninguna nueva.\nPróximo paso: la ficha."
    ) == ("Quedaste: ahí.\nDecisiones: ninguna nueva.\nPróximo paso: la ficha.")
    assert estado_libro.normalizar("solo una frase") is None

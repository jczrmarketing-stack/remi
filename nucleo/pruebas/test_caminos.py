"""## Camino de un libro (Fase 3, tarea 4): hitos «- [ ]» / «- [x]».

Todo corre contra un libro de fixture (`REMI_CONOCIMIENTO` apuntando a
`tmp_path`): ningún libro real de remi-mente se lee ni se modifica acá.
"""
import importlib
import sys
from uuid import uuid4

from fastapi.testclient import TestClient


LIBRO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

## Camino

- [x] Contratos
- [ ] Bandeja
- [ ] Iniciativa

## Notas

Nada que borrar.
"""


def _libro(tmp_path, cuerpo: str = LIBRO) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(cuerpo)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("servidor", "caminos", "libros", "db"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _tarea_hecha(db_mod, conexion, titulo: str) -> None:
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible) "
        "VALUES (?, ?, NULL, 'hecha', 'paso', NULL, 5, 0)",
        (str(uuid4()), titulo),
    )
    conexion.commit()


def test_lee_hitos_y_el_siguiente_abierto(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.get("/camino/malik")
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["hitos"] == [
        {"texto": "Contratos", "hecho": True},
        {"texto": "Bandeja", "hecho": False},
        {"texto": "Iniciativa", "hecho": False},
    ]
    assert cuerpo["siguiente"] == {"texto": "Bandeja", "hecho": False}


def test_sin_tema_conocido_es_404(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    assert cliente.get("/camino/no-existe").status_code == 404


def test_una_tarea_hecha_marca_el_hito_x_en_el_archivo(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    _tarea_hecha(db, conexion, "Bandeja")
    conexion.close()

    cliente = TestClient(servidor.app)
    cuerpo = cliente.get("/camino/malik").json()

    assert cuerpo["hitos"][1] == {"texto": "Bandeja", "hecho": True}
    assert cuerpo["siguiente"] == {"texto": "Iniciativa", "hecho": False}

    texto = (tmp_path / "libros" / "malik.md").read_text()
    assert "- [x] Bandeja" in texto
    # El resto del libro no se toca.
    assert "## Notas" in texto
    assert "Nada que borrar." in texto


def test_nunca_escribe_un_hito_nuevo_ni_reordena(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    antes = (tmp_path / "libros" / "malik.md").read_text()
    cliente.get("/camino/malik")
    despues = (tmp_path / "libros" / "malik.md").read_text()

    # Sin tareas hechas que calcen, el archivo queda idéntico.
    assert antes == despues


def test_todos_cumplidos_siguiente_es_null(tmp_path, monkeypatch):
    _libro(
        tmp_path,
        "---\ntitulo: Malik\ntema: malik\nresumen: x\n---\n\n## Camino\n\n- [x] Contratos\n",
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/camino/malik").json()
    assert cuerpo["siguiente"] is None

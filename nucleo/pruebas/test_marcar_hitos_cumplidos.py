"""T5.5: marcar_hitos_cumplidos solo marca un hito si la tarea hecha es de
ese libro — los hitos del SOP («Intake», «Contrato»…) se repiten entre
libros, así que comparar solo el título los mezclaba."""
from uuid import uuid4

import caminos
import libros

LIBRO_A = """---
titulo: UpVisuals
tema: upvisuals
resumen: r
tipo: cliente
---

## Camino

- [ ] Intake
- [ ] Contrato
"""

LIBRO_B = """---
titulo: BeaM
tema: beam
resumen: r
tipo: cliente
---

## Camino

- [ ] Intake
- [ ] Contrato
"""


def _boveda(tmp_path):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_A)
    (carpeta / "beam.md").write_text(LIBRO_B)
    return carpeta


def _tarea_hecha(conexion, titulo: str) -> str:
    tid = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, "
        "real_min, compartible) VALUES (?, ?, NULL, 'hecha', 'p', NULL, NULL, 0)",
        (tid, titulo),
    )
    conexion.commit()
    return tid


def _sesion(conexion, tarea_id: str, app_contexto: str) -> None:
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) "
        "VALUES (?, ?, '2026-10-01T10:00:00+00:00', '2026-10-01T10:05:00+00:00', 5, ?)",
        (str(uuid4()), tarea_id, app_contexto),
    )
    conexion.commit()


def test_una_tarea_hecha_de_otro_libro_no_marca_el_hito(tmp_path, monkeypatch):
    carpeta = _boveda(tmp_path)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    import sys
    for nombre in ("db", "libros", "caminos"):
        sys.modules.pop(nombre, None)
    import db
    import importlib
    import libros as libros_mod
    import caminos as caminos_mod
    importlib.reload(db)
    importlib.reload(libros_mod)
    importlib.reload(caminos_mod)

    conexion = db.conectar()
    tarea_id = _tarea_hecha(conexion, "Intake")
    _sesion(conexion, tarea_id, "beam")  # el Intake hecho es de BeaM, no de UpVisuals

    libro_upvisuals = next(l for l in libros_mod.listar() if l.tema == "upvisuals")
    hitos = caminos_mod.marcar_hitos_cumplidos(conexion, libro_upvisuals)

    assert hitos[0].hecho is False, "el Intake de UpVisuals no debería marcarse por un Intake de BeaM"


def test_una_tarea_hecha_del_mismo_libro_si_marca_el_hito(tmp_path, monkeypatch):
    carpeta = _boveda(tmp_path)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    import sys
    for nombre in ("db", "libros", "caminos"):
        sys.modules.pop(nombre, None)
    import db
    import importlib
    import libros as libros_mod
    import caminos as caminos_mod
    importlib.reload(db)
    importlib.reload(libros_mod)
    importlib.reload(caminos_mod)

    conexion = db.conectar()
    tarea_id = _tarea_hecha(conexion, "Intake")
    _sesion(conexion, tarea_id, "upvisuals")

    libro_upvisuals = next(l for l in libros_mod.listar() if l.tema == "upvisuals")
    hitos = caminos_mod.marcar_hitos_cumplidos(conexion, libro_upvisuals)

    assert hitos[0].hecho is True

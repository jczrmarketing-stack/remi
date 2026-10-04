"""El nivel 2 del proyecto activo entra al contexto sin llamar a `leer`."""
import importlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

LIBRO = """---
titulo: UpVisuals
tema: upvisuals
resumen: Cliente Alfonso, distribución de contenido.
---

## Estado

Quedaste: armando la Fase 1.
Decisiones: ninguna nueva.
Próximo paso: mandar la propuesta.
"""


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    for nombre in ("db", "libros", "precarga"):
        sys.modules.pop(nombre, None)
    import db
    import libros
    import precarga

    importlib.reload(db)
    importlib.reload(libros)
    importlib.reload(precarga)
    (tmp_path / "proyectos").mkdir(parents=True, exist_ok=True)
    (tmp_path / "proyectos" / "upvisuals.md").write_text(LIBRO)
    return precarga, db


def test_sin_ninguna_senal_no_hay_nada_que_precargar(tmp_path, monkeypatch):
    precarga, _ = _arrancar(tmp_path, monkeypatch)
    (tmp_path / "proyectos" / "upvisuals.md").unlink()  # sin libro, tampoco
    assert precarga.proyecto_activo() is None
    assert precarga.bloque() is None


def test_precarga_el_ultimo_libro_tocado_si_no_hay_bloque_abierto(tmp_path, monkeypatch):
    precarga, db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    try:
        conexion.execute(
            "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), "commit", "/tmp/upvisuals", "upvisuals", "{}", datetime.now(timezone.utc).isoformat()),
        )
        conexion.commit()
    finally:
        conexion.close()

    activo = precarga.proyecto_activo()
    assert activo == ("upvisuals", "ultimo_tocado")
    resultado = precarga.bloque()
    assert resultado is not None
    texto, registro = resultado
    assert "UpVisuals" in texto
    assert "Próximo paso: mandar la propuesta." in texto
    assert registro == "upvisuals razon=ultimo_tocado"


def test_el_bloque_abierto_gana_al_ultimo_tocado(tmp_path, monkeypatch):
    precarga, db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    try:
        conexion.execute(
            "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), "commit", "/tmp/otro", "otro-proyecto", "{}", datetime.now(timezone.utc).isoformat()),
        )
        conexion.commit()
        from modelos import Sesion, Tarea

        tarea = Tarea(
            id=uuid4(), titulo="x", proyecto_id=None, estado="hoy",
            paso_minimo="x", estimado_min=None, real_min=None, hora=None, fecha_limite=None, tipo=None, compartible=False,
        )
        db.crear_tarea(conexion, tarea)
        sesion = Sesion(
            id=uuid4(), tarea_id=tarea.id, inicio=datetime.now(timezone.utc),
            fin=None, real_min=0, app_contexto="upvisuals",
        )
        db.crear_sesion(conexion, sesion)
    finally:
        conexion.close()

    assert precarga.proyecto_activo() == ("upvisuals", "bloque_abierto")


def test_sin_estado_todavia_usa_el_resumen_del_libro(tmp_path, monkeypatch):
    precarga, db = _arrancar(tmp_path, monkeypatch)
    (tmp_path / "proyectos" / "upvisuals.md").write_text(
        "---\ntitulo: UpVisuals\ntema: upvisuals\nresumen: Cliente Alfonso.\n---\n\nNada más.\n"
    )
    resumen = precarga.resumen_nivel2("upvisuals")
    assert resumen == "UpVisuals: Cliente Alfonso."

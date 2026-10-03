"""Lo viejo dice que es viejo (encargo del 2-oct, tarea 3): todo episodio,
lección o Estado que entra al contexto lleva su fecha visible («30-sep: …»).
El caso real: Remi presentó un 401 del 30-sep como si pasara hoy."""
import os
import sqlite3
from datetime import date, datetime, timezone

import libros
import precarga
import trabajo
import vectores

EPISODIO_401 = '---\ntitulo: "El agente de /investigar en malik-gestion no llegó a arrancar: 401"\ntema: malik\nresumen: "revisar las credenciales"\n---\n\nCuerpo.\n'
LIBRO = "---\ntitulo: Malik\ntema: malik\nresumen: r\n---\n\n## Estado\n\nQuedaste: en el 401.\nDecisiones: ninguna.\nPróximo paso: revisar el token.\n"


def test_la_fecha_corta():
    assert libros.fecha_corta(date(2026, 9, 30)) == "30-sep"
    assert libros.fecha_corta(date(2026, 10, 2)) == "2-oct"


def _boveda(tmp_path, monkeypatch):
    (tmp_path / "proyectos").mkdir()
    (tmp_path / "episodios").mkdir()
    (tmp_path / "proyectos" / "malik.md").write_text(LIBRO)
    (tmp_path / "episodios" / "2026-09-30-el-agente-de-investigar.md").write_text(EPISODIO_401)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path))
    return tmp_path


def test_los_asociados_de_un_episodio_llevan_su_fecha(tmp_path, monkeypatch):
    boveda = _boveda(tmp_path, monkeypatch)
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    vectores.preparar(conexion)
    uno = [1.0] + [0.0] * (vectores.DIMENSIONES - 1)
    filas = [
        (boveda / "episodios" / "2026-09-30-el-agente-de-investigar.md", "episodio", "El agente de /investigar no arrancó: 401"),
        (boveda / "proyectos" / "malik.md", "libro", "Malik"),
    ]
    for i, (ruta, tipo, titulo) in enumerate(filas, start=1):
        conexion.execute(
            "INSERT INTO notas_vector (id, ruta, tipo, titulo, hash, actualizado) VALUES (?, ?, ?, ?, 'h', 'x')",
            (i, str(ruta), tipo, titulo),
        )
        conexion.execute("INSERT INTO notas_vector_embed (rowid, embedding) VALUES (?, ?)", (i, vectores._empaquetar(uno)))
    monkeypatch.setattr(vectores, "embed", lambda texto: uno)

    con_fecha = vectores.asociar(conexion, "el 401", con_fecha=True)
    assert "30-sep: El agente de /investigar no arrancó: 401" in con_fecha
    assert "Malik" in con_fecha  # un libro no es «viejo»: sin fecha
    # Sin pedirla, como siempre (experiencia.buscar usa los títulos tal cual).
    assert "El agente de /investigar no arrancó: 401" in vectores.asociar(conexion, "el 401")


def test_el_estado_precargado_dice_de_cuando_es(tmp_path, monkeypatch):
    boveda = _boveda(tmp_path, monkeypatch)
    hace = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc).timestamp()
    os.utime(boveda / "proyectos" / "malik.md", (hace, hace))
    texto = precarga.resumen_nivel2("malik")
    assert texto is not None and "Estado del 30-sep" in texto and "Quedaste: en el 401." in texto


def test_los_ojo_llevan_la_fecha_de_la_ultima_vez(tmp_path, monkeypatch):
    import experiencia
    from experiencia import Leccion

    _boveda(tmp_path, monkeypatch)
    experiencia.escribir(
        Leccion(
            titulo="El 401 de malik", tema="malik", resumen="r", clase="error", donde="x",
            secciones={"Síntoma": "401.", "Lo que creímos": "", "Causa real": "El token había vencido.",
                       "Cura": "Se renovó.", "Cómo verlo antes": "Mirar la fecha."},
            fuente="claude-code",
        ),
        ahora=datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc),
    )
    (ojo,) = trabajo.lecciones_de_ojo("malik")
    assert ojo.startswith("Ojo: el 30-sep ya pasó El 401 de malik")


def test_pensar_pide_los_asociados_con_fecha(monkeypatch):
    import pensar

    vistos = {}
    monkeypatch.setattr(vectores, "asociar", lambda conexion, frase, **k: vistos.update(k) or [])
    pensar._asociados("el 401")
    assert vistos == {"con_fecha": True}

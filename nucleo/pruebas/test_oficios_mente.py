"""Los oficios entran a la mente (Biblia Parte VI, Fase S punto 1).

Un oficio es un libro más: título y resumen siempre presentes en el índice
que viaja en el system prompt, y se abre entero con `leer()` como cualquier
otro. Esto prueba la siembra, no la asociación por vector (ya cubierta en
test_vectores.py).
"""
import sqlite3

import db
import sembrar_conocimiento


def _boveda(tmp_path):
    proyectos = tmp_path / "boveda" / "proyectos"
    oficios = tmp_path / "boveda" / "oficios"
    proyectos.mkdir(parents=True)
    oficios.mkdir(parents=True)
    (oficios / "mantenimiento.md").write_text(
        "---\n"
        "titulo: Mantenimiento — la mensualidad\n"
        "tema: oficio-mantenimiento\n"
        "resumen: Cómo se cobra la cuota mensual después de entregar.\n"
        "claves: [mensualidad, retainer]\n"
        "tipo: oficio\n"
        "---\n\n"
        "## Precio\nSe cobra por adelantado, mes a mes.\n"
    )
    return proyectos


def test_sembrar_oficios_entra_al_indice_con_nivel_1(tmp_path, monkeypatch) -> None:
    proyectos = _boveda(tmp_path)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(proyectos))
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))

    cuenta = sembrar_conocimiento.sembrar_oficios()
    assert cuenta["creadas"] == 1

    conexion = db.conectar()
    try:
        indice = db.indice_memoria(conexion)
    finally:
        conexion.close()

    entrada = next((e for e in indice if e.tema == "oficio-mantenimiento"), None)
    assert entrada is not None, indice
    assert "Mantenimiento" in entrada.titulo
    assert "mensualidad" in entrada.resumen.lower() or "cuota" in entrada.resumen.lower()
    assert entrada.nivel == sembrar_conocimiento.NIVEL_RECIENTE


def test_sembrar_oficios_es_idempotente(tmp_path, monkeypatch) -> None:
    proyectos = _boveda(tmp_path)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(proyectos))
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))

    primera = sembrar_conocimiento.sembrar_oficios()
    segunda = sembrar_conocimiento.sembrar_oficios()

    assert primera["creadas"] == 1
    assert segunda["creadas"] == 0
    assert segunda["iguales"] == 1


def test_oficio_se_lee_entero_por_id(tmp_path, monkeypatch) -> None:
    proyectos = _boveda(tmp_path)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(proyectos))
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sembrar_conocimiento.sembrar_oficios()

    conexion = db.conectar()
    try:
        entrada = next(
            e for e in db.indice_memoria(conexion) if e.tema == "oficio-mantenimiento"
        )
        memoria = db.leer_memoria(conexion, entrada.id)
    finally:
        conexion.close()

    assert memoria is not None
    assert "Se cobra por adelantado" in memoria.cuerpo


def test_carpeta_de_oficios_es_hermana_de_proyectos(tmp_path, monkeypatch) -> None:
    proyectos = tmp_path / "otra" / "proyectos"
    proyectos.mkdir(parents=True)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(proyectos))
    assert sembrar_conocimiento.carpeta_oficios() == proyectos.parent / "oficios"

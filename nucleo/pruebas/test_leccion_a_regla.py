"""T9.1: cuando una lección llega a veces: 2, Remi propone una regla —
nunca la escribe sola."""
import sys
from datetime import datetime, timezone

import experiencia
from experiencia import Leccion


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    (tmp_path / "boveda" / "oficios").mkdir(parents=True, exist_ok=True)
    (tmp_path / "boveda" / "oficios" / "mi-voz.md").write_text(
        "---\ntitulo: Mi voz\ntema: oficio-mi-voz\nresumen: r\ntipo: oficio\n---\n\nCuerpo.\n"
    )
    for nombre in ("db", "experiencia", "preguntas", "correcciones", "episodios", "libros"):
        sys.modules.pop(nombre, None)
    import importlib

    import db
    import experiencia as exp
    import preguntas as preg

    importlib.reload(db)
    importlib.reload(exp)
    importlib.reload(preg)
    return db, exp, preg


def _leccion():
    return Leccion(
        titulo="El 401 de malik por token vencido",
        tema="malik",
        resumen="El bot devolvía 401 porque el token había vencido.",
        clase="error",
        donde="x",
        secciones={
            "Síntoma": "El bot contestaba 401.",
            "Lo que creímos": "",
            "Causa real": "El token había vencido.",
            "Cura": "Se renovó el token.",
            "Cómo verlo antes": "Revisar la fecha de expiración del token antes de depurar otra cosa.",
        },
        fuente="claude-code",
    )


def test_la_primera_vez_no_propone_nada(tmp_path, monkeypatch):
    db, exp, preg = _arrancar(tmp_path, monkeypatch)
    ahora = datetime.now(timezone.utc)
    exp.escribir(_leccion(), ahora)

    conexion = db.conectar()
    pendientes = db.listar_preguntas_pendientes(conexion, ahora, "malik")
    assert pendientes == []


def test_la_segunda_vez_propone_la_regla(tmp_path, monkeypatch):
    db, exp, preg = _arrancar(tmp_path, monkeypatch)
    ahora = datetime.now(timezone.utc)
    exp.escribir(_leccion(), ahora)

    exp.escribir(_leccion(), ahora)

    conexion = db.conectar()
    pendientes = db.listar_preguntas_pendientes(conexion, ahora, "malik")
    assert len(pendientes) == 1
    assert pendientes[0].campo.startswith("regla.")
    assert "ya pasó dos veces" in pendientes[0].voz


def test_decir_que_si_aplica_la_regla_con_commit(tmp_path, monkeypatch):
    db, exp, preg = _arrancar(tmp_path, monkeypatch)
    ahora = datetime.now(timezone.utc)
    exp.escribir(_leccion(), ahora)
    exp.escribir(_leccion(), ahora)
    conexion = db.conectar()
    pregunta = db.listar_preguntas_pendientes(conexion, ahora, "malik")[0]

    entendida = preg.responder(conexion, pregunta, "dale")

    assert entendida is True
    texto_oficio = (tmp_path / "boveda" / "oficios" / "mi-voz.md").read_text()
    assert "Revisar la fecha de expiración" in texto_oficio


def test_decir_que_no_descarta_en_silencio(tmp_path, monkeypatch):
    db, exp, preg = _arrancar(tmp_path, monkeypatch)
    ahora = datetime.now(timezone.utc)
    exp.escribir(_leccion(), ahora)
    exp.escribir(_leccion(), ahora)
    conexion = db.conectar()
    pregunta = db.listar_preguntas_pendientes(conexion, ahora, "malik")[0]

    entendida = preg.responder(conexion, pregunta, "no, dejalo así")

    assert entendida is True  # se entendió la respuesta — es un "no"
    texto_oficio = (tmp_path / "boveda" / "oficios" / "mi-voz.md").read_text()
    assert "Revisar la fecha de expiración" not in texto_oficio


def test_una_tercera_vez_no_duplica_la_propuesta(tmp_path, monkeypatch):
    db, exp, preg = _arrancar(tmp_path, monkeypatch)
    ahora = datetime.now(timezone.utc)
    exp.escribir(_leccion(), ahora)
    exp.escribir(_leccion(), ahora)
    exp.escribir(_leccion(), ahora)

    conexion = db.conectar()
    pendientes = db.listar_preguntas_pendientes(conexion, ahora, "malik")
    assert len(pendientes) == 1

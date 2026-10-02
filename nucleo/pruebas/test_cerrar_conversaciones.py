"""T9.5: lo que se habla con Remi también queda — una conversación de la
ventanita/Telegram, 60 min sin turnos, con sustancia, deja su episodio."""
import sys
from datetime import datetime, timedelta, timezone

import db

TEXTO_SUSTANCIAL = "Hablamos del precio de la Fase 1 de UpVisuals. " * 40  # > LARGO_MINIMO


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("db", "cierre", "episodios", "libros", "temas"):
        sys.modules.pop(nombre, None)
    import importlib

    import cierre as c
    import db as d

    importlib.reload(d)
    importlib.reload(c)
    return d, c


def _conversacion_con_turnos(db_mod, texto_juan: str, hace: timedelta) -> str:
    conexion = db_mod.conectar()
    try:
        ahora = datetime.now(timezone.utc) - hace
        conversacion_id = db_mod.guardar_turno(conexion, "juan", texto_juan, ahora)
        db_mod.guardar_turno(conexion, "remi", "Entendido.", ahora + timedelta(seconds=5))
    finally:
        conexion.close()
    return conversacion_id


def test_una_conversacion_activa_no_se_toca(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=5))

    cerradas = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert cerradas == 0


def test_una_conversacion_inactiva_sustancial_deja_episodio(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    conversacion_id = _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))

    cerradas = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert cerradas == 1
    episodios = list((tmp_path / "boveda" / "episodios").glob("*charla*.md"))
    assert len(episodios) == 1

    conexion = db_mod.conectar()
    try:
        fila = conexion.execute(
            "SELECT titulo, episodio_hecho FROM conversaciones WHERE id = ?", (conversacion_id,)
        ).fetchone()
    finally:
        conexion.close()
    assert fila["episodio_hecho"] == 1
    assert fila["titulo"]


def test_una_conversacion_trivial_no_deja_episodio_pero_se_marca(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    conversacion_id = _conversacion_con_turnos(db_mod, "hola", hace=timedelta(minutes=90))

    cerradas = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert cerradas == 0
    assert list((tmp_path / "boveda" / "episodios").glob("*.md")) == []
    conexion = db_mod.conectar()
    try:
        fila = conexion.execute(
            "SELECT episodio_hecho FROM conversaciones WHERE id = ?", (conversacion_id,)
        ).fetchone()
    finally:
        conexion.close()
    assert fila["episodio_hecho"] == 1


def test_no_se_revisa_dos_veces(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))

    cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))
    segunda = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert segunda == 0
    assert len(list((tmp_path / "boveda" / "episodios").glob("*.md"))) == 1

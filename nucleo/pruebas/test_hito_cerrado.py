"""B3.4 (forma K): cómo se cerró cada hito solo, y deshacer."""
import sys
from datetime import datetime, timezone


def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sys.modules.pop("db", None)
    import db

    return db


def test_marcar_y_leer_hito_cerrado(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    en = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    db.marcar_hito_cerrado(conexion, "upvisuals", 5, "encargo", "sess-1", en)
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()

    assert cerrado == db.HitoCerrado(tipo="encargo", ref="sess-1", en=en)


def test_hito_sin_cerrar_es_none(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()

    assert cerrado is None


def test_deshacer_lo_quita(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    en = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    db.marcar_hito_cerrado(conexion, "upvisuals", 5, "encargo", "sess-1", en)
    db.deshacer_hito_cerrado(conexion, "upvisuals", 5)
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()

    assert cerrado is None


def test_marcar_de_nuevo_reemplaza_no_duplica(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    en1 = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    en2 = datetime(2026, 10, 4, 13, 0, tzinfo=timezone.utc)
    db.marcar_hito_cerrado(conexion, "upvisuals", 5, "encargo", "sess-1", en1)
    db.marcar_hito_cerrado(conexion, "upvisuals", 5, "mensaje", "sess-2", en2)
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()

    assert cerrado == db.HitoCerrado(tipo="mensaje", ref="sess-2", en=en2)


def test_dos_temas_no_se_pisan(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    en = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    db.marcar_hito_cerrado(conexion, "upvisuals", 5, "encargo", "sess-1", en)
    db.marcar_hito_cerrado(conexion, "beam", 5, "mensaje", "sess-2", en)
    a = db.hito_cerrado_de(conexion, "upvisuals", 5)
    b = db.hito_cerrado_de(conexion, "beam", 5)
    conexion.close()

    assert a.tipo == "encargo"
    assert b.tipo == "mensaje"

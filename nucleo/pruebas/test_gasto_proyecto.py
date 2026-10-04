"""B6.1: la tabla gasto_proyecto — de un proyecto, o común (tema NULL)."""
import sys
from datetime import datetime, timedelta, timezone


def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sys.modules.pop("db", None)
    import db

    return db


def test_crear_y_leer_gasto_de_proyecto(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    fecha = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, "upvisuals", "servidor", 40.0, fecha)
    gastos = db.gastos_de_tema(conexion, "upvisuals")
    conexion.close()
    assert len(gastos) == 1
    assert gastos[0].monto == 40.0
    assert gastos[0].concepto == "servidor"


def test_gasto_comun_no_aparece_en_gastos_de_tema(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    fecha = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, None, "dominio", 20.0, fecha)
    db.crear_gasto(conexion, "upvisuals", "servidor", 40.0, fecha)
    de_upvisuals = db.gastos_de_tema(conexion, "upvisuals")
    conexion.close()
    assert [g.concepto for g in de_upvisuals] == ["servidor"]


def test_gastos_comunes_desde_una_fecha(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    mes_pasado = datetime(2026, 9, 1, tzinfo=timezone.utc)
    este_mes = datetime(2026, 10, 2, tzinfo=timezone.utc)
    db.crear_gasto(conexion, None, "dominio", 20.0, mes_pasado)
    db.crear_gasto(conexion, None, "membresía", 100.0, este_mes)
    comunes = db.gastos_comunes_desde(conexion, datetime(2026, 10, 1, tzinfo=timezone.utc))
    conexion.close()
    assert [g.concepto for g in comunes] == ["membresía"]


def test_corregir_un_gasto_a_mano(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    fecha = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    gasto = db.crear_gasto(conexion, "upvisuals", "servidor", 40.0, fecha)
    corregido = db.corregir_gasto(conexion, gasto.id, 45.0)
    de_nuevo = db.gastos_de_tema(conexion, "upvisuals")
    conexion.close()
    assert corregido is not None and corregido.monto == 45.0
    assert de_nuevo[0].monto == 45.0


def test_corregir_un_gasto_que_no_existe_es_none(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    conexion = db.conectar()
    resultado = db.corregir_gasto(conexion, "no-existe", 10.0)
    conexion.close()
    assert resultado is None

"""B6: ficha.py — gastado agrupado, comunes repartidos por minutos del
mes, y por_hora. Sin IA, puro."""
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sys.modules.pop("db", None)
    sys.modules.pop("trabajo", None)
    sys.modules.pop("ficha", None)
    import db

    import ficha

    return ficha


def _sesion(conexion, tema, inicio, fin):
    tarea_id = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible) "
        "VALUES (?, 'x', NULL, 'hecha', 'paso', NULL, NULL, 0)",
        (tarea_id,),
    )
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, ?, 0, ?)",
        (str(uuid4()), tarea_id, inicio.isoformat(), fin.isoformat() if fin else None, tema),
    )
    conexion.commit()


def test_gastado_de_un_tema_sin_comunes(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, "upvisuals", "servidor", 40.0, ahora)
    gastado, gastos = ficha.gastado_de(conexion, "upvisuals", ["upvisuals"], ahora)
    conexion.close()
    assert gastado == 40.0
    assert gastos == [ficha.GastoAgrupado(concepto="servidor", monto=40.0)]


def test_gastos_del_mismo_concepto_se_agrupan(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, "upvisuals", "servidor", 40.0, ahora)
    db.crear_gasto(conexion, "upvisuals", "servidor", 10.0, ahora)
    gastado, gastos = ficha.gastado_de(conexion, "upvisuals", ["upvisuals"], ahora)
    conexion.close()
    assert gastado == 50.0
    assert gastos == [ficha.GastoAgrupado(concepto="servidor", monto=50.0)]


def test_comunes_se_reparten_por_minutos_del_mes(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, None, "membresía", 100.0, ahora)
    # upvisuals: 180 min este mes; beam: 60 min este mes → 75%/25%.
    _sesion(conexion, "upvisuals", ahora - timedelta(hours=3), ahora)
    _sesion(conexion, "beam", ahora - timedelta(hours=1), ahora)
    gastado_up, _ = ficha.gastado_de(conexion, "upvisuals", ["upvisuals", "beam"], ahora)
    gastado_beam, _ = ficha.gastado_de(conexion, "beam", ["upvisuals", "beam"], ahora)
    conexion.close()
    assert gastado_up == 75.0
    assert gastado_beam == 25.0


def test_un_proyecto_sin_minutos_este_mes_no_carga_comunes(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, None, "membresía", 100.0, ahora)
    gastado, _ = ficha.gastado_de(conexion, "sin-trabajo", ["sin-trabajo"], ahora)
    conexion.close()
    assert gastado == 0.0


def test_por_hora_sin_minutos_es_none(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    assert ficha.por_hora(1000.0, 100.0, 0) is None


def test_por_hora_calculado(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    # (1000 - 100) / 2 horas = 450/hora
    assert ficha.por_hora(1000.0, 100.0, 120) == 450.0


def test_gastos_comunes_mes_no_trae_los_de_meses_pasados(tmp_path, monkeypatch):
    ficha = _db(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.crear_gasto(conexion, None, "vieja", 50.0, datetime(2026, 9, 1, tzinfo=timezone.utc))
    db.crear_gasto(conexion, None, "nueva", 100.0, ahora)
    total = ficha.gastos_comunes_mes(conexion, ahora)
    conexion.close()
    assert total == 100.0

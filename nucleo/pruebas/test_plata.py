"""GET /plata (Panel · Metas): solo números, ningún texto que regañe.

`calcular()` toma `ahora` como parámetro — nada acá llama a
`datetime.now()`, para que las pruebas controlen el reloj del todo.
"""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import plata

BOGOTA = plata.BOGOTA


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "plata", "entregas", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _entrega(conexion, fecha: datetime, monto: float | None, estado: str, cliente: str = "Alfonso") -> None:
    conexion.execute(
        "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
        "VALUES (?, ?, ?, ?, ?, ?, 1)",
        (str(uuid4()), cliente, str(uuid4()), fecha.isoformat(), monto, estado),
    )
    conexion.commit()


def test_sin_entregas_cobrado_es_cero_nunca_error(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.get("/plata")
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["semana"]["cobrado"] == 0
    assert cuerpo["mes"]["cobrado"] == 0
    assert cuerpo["mes"]["faltan"] == cuerpo["mes"]["meta"]
    assert cuerpo["proximo"] is None


def test_meta_semanal_es_la_mensual_sobre_4_33(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/plata").json()
    assert cuerpo["semana"]["meta_semanal"] == 2400 / 4.33
    assert cuerpo["mes"]["meta"] == 2400


def test_cobrado_de_la_semana_solo_cuenta_pagadas_de_esta_semana(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    lunes = plata._lunes(ahora)

    _entrega(conexion, lunes, 500, "pagada")  # de esta semana
    _entrega(conexion, lunes - timedelta(days=1), 900, "pagada")  # semana pasada
    _entrega(conexion, ahora, 300, "camino")  # no cobrada
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.semana.cobrado == 500


def test_cobrado_del_mes_suma_todas_las_pagadas_del_mes(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    primero = plata._primero_del_mes(ahora)

    _entrega(conexion, primero, 500, "pagada")
    _entrega(conexion, ahora, 300, "pagada")
    _entrega(conexion, primero - timedelta(days=1), 999, "pagada")  # mes pasado
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.mes.cobrado == 800
    assert resultado.mes.faltan == 2400 - 800


def test_faltan_nunca_es_negativo_si_ya_se_supero_la_meta(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _entrega(conexion, ahora, 5000, "pagada")
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.mes.faltan == 0


def test_proximo_es_la_entrega_con_dinero_mas_cercana_sin_cobrar(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _entrega(conexion, ahora + timedelta(days=10), 1000, "camino", cliente="Lejano")
    _entrega(conexion, ahora + timedelta(days=2), 500, "entregada", cliente="Cercano")
    _entrega(conexion, ahora - timedelta(days=1), 200, "camino", cliente="Pasado")  # ya pasó
    _entrega(conexion, ahora + timedelta(days=1), None, "camino", cliente="SinMonto")  # sin monto
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.proximo is not None
    assert resultado.proximo.cliente == "Cercano"
    assert resultado.proximo.monto == 500


def test_nunca_hay_texto_que_regane(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/plata").json()
    for valor in _valores_string(cuerpo):
        for palabra in ("atrasa", "deber", "fall", "urgen", "mal"):
            assert palabra not in valor.lower()


def _valores_string(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _valores_string(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _valores_string(v)
    elif isinstance(obj, str):
        yield obj

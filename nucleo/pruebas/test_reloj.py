"""R2 (forma S): el Reloj — EBS con simulación sembrada sobre velocidades
reales (estimado / real) de tareas hechas del mismo tipo."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import db
import reloj
import servidor
from modelos import Propuesta, Tarea


def _tarea_hecha(tipo: str, estimado_min: int, real_min: int) -> Tarea:
    return Tarea(
        id=uuid4(),
        titulo="una tarea",
        proyecto_id=None,
        estado="hecha",
        paso_minimo="listo",
        estimado_min=estimado_min,
        real_min=real_min,
        hora=None,
        fecha_limite=None,
        tipo=tipo,
        compartible=False,
    )


def test_sin_datos_devuelve_el_mismo_minuto(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        estimacion = reloj.estimar(conexion, "código", 30)
    finally:
        conexion.close()
    assert estimacion.n == 0
    assert estimacion.p50 == estimacion.p80 == estimacion.p95 == 30


def test_velocidad_menor_a_uno_sube_el_p50(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        # 10 tareas de "código": estimado 30, real 60 → velocidad 0.5 (se
        # tardó el doble de lo dicho).
        for _ in range(10):
            db.crear_tarea(conexion, _tarea_hecha("código", 30, 60))
        estimacion = reloj.estimar(conexion, "código", 30, semilla=1)
    finally:
        conexion.close()
    assert estimacion.n == 10
    assert estimacion.p50 > 30
    assert estimacion.p95 >= estimacion.p80 >= estimacion.p50


def test_tipo_nuevo_usa_historial_amplio(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        for _ in range(8):
            db.crear_tarea(conexion, _tarea_hecha("diseño", 20, 40))
        # Solo 2 de "código" — menos del mínimo propio (6): usa el
        # historial amplio (las 8 de "diseño") en vez de quedarse sin datos.
        for _ in range(2):
            db.crear_tarea(conexion, _tarea_hecha("código", 20, 40))
        estimacion = reloj.estimar(conexion, "código", 20, semilla=2)
    finally:
        conexion.close()
    assert estimacion.n == 2  # el `n` reporta lo propio, aunque la muestra sea amplia
    assert estimacion.p50 > 20


def test_endpoint_get_reloj_estimar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    r = cliente.get("/reloj/estimar", params={"tipo": "código", "min": 30})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["tipo"] == "código"
    assert cuerpo["p50"] == 30  # sin datos, nunca inventa
    assert cuerpo["n"] == 0


def test_excede_90_min():
    assert reloj.excede_90_min(91) is True
    assert reloj.excede_90_min(90) is False


# --- R5.2: latido -------------------------------------------------------


def test_latido_sin_datos_nunca_inventa_dias_callados(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        latidos = reloj.calcular_latido(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()
    assert {l.pieza for l in latidos} == {"reloj", "pronosticos", "cuenta"}
    assert all(l.callado_dias is None for l in latidos)
    assert reloj.piezas_caladas(latidos) == []


def test_dos_dias_sin_datos_de_propuestas_es_una_pieza_calada(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        db.crear_propuesta(
            conexion, Propuesta(id=uuid4(), cliente="x", monto=100.0, fecha=ahora - timedelta(days=3), estado="pendiente")
        )
        latidos = reloj.calcular_latido(conexion, ahora)
    finally:
        conexion.close()
    cuenta = next(l for l in latidos if l.pieza == "cuenta")
    assert cuenta.callado_dias == 3
    caladas = reloj.piezas_caladas(latidos)
    assert len(caladas) == 1
    assert caladas[0].pieza == "cuenta"


def test_un_dia_sin_datos_no_se_considera_calado(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        db.crear_propuesta(
            conexion, Propuesta(id=uuid4(), cliente="x", monto=100.0, fecha=ahora - timedelta(days=1), estado="pendiente")
        )
        latidos = reloj.calcular_latido(conexion, ahora)
    finally:
        conexion.close()
    assert reloj.piezas_caladas(latidos) == []


def test_endpoint_get_rumbo_latido(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    r = cliente.get("/rumbo/latido")
    assert r.status_code == 200
    piezas = {item["pieza"] for item in r.json()}
    assert piezas == {"reloj", "pronosticos", "cuenta"}

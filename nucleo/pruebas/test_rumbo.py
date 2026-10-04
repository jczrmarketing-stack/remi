"""R1: Rumbo — visión, meta, escalera y partida. Sin IA: `parsear_vision`
es una función pura; la meta real solo cambia con `confirmada: true`."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import db
import rumbo
import servidor
from modelos import Sesion, Tarea


def test_parsear_vision_extrae_rango_y_plazo():
    propuesta = rumbo.parsear_vision("quiero 10 a 15 mil al mes, seis meses seguidos")
    assert propuesta.monto_min == 10000
    assert propuesta.monto_max == 15000
    assert propuesta.meses_seguidos == 6


def test_parsear_vision_un_solo_monto_sin_plazo():
    propuesta = rumbo.parsear_vision("quiero llegar a 20 mil al mes")
    assert propuesta.monto_min == 20000
    assert propuesta.monto_max == 20000
    assert propuesta.meses_seguidos is None


def test_parsear_vision_sin_numero_no_inventa():
    propuesta = rumbo.parsear_vision("quiero vivir tranquilo")
    assert propuesta.monto_min is None
    assert propuesta.meses_seguidos is None


def test_contar_vision_deja_propuesta_y_no_cambia_la_meta(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)

    r = cliente.post("/rumbo/vision", json={"texto": "quiero 10 a 15 mil al mes, seis meses seguidos"})
    assert r.status_code == 200
    propuesta = r.json()["propuesta"]
    assert propuesta["monto_min"] == 10000
    assert propuesta["monto_max"] == 15000
    assert propuesta["meses_seguidos"] == 6

    # Contar la visión no confirma nada: la meta sigue vacía.
    rumbo_actual = cliente.get("/rumbo").json()
    assert rumbo_actual["meta"] is None
    assert rumbo_actual["vision"] == "quiero 10 a 15 mil al mes, seis meses seguidos"


def test_meta_solo_cambia_con_confirmada(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)

    cliente.post("/rumbo/vision", json={"texto": "quiero 10 a 15 mil al mes, seis meses seguidos"})
    sin_confirmar = cliente.post(
        "/rumbo/meta",
        json={"monto_min": 10000, "monto_max": 15000, "meses_seguidos": 6, "confirmada": False},
    ).json()
    assert sin_confirmar is None
    assert cliente.get("/rumbo").json()["meta"] is None

    confirmada = cliente.post(
        "/rumbo/meta",
        json={"monto_min": 10000, "monto_max": 15000, "meses_seguidos": 6, "confirmada": True},
    ).json()
    assert confirmada["monto_min"] == 10000
    assert cliente.get("/rumbo").json()["meta"]["monto_max"] == 15000


def test_partida_trae_horas_medidas_reales(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    tarea = Tarea(
        id=uuid4(), titulo="algo", proyecto_id=None, estado="hoy", paso_minimo="paso",
        estimado_min=None, real_min=None, hora=None, fecha_limite=None,
    )
    db.crear_tarea(conexion, tarea)
    ahora = datetime.now(timezone.utc)
    sesion = Sesion(id=uuid4(), tarea_id=tarea.id, inicio=ahora - timedelta(hours=2), fin=ahora, real_min=120, app_contexto=None)
    db.crear_sesion(conexion, sesion)
    conexion.close()

    cliente = TestClient(servidor.app)
    partida = cliente.get("/rumbo").json()["partida"]
    horas = next(item for item in partida if item["texto"] == "Horas reales por semana")
    assert horas["valor"] == "2.0"
    assert horas["origen"] == "medido"

"""R4.5 (forma P): pronósticos y el recalibrador logístico (Metaculus
MIT, adaptado — ver LICENCIAS-TERCEROS.md)."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient

import calibracion
import db
import servidor
from modelos import Pronostico


def test_menos_de_10_resueltos_no_recalibra():
    assert calibracion.entrenar_recalibrador([0.5, 0.6], [True, False]) is None


def test_todos_el_mismo_resultado_no_recalibra():
    predicciones = [0.3 + 0.01 * i for i in range(12)]
    assert calibracion.entrenar_recalibrador(predicciones, [True] * 12) is None


def test_30_sinteticos_sesgados_al_si_bajan_las_probabilidades_y_sesgo_mayor_a_cero():
    rng = np.random.default_rng(7)
    q = rng.uniform(0.1, 0.9, size=30)
    outcomes = (rng.uniform(size=30) < q).tolist()
    logit_q = np.log(q / (1 - q))
    # BIA_true = 1.0: el que pronostica dice más «sí» de lo que en verdad pasa.
    p_dicho = 1 / (1 + np.exp(-(1.0 + logit_q)))

    recalibrador = calibracion.entrenar_recalibrador(p_dicho.tolist(), outcomes)
    assert recalibrador is not None
    assert recalibrador.bia > 0
    for p in (0.55, 0.7, 0.85):
        assert recalibrador.ajustar(p) < p


def test_endpoint_calibracion_sin_resueltos(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    r = cliente.get("/calibracion")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["resueltos"] == 0
    assert cuerpo["sesgo_si"] is None
    assert cuerpo["muestra_grafica"] is False


def test_crear_y_resolver_pronostico(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    ahora = datetime.now(timezone.utc)
    r = cliente.post(
        "/pronosticos",
        json={
            "que": "¿cierro la propuesta de Beam este mes?", "p": 0.6,
            "vence": (ahora + timedelta(days=20)).isoformat(), "regla_si_no": "si firma el contrato antes del 30",
            "tipo": "mundo", "origen": "manual",
        },
    )
    assert r.status_code == 201
    pronostico_id = r.json()["id"]

    r2 = cliente.post(f"/pronosticos/{pronostico_id}/resolver", json={"resultado": True})
    assert r2.status_code == 200

    conexion = db.conectar()
    try:
        pronostico = db.leer_pronostico(conexion, pronostico_id)
    finally:
        conexion.close()
    assert pronostico is not None
    assert pronostico.resultado is True


def test_muestra_grafica_desde_20_resueltos(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        for i in range(20):
            pronostico = Pronostico(
                id=uuid4(), que=f"pregunta {i}", p=0.5, vence=ahora, regla_si_no="x",
                tipo="mundo", origen="manual", resultado=(i % 2 == 0), creada_en=ahora,
            )
            db.crear_pronostico(conexion, pronostico)
    finally:
        conexion.close()

    cliente = TestClient(servidor.app)
    cuerpo = cliente.get("/calibracion").json()
    assert cuerpo["resueltos"] == 20
    assert cuerpo["muestra_grafica"] is True

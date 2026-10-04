"""R1: Rumbo — visión, meta, escalera y partida. Sin IA: `parsear_vision`
es una función pura; la meta real solo cambia con `confirmada: true`."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import db
import rumbo
import servidor
from modelos import Apuesta, Propuesta, Sesion, Tarea


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
        estimado_min=None, real_min=None, hora=None, fecha_limite=None, tipo=None,
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


# --- R2 (forma R): cuenta hacia atrás ---------------------------------


def test_parsear_propuesta_reconoce_cliente_y_monto():
    parseada = rumbo.parsear_propuesta("le mandé la propuesta a Alfonso por 1.500")
    assert parseada is not None
    assert parseada.cliente == "Alfonso"
    assert parseada.monto == 1500.0


def test_parsear_propuesta_sin_verbo_no_reconoce():
    assert rumbo.parsear_propuesta("Alfonso me debe 1.500") is None


def test_cuenta_con_ocho_propuestas_y_dos_cierres_da_cierre_025(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    cliente.post("/rumbo/meta", json={"monto_min": 10000, "monto_max": 15000, "meses_seguidos": 6, "confirmada": True})

    conexion = db.conectar()
    try:
        for i in range(8):
            estado = "cerrada" if i < 2 else "pendiente"
            db.crear_propuesta(
                conexion,
                Propuesta(id=uuid4(), cliente=f"cliente{i}", monto=1000.0, fecha=datetime.now(timezone.utc), estado=estado),
            )
    finally:
        conexion.close()

    cuenta = cliente.get("/rumbo/cuenta").json()
    assert cuenta["cierre"]["p"] == 0.25
    assert cuenta["cierre"]["origen"] == "propia"
    assert cuenta["cierre"]["base_n"] == 8
    assert cuenta["meta_mes"] == 12500
    assert cuenta["ticket"] == 1000
    assert cuenta["necesarias"] == 12.5
    assert cuenta["propuestas_semana"] == 8


def test_cuenta_con_menos_de_cinco_usa_tasa_general(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    conexion = db.conectar()
    try:
        db.crear_propuesta(
            conexion, Propuesta(id=uuid4(), cliente="x", monto=500.0, fecha=datetime.now(timezone.utc), estado="pendiente")
        )
    finally:
        conexion.close()
    cuenta = cliente.get("/rumbo/cuenta").json()
    assert cuenta["cierre"]["origen"] == "general"
    assert cuenta["cierre"]["base_n"] == 1


def test_registrar_propuesta_hablada_por_mensaje(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    r = cliente.post("/mensaje", json={"texto": "le mandé la propuesta a Beam por 2.000"})
    assert r.status_code == 200
    assert r.json()["tipo"] == "propuesta"
    cuenta = cliente.get("/rumbo/cuenta").json()
    assert cuenta["cierre"]["base_n"] == 1


# --- R2 (forma O): apuestas --------------------------------------------


def test_crear_y_ver_apuesta(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    ahora = datetime.now(timezone.utc)
    r = cliente.post(
        "/rumbo/apuestas",
        json={
            "camino": "malik_premium",
            "inicio": (ahora - timedelta(days=1)).isoformat(),
            "fin": (ahora + timedelta(days=59)).isoformat(),
            "tope_horas": 40,
            "tope_plata": 500,
        },
    )
    assert r.status_code == 201
    apuestas = cliente.get("/rumbo/apuestas").json()
    assert len(apuestas) == 1
    assert apuestas[0]["camino"] == "malik_premium"
    assert apuestas[0]["resultado"] is None
    assert apuestas[0]["gastado_horas"] == 0.0


def test_senal_pausa_cuando_se_pasa_el_tope_de_plata(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        apuesta = Apuesta(
            id=uuid4(), camino="malik_premium", inicio=ahora - timedelta(days=5), fin=ahora + timedelta(days=55),
            tope_horas=40, tope_plata=100, resultado=None,
        )
        db.crear_apuesta(conexion, apuesta)
        db.crear_gasto(conexion, "malik_premium", "ads", 150.0, ahora)
    finally:
        conexion.close()

    cliente = TestClient(servidor.app)
    vista = cliente.get("/rumbo/apuestas").json()[0]
    assert vista["gastado_plata"] == 150.0
    assert vista["senal_pausa"] is True
    assert vista["senal_sigue"] is False


def test_cerrar_apuesta(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        apuesta = Apuesta(
            id=uuid4(), camino="x", inicio=ahora, fin=ahora + timedelta(days=60),
            tope_horas=10, tope_plata=10, resultado=None,
        )
        db.crear_apuesta(conexion, apuesta)
        apuesta_id = str(apuesta.id)
    finally:
        conexion.close()

    cliente = TestClient(servidor.app)
    r = cliente.post(f"/rumbo/apuestas/{apuesta_id}/cerrar", json={"resultado": "pausa"})
    assert r.status_code == 200
    vista = cliente.get("/rumbo/apuestas").json()[0]
    assert vista["resultado"] == "pausa"


def test_apuesta_al_dia_14_produce_pregunta_de_tres_salidas(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        apuesta = Apuesta(
            id=uuid4(), camino="malik_premium", inicio=ahora - timedelta(days=14), fin=ahora + timedelta(days=46),
            tope_horas=40, tope_plata=500, resultado=None,
        )
        db.crear_apuesta(conexion, apuesta)
    finally:
        conexion.close()

    cliente = TestClient(servidor.app)
    cliente.get("/rumbo/apuestas")  # dispara revisar_apuestas_vencidas

    conexion = db.conectar()
    try:
        pregunta = db.pregunta_de_tema_campo(conexion, "_rumbo", f"apuesta_dia14::{apuesta.id}")
    finally:
        conexion.close()
    assert pregunta is not None
    assert "sigue" in pregunta.voz and "pausa" in pregunta.voz and "extiendes" in pregunta.voz

    # Una segunda vuelta no duplica la pregunta (ley 3).
    cliente.get("/rumbo/apuestas")
    conexion = db.conectar()
    try:
        preguntas_dia14 = conexion.execute(
            "SELECT COUNT(*) AS n FROM preguntas WHERE campo = ?", (f"apuesta_dia14::{apuesta.id}",)
        ).fetchone()["n"]
    finally:
        conexion.close()
    assert preguntas_dia14 == 1


# --- R5.3: poda mensual --------------------------------------------------


def test_todo_sin_uso_en_30_dias_propone_quitarlas(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        pregunta = rumbo.proponer_poda(conexion, ahora)
    finally:
        conexion.close()
    assert pregunta is not None
    assert "apuestas" in pregunta.voz


def test_con_actividad_reciente_no_propone_nada(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        db.crear_apuesta(
            conexion,
            Apuesta(id=uuid4(), camino="x", inicio=ahora, fin=ahora + timedelta(days=60), tope_horas=10, tope_plata=10, resultado=None),
        )
        db.crear_propuesta(conexion, Propuesta(id=uuid4(), cliente="x", monto=100.0, fecha=ahora, estado="pendiente"))
        pregunta = rumbo.proponer_poda(conexion, ahora)
    finally:
        conexion.close()
    # apuestas y propuestas tuvieron actividad; caminos y pronósticos no.
    assert pregunta is not None
    assert "apuestas" not in pregunta.voz
    assert "caminos" in pregunta.voz


def test_poda_no_se_repite_el_mismo_mes(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        primera = rumbo.proponer_poda(conexion, ahora)
        segunda = rumbo.proponer_poda(conexion, ahora + timedelta(hours=1))
    finally:
        conexion.close()
    assert primera is not None
    assert segunda is None

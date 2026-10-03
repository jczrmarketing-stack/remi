"""La conversación sigue hasta que Juan Camilo la cambie (3-oct): «si uno se va
a la cocina y vuelve, no empezamos otra conversación». Antes, 60 min sin
turnos abrían una nueva."""
from datetime import datetime, timedelta, timezone

import db

AHORA = datetime(2026, 10, 3, 6, 0, tzinfo=timezone.utc)


def _turno(texto, hace, rol="juan"):
    conexion = db.conectar()
    try:
        return db.guardar_turno(conexion, rol, texto, AHORA - hace)
    finally:
        conexion.close()


def test_tres_horas_despues_sigue_la_misma_conversacion():
    primera = _turno("hablemos de la fase 1", timedelta(hours=3))
    segunda = _turno("ya volví", timedelta(0))
    assert primera == segunda
    conexion = db.conectar()
    try:
        vigente = db.conversacion_vigente(conexion, AHORA)
        assert vigente is not None and vigente.id == primera
    finally:
        conexion.close()


def test_solo_empezar_de_cero_abre_otra():
    primera = _turno("hablemos de la fase 1", timedelta(minutes=5))
    conexion = db.conectar()
    try:
        db.cerrar_conversacion_vigente(conexion, AHORA)
    finally:
        conexion.close()
    assert _turno("otra cosa", timedelta(0)) != primera


def test_retomar_una_vieja_cierra_la_que_estaba():
    vieja = _turno("la vieja", timedelta(hours=5))
    conexion = db.conectar()
    try:
        db.cerrar_conversacion_vigente(conexion, AHORA - timedelta(hours=4))
    finally:
        conexion.close()
    actual = _turno("la actual", timedelta(minutes=10))
    conexion = db.conectar()
    try:
        db.retomar_conversacion(conexion, vieja, AHORA)
        abiertas = conexion.execute("SELECT id FROM conversaciones WHERE cerrada = 0").fetchall()
    finally:
        conexion.close()
    assert [f["id"] for f in abiertas] == [vieja]
    assert actual != vieja


def test_el_episodio_sale_cuando_la_cambia_no_por_tiempo():
    vigente = _turno("hablemos de la fase 1", timedelta(hours=3))
    conexion = db.conectar()
    try:
        assert db.conversaciones_para_cerrar(conexion, AHORA) == []  # sigue viva: nada
        db.cerrar_conversacion_vigente(conexion, AHORA)
        assert db.conversaciones_para_cerrar(conexion, AHORA) == [vigente]
    finally:
        conexion.close()


def test_la_charla_reciente_sigue_siendo_la_ultima_hora():
    """Para la Bandeja (T11.1): lo suelto de una charla no es idea solo
    mientras se está charlando, no para siempre."""
    _turno("hola", timedelta(hours=2))
    conexion = db.conectar()
    try:
        assert db.hay_charla_reciente(conexion, AHORA) is False
        db.guardar_turno(conexion, "juan", "sigo", AHORA - timedelta(minutes=10))
        assert db.hay_charla_reciente(conexion, AHORA) is True
    finally:
        conexion.close()

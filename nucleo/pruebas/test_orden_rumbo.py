"""R5.1: Hoy ordenado por el Rumbo."""
from datetime import datetime, timedelta, timezone

import orden_rumbo
from orden_rumbo import PropuestaHoy


def test_con_una_apuesta_activa_y_la_cuenta_en_1_de_2_sube_la_que_falta():
    propuestas = [
        PropuestaHoy(texto="responder un correo viejo", fecha_prometida=None, cumple_cuenta_semana=False, cumple_paso_apuesta=False, meta_estable_por_hora=5.0),
        PropuestaHoy(texto="mandar la propuesta que falta para la cuenta de la semana", fecha_prometida=None, cumple_cuenta_semana=True, cumple_paso_apuesta=False, meta_estable_por_hora=3.0),
        PropuestaHoy(texto="trabajar en la apuesta activa de malik_premium", fecha_prometida=None, cumple_cuenta_semana=False, cumple_paso_apuesta=True, meta_estable_por_hora=8.0),
    ]
    elegida = orden_rumbo.elegir(propuestas)
    assert elegida is not None
    # empate entre las dos de rumbo: gana la de más meta estable por hora.
    assert elegida.texto == "trabajar en la apuesta activa de malik_premium"
    assert "apuesta activa" in elegida.por_que


def test_fecha_prometida_gana_sobre_todo_lo_demas():
    ahora = datetime.now(timezone.utc)
    propuestas = [
        PropuestaHoy(texto="la de rumbo", fecha_prometida=None, cumple_cuenta_semana=True, cumple_paso_apuesta=False, meta_estable_por_hora=100.0),
        PropuestaHoy(texto="la que vence pronto", fecha_prometida=ahora + timedelta(days=1), cumple_cuenta_semana=False, cumple_paso_apuesta=False, meta_estable_por_hora=0.0),
    ]
    elegida = orden_rumbo.elegir(propuestas)
    assert elegida is not None
    assert elegida.texto == "la que vence pronto"
    assert "fecha" in elegida.por_que


def test_entre_dos_con_fecha_gana_la_mas_cercana():
    ahora = datetime.now(timezone.utc)
    propuestas = [
        PropuestaHoy(texto="lejos", fecha_prometida=ahora + timedelta(days=10), cumple_cuenta_semana=False, cumple_paso_apuesta=False, meta_estable_por_hora=0.0),
        PropuestaHoy(texto="cerca", fecha_prometida=ahora + timedelta(days=1), cumple_cuenta_semana=False, cumple_paso_apuesta=False, meta_estable_por_hora=0.0),
    ]
    elegida = orden_rumbo.elegir(propuestas)
    assert elegida is not None
    assert elegida.texto == "cerca"


def test_sin_fecha_ni_rumbo_gana_por_meta_estable_por_hora():
    propuestas = [
        PropuestaHoy(texto="paga poco por hora", fecha_prometida=None, cumple_cuenta_semana=False, cumple_paso_apuesta=False, meta_estable_por_hora=1.0),
        PropuestaHoy(texto="paga mucho por hora", fecha_prometida=None, cumple_cuenta_semana=False, cumple_paso_apuesta=False, meta_estable_por_hora=50.0),
    ]
    elegida = orden_rumbo.elegir(propuestas)
    assert elegida is not None
    assert elegida.texto == "paga mucho por hora"
    assert "por hora" in elegida.por_que


def test_sin_propuestas_no_elige_nada():
    assert orden_rumbo.elegir([]) is None

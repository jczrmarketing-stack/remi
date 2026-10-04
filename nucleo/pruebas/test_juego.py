"""R3: «Ábreme el juego». El generador es un doble en todos los casos —
nunca una llamada real al modelo en pytest."""
from datetime import datetime, timezone

import juego
from juego import JugadaCruda


def test_descarta_palabras_de_moda():
    crudas = [
        JugadaCruda(texto="Un ecosistema disruptivo de clientes", lente=1),
        JugadaCruda(texto="Subir el precio del paquete mensual", lente=2),
    ]
    filtradas = juego.filtrar_jugadas(crudas)
    textos = [j.texto for j in filtradas]
    assert "Un ecosistema disruptivo de clientes" not in textos
    assert "Subir el precio del paquete mensual" in textos


def test_descarta_repetidas_por_similitud():
    crudas = [
        JugadaCruda(texto="Subir el precio del paquete mensual a todos los clientes", lente=1),
        JugadaCruda(texto="Subir el precio del paquete mensual a todos los clientes nuevos", lente=1),
    ]
    filtradas = juego.filtrar_jugadas(crudas)
    # Las dos son casi idénticas: sobrevive una sola, más la fija que
    # cuestiona la meta (ninguna de las dos originales lo hacía).
    assert len(filtradas) == 2


def test_siempre_hay_una_que_cuestiona_la_meta():
    crudas = [JugadaCruda(texto="Subir el precio", lente=1), JugadaCruda(texto="Bajar el precio", lente=2)]
    filtradas = juego.filtrar_jugadas(crudas)
    assert any("?" in j.texto and "meta" in j.texto.lower() for j in filtradas)
    assert len(filtradas) == 3  # las 2 + la fija


def test_si_ya_hay_una_que_cuestiona_la_meta_no_agrega_otra():
    crudas = [JugadaCruda(texto="¿Y si la meta real debería ser otra?", lente=None)]
    filtradas = juego.filtrar_jugadas(crudas)
    assert len(filtradas) == 1


def test_generar_jugadas_usa_el_generador_inyectado():
    llamadas = []

    def generador_doble() -> list[JugadaCruda]:
        llamadas.append(1)
        return [JugadaCruda(texto="Jugada de prueba", lente=3)]

    jugadas = juego.generar_jugadas(generador_doble)
    assert len(llamadas) == 1
    assert jugadas[0].texto == "Jugada de prueba"


def test_jugadas_a_ideas_van_a_la_bandeja_con_origen_rumbo():
    ahora = datetime.now(timezone.utc)
    jugadas = [JugadaCruda(texto="Una jugada", lente=2)]
    ideas = juego.jugadas_a_ideas(jugadas, ahora)
    assert len(ideas) == 1
    assert ideas[0].origen == "rumbo"
    assert ideas[0].estado == "enfriando"
    assert ideas[0].problema_vision == 2
    assert ideas[0].enfria_hasta > ahora

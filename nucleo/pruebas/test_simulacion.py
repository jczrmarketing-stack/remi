"""R4.4: simulación de seis meses, sembrada."""
import simulacion


def test_misma_semilla_da_las_mismas_bandas():
    r1 = simulacion.simular(media_mensual=2000, desviacion_mensual=500, umbral=10000, semilla=42)
    r2 = simulacion.simular(media_mensual=2000, desviacion_mensual=500, umbral=10000, semilla=42)
    assert r1.bandas == r2.bandas
    assert r1.frecuencia == r2.frecuencia
    assert r1.ruina_de_10 == r2.ruina_de_10


def test_semillas_distintas_pueden_dar_bandas_distintas():
    r1 = simulacion.simular(media_mensual=2000, desviacion_mensual=500, umbral=10000, semilla=1)
    r2 = simulacion.simular(media_mensual=2000, desviacion_mensual=500, umbral=10000, semilla=2)
    assert r1.bandas != r2.bandas


def test_bandas_ordenadas_probable_menor_o_igual_que_techo():
    r = simulacion.simular(media_mensual=2000, desviacion_mensual=500, umbral=10000, semilla=3)
    assert r.bandas.probable <= r.bandas.posible <= r.bandas.techo


def test_la_plata_nunca_es_negativa_en_la_banda_probable():
    # media muy baja, desviación muy alta: si no se recortara en 0, el
    # total podría salir negativo.
    r = simulacion.simular(media_mensual=10, desviacion_mensual=5000, umbral=100, semilla=5)
    assert r.bandas.probable >= 0


def test_kelly_tope_cero_sin_borde():
    assert simulacion.kelly_tope(probabilidad=0.4, ganancia_neta=1.0, perdida_neta=1.0) == 0.0


def test_kelly_tope_positivo_con_borde_claro():
    tope = simulacion.kelly_tope(probabilidad=0.7, ganancia_neta=1.0, perdida_neta=1.0)
    assert 0.0 < tope <= 1.0

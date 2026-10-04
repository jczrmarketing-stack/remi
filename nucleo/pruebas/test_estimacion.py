"""R4.1-R4.3: números honestos. Los estimadores/críticos son dobles —
nunca una llamada real de pago en pytest."""
import estimacion
from estimacion import Critica


def test_mediana_de_tres_estimaciones_02_03_09():
    assert estimacion.combinar_a_ciegas([0.2, 0.3, 0.9]) == 0.3


def test_mediana_no_se_mueve_por_un_extremo():
    # un valor rarísimo no debe mover la mediana como movería un promedio.
    normal = estimacion.combinar_a_ciegas([0.3, 0.32, 0.31])
    con_extremo = estimacion.combinar_a_ciegas([0.3, 0.32, 0.31, 0.99])
    assert abs(normal - con_extremo) < 0.02


def test_estimar_a_ciegas_llama_cada_estimador_una_vez():
    llamadas = []

    def modelo_a() -> float:
        llamadas.append("a")
        return 0.4

    def modelo_b() -> float:
        llamadas.append("b")
        return 0.6

    resultado = estimacion.estimar_a_ciegas([modelo_a, modelo_b])
    assert resultado == [0.4, 0.6]
    assert llamadas == ["a", "b"]


def test_mezclar_con_pesos_fijos():
    # pesos (0.5, 0.3, 0.2): modelos 0.5, base 0.0, propio 1.0.
    mezcla = estimacion.mezclar(mediana_modelos=0.5, tasa_base=0.0, estimado_propio=1.0, pesos=(0.5, 0.3, 0.2))
    assert abs(mezcla - (0.5 * 0.5 + 0.0 * 0.3 + 1.0 * 0.2)) < 1e-9


def test_mezclar_normaliza_pesos_que_no_suman_uno():
    mezcla_doble = estimacion.mezclar(mediana_modelos=1.0, tasa_base=0.0, estimado_propio=0.0, pesos=(1.0, 0.0, 0.0))
    mezcla_doble_x2 = estimacion.mezclar(mediana_modelos=1.0, tasa_base=0.0, estimado_propio=0.0, pesos=(2.0, 0.0, 0.0))
    assert abs(mezcla_doble - mezcla_doble_x2) < 1e-9


def test_necesita_segunda_ronda_solo_si_toca_un_supuesto_real():
    supuestos = {"la meta sigue siendo 10 mil", "el ticket promedio es 1500"}
    sin_tocar = [Critica(autor="A", problemas=["el plazo es corto"])]
    assert estimacion.necesita_segunda_ronda(sin_tocar, supuestos) is False

    tocando = [Critica(autor="abogado_del_diablo", problemas=["la meta sigue siendo 10 mil", "otra cosa"])]
    assert estimacion.necesita_segunda_ronda(tocando, supuestos) is True

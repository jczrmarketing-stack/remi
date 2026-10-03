"""Si piden un prompt y el modelo solo pregunta, el prompt sale igual.

El 3-oct la frase del carácter no alcanzó: Haiku y Sonnet abrieron con
«¿qué es X?». La regla corre después del modelo, antes de guardar y de
hablar. Pura: no llama a nadie.
"""
from __future__ import annotations

import concreto
import pensar


def _palabras_antes_de_preguntar(texto: str) -> int:
    return len(texto.split("?", 1)[0].split())


def test_pide_prompt_reconoce_el_pedido_concreto():
    assert concreto.pide_prompt("dame un prompt para preguntarle X a Grok")
    assert concreto.pide_prompt("Hazme un prompt para el encargo.")
    assert not concreto.pide_prompt("¿qué hora es?")
    assert not concreto.pide_prompt("gracias por el dato")
    assert not concreto.pide_prompt("el prompt de ayer quedó corto")


def test_entrega_primero_exige_doce_palabras_antes_de_la_pregunta():
    largo = "Prompt para copiar: pregúntale a Grok el mecanismo y deja el hueco marcado en el texto."
    assert concreto.entrega_primero(largo)
    assert concreto.entrega_primero(largo + " ¿Falta algo?")
    assert not concreto.entrega_primero("¿Qué es X?")
    assert not concreto.entrega_primero("Dame el tema y te armo el prompt.")


def test_si_ya_entrego_no_se_toca():
    pedido = "dame un prompt para preguntarle X a Grok"
    respuesta = (
        "Prompt para copiar: pregúntale a Grok qué es X y marca el hueco "
        "donde falte el dato. ¿Quieres otro tono?"
    )
    assert concreto.concreto_primero(pedido, respuesta) == respuesta


def test_si_solo_pregunta_el_prompt_va_primero_y_la_pregunta_queda():
    pedido = "dame un prompt para preguntarle X a Grok"
    respuesta = "¿Qué es X?"
    salida = concreto.concreto_primero(pedido, respuesta)
    assert salida.index("Prompt para copiar:") < salida.index("¿Qué es X?")
    assert "Preguntarle X a Grok" in salida
    assert _palabras_antes_de_preguntar(salida) >= 12
    assert concreto.concreto_primero(pedido, salida) == salida


def test_un_pedido_que_no_es_prompt_se_queda_igual():
    respuesta = "¿Qué es X?"
    assert concreto.concreto_primero("gracias por el dato", respuesta) == respuesta


def test_pensar_en_vivo_no_suelta_la_pregunta_antes_del_prompt(monkeypatch):
    monkeypatch.setattr(pensar, "_indice", lambda: [])

    def entero(*_a, **_k):
        return pensar.Pensado("¿Qué es la X que quieres preguntarle?", 3, 9, "haiku")

    def no_en_vivo(*_a, **_k):
        raise AssertionError("el stream no debe soltar la pregunta antes del prompt")

    monkeypatch.setattr(pensar, "_respuesta_entera_del_motor", entero)
    monkeypatch.setattr(pensar, "_frases_del_motor", no_en_vivo)

    frases = []
    generador = pensar.pensar_en_frases(
        "dame un prompt para preguntarle X a Grok", "claude", "rapido", en_vivo=True
    )
    try:
        while True:
            frases.append(next(generador))
    except StopIteration as fin:
        pensado = fin.value

    assert pensado is not None
    texto = pensado.paso_minimo
    assert _palabras_antes_de_preguntar(texto) >= 12
    assert "Prompt para copiar:" in texto
    assert "¿Qué es la X que quieres preguntarle?" in texto
    assert frases
    assert "¿Qué es la X" not in frases[0]
    assert pensar._turnos()[-1].texto == texto

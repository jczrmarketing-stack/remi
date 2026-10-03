"""El voseo se va con una regla, no con el prompt (3-oct).

Veinte frases son de la charla de hoy, tal como quedaron en los turnos.
Veinte normales no tienen voseo: «además», «después», «país», «estás» y
el futuro («hablarás», «verás») tienen que salir iguales.
"""
from __future__ import annotations

import voseo
import pensar


# Charla del 3-oct, turnos de Remi. Cada una trae al menos una forma de vos.
_DEL_LOG = [
    ("¿Qué necesitás?", "¿Qué necesitas?"),
    (
        "Mirá los últimos turnos: me preguntaste tres veces si te escuchaba, y después me dijiste «cuando baja la bolita el texto debe desaparecer» sin decirme de cuál proyecto.",
        "Mira los últimos turnos: me preguntaste tres veces si te escuchaba, y después me dijiste «cuando baja la bolita el texto debe desaparecer» sin decirme de cuál proyecto.",
    ),
    (
        "Esto es lo que funciona: cuando tenés algo que arreglar, decime de una el proyecto, qué ves ahora y qué querés que pase.",
        "Esto es lo que funciona: cuando tienes algo que arreglar, dime de una el proyecto, qué ves ahora y qué quieres que pase.",
    ),
    ("¿Cuál es el proyecto y qué querés arreglar?", "¿Cuál es el proyecto y qué quieres arreglar?"),
    (
        "Dale con una frase: qué ves ahora y qué querés que pase.",
        "Dale con una frase: qué ves ahora y qué quieres que pase.",
    ),
    (
        "Pero aquí hay algo que ya tenés: yo ya traigo todo el iceberg completo a cada conversación.",
        "Pero aquí hay algo que ya tienes: yo ya traigo todo el iceberg completo a cada conversación.",
    ),
    (
        "Cuando arrancás conmigo, tengo precargado (nivel 2 en el sistema).",
        "Cuando arrancas conmigo, tengo precargado (nivel 2 en el sistema).",
    ),
    (
        "es que vos no me lo estás trayendo a mano.",
        "es que tú no me lo estás trayendo a mano.",
    ),
    (
        "Cuando decís algo, yo no sé si es de Malik, de UpVisuals o de Remi mismo.",
        "Cuando dices algo, yo no sé si es de Malik, de UpVisuals o de Remi mismo.",
    ),
    (
        "Lo que necesitás es decirme el proyecto y una frase del problema.",
        "Lo que necesitas es decirme el proyecto y una frase del problema.",
    ),
    ("¿Qué sentís con todo esto?", "¿Qué sientes con todo esto?"),
    (
        "Cuando sé que vos necesitás que alguien te diga eso, en lugar de solo hacer lo que pedís, pienso distinto.",
        "Cuando sé que tú necesitas que alguien te diga eso, en lugar de solo hacer lo que pides, pienso distinto.",
    ),
    (
        "me ayudó a saber quién sos vos de verdad, no solo lo que está escrito.",
        "me ayudó a saber quién eres tú de verdad, no solo lo que está escrito.",
    ),
    (
        "El TDAH, lo que soltás a mitad, cuándo te importa algo de verdad.",
        "El TDAH, lo que sueltas a mitad, cuándo te importa algo de verdad.",
    ),
    ("si solo querés seguir conversando, me aviso.", "si solo quieres seguir conversando, me aviso."),
    (
        "cuándo necesitás que te frene y cuándo necesitás que te siga.",
        "cuándo necesitas que te frene y cuándo necesitas que te siga.",
    ),
    (
        "¿Sentís que algo cambió, o es que querés confirmar que estoy aquí de verdad y no solo simulando?",
        "¿Sientes que algo cambió, o es que quieres confirmar que estoy aquí de verdad y no solo simulando?",
    ),
    (
        'Dijiste "Gracias" dos veces seguidas sin decir qué querés.',
        'Dijiste "Gracias" dos veces seguidas sin decir qué quieres.',
    ),
    (
        "copias esto en X y se lo mandás a @grok",
        "copias esto en X y se lo mandas a @grok",
    ),
    (
        "¿querés que después de tener eso, yo rediseñe cómo hablo contigo, o solo querés guardar la investigación para analizar después?",
        "¿quieres que después de tener eso, yo rediseñe cómo hablo contigo, o solo quieres guardar la investigación para analizar después?",
    ),
]

# Cero voseo. Si alguna letra cambia, es un falso positivo.
_NORMALES = [
    "Además, después del país viene la ciudad.",
    "Estás asumiendo que adivino el proyecto.",
    "Hablarás con él mañana si quieres.",
    "El interés atraviesa el francés y el inglés.",
    "Más atrás, jamás, detrás de la casa.",
    "París tiene maíz y una raíz en el cuento.",
    "Quizás el compás del cortés no es el revés.",
    "Tú tienes el dato y puedes seguir.",
    "Dime cómo lo quieres y lo hago.",
    "La última vez esto te tomó cuarenta minutos.",
    "Hoy solo esto: la tarjeta. Cinco minutos.",
    "Gracias por el dato, lo anoto.",
    "¿Verificaste ya que el token está vigente?",
    "El código está a mitad y los tests no cierran.",
    "Acá estoy, listo para el siguiente paso.",
    "No urges: quitas fricción, no sumas miedo.",
    "Verás el resultado cuando termine el núcleo.",
    "Demás está decir que el ananás no entra.",
    "A través del portugués el interés cambia.",
    "Después de además, el país sigue ahí y estás bien.",
]


def test_veinte_frases_del_log_salen_de_tu():
    assert len(_DEL_LOG) == 20
    for cruda, de_tu in _DEL_LOG:
        assert voseo.voseo_a_tu(cruda) == de_tu


def test_veinte_frases_normales_no_cambian():
    assert len(_NORMALES) == 20
    for frase in _NORMALES:
        assert voseo.voseo_a_tu(frase) == frase


def test_aplicarla_dos_veces_no_cambia_nada():
    for cruda, de_tu in _DEL_LOG:
        assert voseo.voseo_a_tu(de_tu) == de_tu
        assert voseo.voseo_a_tu(voseo.voseo_a_tu(cruda)) == de_tu
    for frase in _NORMALES:
        assert voseo.voseo_a_tu(voseo.voseo_a_tu(frase)) == frase


def test_respeta_mayusculas_y_no_toca_vosotros():
    assert voseo.voseo_a_tu("NECESITÁS") == "NECESITAS"
    assert voseo.voseo_a_tu("Mirá.") == "Mira."
    assert voseo.voseo_a_tu("con vosotros") == "con vosotros"


def _recoger(frases):
    salida = []
    try:
        while True:
            salida.append(next(frases))
    except StopIteration as fin:
        return salida, fin.value


def test_cada_frase_del_stream_sale_de_tu_antes_de_mostrarla():
    def deltas():
        yield "Cuando tenés algo que arreglar, decime. "
        yield "¿Qué querés?"
        return None

    frases, _ = _recoger(pensar._en_frases(deltas()))
    assert frases == [
        "Cuando tienes algo que arreglar, dime.",
        "¿Qué quieres?",
    ]


def test_la_salida_de_pensar_sale_de_tu(monkeypatch):
    crudo = pensar.Pensado(
        paso_minimo="¿Qué necesitás? Cuando tenés tiempo, decime.",
        tokens_entrada=1,
        tokens_salida=1,
        modelo="haiku",
    )
    monkeypatch.setattr(pensar, "_respuesta_entera_del_motor", lambda *a, **k: crudo)
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    monkeypatch.setattr(pensar, "_asociados", lambda _f: [])
    monkeypatch.setattr(pensar, "_tema_dudoso", lambda _f: None)
    monkeypatch.setattr(pensar, "_precarga", lambda: None)
    monkeypatch.setattr(pensar, "_conversacion", lambda: ([], ""))
    monkeypatch.setattr(pensar, "_guardar_turno", lambda *a, **k: "id")
    monkeypatch.setattr(pensar, "_actualizar_resumen_en_segundo_plano", lambda *a, **k: None)
    monkeypatch.setattr(pensar, "_cerrar_conversaciones_inactivas_en_segundo_plano", lambda: None)

    pensado = pensar.pensar("dame el dato")
    assert pensado is not None
    assert pensado.paso_minimo == "¿Qué necesitas? Cuando tienes tiempo, dime."

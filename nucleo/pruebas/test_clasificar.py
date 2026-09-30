"""El clasificador: sin IA, puro, y con el español que se escribe de verdad."""
import pytest

from clasificar import clasificar, normalizar

# — Las frases de la auditoría de Grok, tal cual —


@pytest.mark.parametrize(
    "frase",
    [
        "pare un segundo",
        "la dejo hecha manana",
        "quedo listo",
        "listo el contrato",
        "hoy no puedo",
        "se me ocurrio q hoy armo un curso",
        "voy a ver si armo el curso",
    ],
)
def test_grok_idea(frase):
    assert clasificar(frase) == "idea"


@pytest.mark.parametrize(
    "frase",
    ["me pongo con la propuesta", "arranque con alfonso", "sigo con la factura"],
)
def test_grok_hoy(frase):
    assert clasificar(frase) == "hoy"


@pytest.mark.parametrize("frase", ["ya esta", "listo", "Terminé!!"])
def test_grok_hecha(frase):
    assert clasificar(frase) == "hecha"


# — La guarda de negación de antes —


@pytest.mark.parametrize(
    "frase, esperado",
    [
        ("no me quedó listo", "idea"),
        ("todavía no termino", "idea"),
        ("nunca lo terminé", "idea"),
        ("tampoco está listo", "idea"),
        ("listo", "hecha"),
        ("ya terminé", "hecha"),
    ],
)
def test_guarda_de_negacion(frase, esperado):
    assert clasificar(frase) == esperado


# — Cierres: exactos o nada —


@pytest.mark.parametrize(
    "frase",
    ["listo", "Listo!", "LISTO", "hecha", "hecho", "paro", "paré", "ya estuvo", "hasta acá", "cerrado", "ya está"],
)
def test_cierra_solo_con_la_palabra_exacta(frase):
    assert clasificar(frase) == "hecha"


@pytest.mark.parametrize(
    "frase",
    [
        # Mencionan un cierre, no lo dicen. Antes cerraban por «≤3 palabras más».
        "listo la tarjeta",
        "Terminé la tarjeta",
        "listo por hoy",
        "cuando esté listo el informe te aviso",
    ],
)
def test_mencionar_un_cierre_no_cierra(frase):
    assert clasificar(frase) == "idea"


# — Arranques: al principio, con prefijo opcional —


@pytest.mark.parametrize(
    "frase",
    [
        "voy a escribir la propuesta ahora",
        "voy a revisar el contrato",
        "arranco con la landing",
        "empiezo por el formulario",
        "empecé con el informe",
        "vamos con las facturas",
        "VOY A LLAMAR AL BANCO",
        "ahora voy a revisar los proxies",
        "hoy me pongo con el presupuesto",
        "ya arranco con esto",
    ],
)
def test_abre_un_bloque(frase):
    assert clasificar(frase) == "hoy"


@pytest.mark.parametrize(
    "frase",
    [
        # «hoy» y «ahora» sueltos ya no abren.
        "hoy toca el informe",
        "ahora reviso los proxies",
        "hoy tengo q mandar el presupuesto",
        # El arranque tiene que estar al principio.
        "creo que voy a revisar el contrato",
        # Frenos.
        "voy a ver si llego",
        "quizas arranco con esto",
        "a lo mejor me pongo con la propuesta",
        "arranco con la idea del curso",
        # Lo suelto de siempre.
        "se me ocurrió vender plantillas",
        "y si hacemos un bot de whatsapp para la agencia",
        "",
        "   ",
    ],
)
def test_lo_demas_enfria_como_idea(frase):
    assert clasificar(frase) == "idea"


def test_normalizar_saca_tildes_signos_y_mayusculas():
    assert normalizar("¡TERMINÉ!") == "termine"
    assert normalizar("Añadir más") == "anadir mas"
    assert normalizar("  hola,   qué tal?  ") == "hola que tal"
    assert normalizar("") == ""


# — Preguntas: se contestan, no se guardan —


@pytest.mark.parametrize(
    "frase",
    [
        "¿qué tengo pendiente con Alfonso?",
        "¿y cuándo arranco?",
        "¿listo?",
        "listo?",
        "¿ya está?",
        "¿voy a llegar al 18?",
        "y cuanto me falta cobrar",
        "donde quedó el contrato de Alfonso",
        "por que no me entiende el microfono",
    ],
)
def test_una_pregunta_es_pregunta(frase):
    assert clasificar(frase) == "pregunta"


@pytest.mark.parametrize(
    "frase, esperado",
    [
        ("que no se me olvide llamar al banco", "idea"),
        ("cuando esté listo el informe te aviso", "idea"),
        ("para que no se me olvide el dominio", "idea"),
        ("como va lo de malik", "idea"),
        ("se me ocurrió cuánto cobrar por el curso", "idea"),
        ("listo", "hecha"),
        ("voy a revisar el contrato", "hoy"),
    ],
)
def test_sin_signos_ni_arranque_interrogativo_no_es_pregunta(frase, esperado):
    assert clasificar(frase) == esperado

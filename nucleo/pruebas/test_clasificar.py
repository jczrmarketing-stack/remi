"""El clasificador: sin IA, puro, y con el español que se escribe de verdad."""
import pytest

from clasificar import clasificar, normalizar


@pytest.mark.parametrize(
    "frase",
    [
        "listo",
        "Listo!",
        "LISTO",
        "terminé",
        "termine",
        "Terminé la tarjeta",
        "hecha",
        "paro",
        "paré",
        "listo por hoy",
    ],
)
def test_cierra_el_bloque(frase):
    assert clasificar(frase) == "hecha"


@pytest.mark.parametrize(
    "frase",
    [
        "voy a escribir la propuesta ahora",
        "voy a revisar el contrato",
        "arranco con la landing",
        "empiezo por el formulario",
        "vamos con las facturas",
        "hoy toca el informe",
        "ahora reviso los proxies",
        # Español coloquial: sin tildes, con «q», en mayúsculas.
        "VOY A LLAMAR AL BANCO",
        "hoy tengo q mandar el presupuesto",
        "ahora si arranco con esto",
    ],
)
def test_abre_un_bloque_hoy(frase):
    assert clasificar(frase) == "hoy"


@pytest.mark.parametrize(
    "frase",
    [
        "se me ocurrió vender plantillas",
        "se me ocurrio una app de recetas",
        "y si hacemos un bot de whatsapp para la agencia",
        "estaria bueno cobrar por suscripcion",
        "podriamos migrar todo a kiplink",
        "anotar q el dominio vence en octubre",
        "una idea: newsletter semanal",
        "",
        "   ",
        # Menciona «listo» pero es una frase larga: no cierra nada.
        "todavia no esta listo el flujo de pagos de la tienda",
    ],
)
def test_lo_demas_enfria_como_idea(frase):
    assert clasificar(frase) == "idea"


def test_una_frase_larga_no_cierra_por_mencionar_listo():
    """La ley 1 depende de que «listo» cierre de verdad un bloque; si
    cerrara con cualquier frase que lo mencione, el historial mentiría."""
    assert clasificar("listo") == "hecha"
    assert clasificar("listo el informe") == "hecha"
    assert clasificar("cuando esté listo el informe te aviso") == "idea"


def test_hecha_gana_sobre_hoy():
    """«listo por hoy» cierra: primero se mira si cierra, después si abre."""
    assert clasificar("listo por hoy") == "hecha"


def test_normalizar_saca_tildes_signos_y_mayusculas():
    assert normalizar("¡TERMINÉ!") == "termine"
    assert normalizar("Añadir más") == "anadir mas"
    assert normalizar("  hola,   qué tal?  ") == "hola que tal"
    assert normalizar("") == ""

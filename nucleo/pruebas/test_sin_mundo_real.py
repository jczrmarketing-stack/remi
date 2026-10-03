"""F4.2: la guarda de conftest corta Telegram, Notion y el núcleo real.
(El token de la URL nunca se imprime: el registro guarda solo el host.)"""
import httpx
import pytest

import conftest


@pytest.mark.mundo_real_esperado
@pytest.mark.parametrize(
    "url",
    [
        "https://api.telegram.org/botTOKEN/getUpdates",
        "https://api.notion.com/v1/users/me",
        "http://127.0.0.1:4400/salud",
        "http://localhost:4400/salud",
    ],
)
def test_la_guarda_corta_y_anota(url):
    with pytest.raises(conftest.MundoRealProhibido):
        httpx.get(url, timeout=1)
    assert len(conftest._INTENTOS_AL_MUNDO_REAL) == 1
    assert "TOKEN" not in conftest._INTENTOS_AL_MUNDO_REAL[0]


def test_lo_que_no_es_el_mundo_real_pasa():
    # Otro puerto local: la guarda no lo toca (no hay nadie, así que falla
    # por conexión, no por la guarda).
    with pytest.raises(httpx.HTTPError) as error:
        httpx.get("http://127.0.0.1:1/x", timeout=0.5)
    assert not isinstance(error.value, conftest.MundoRealProhibido)

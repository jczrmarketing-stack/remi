import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar_servidor():
    for nombre in ("servidor", "db", "modelos", "tts"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


# — Elegir voz: español salvo que el texto sea claramente inglés —


def test_el_prefijo_de_la_voz_marca_el_idioma():
    import tts

    assert tts.lang_code("em_alex") == "e"
    assert tts.lang_code("ef_dora") == "e"
    assert tts.lang_code("af_bella") == "a"


def test_auto_elige_espanol_para_la_voz_de_remi():
    import tts

    assert tts.elegir_voz("Hoy solo esto: la tarjeta. Cinco minutos.") == tts.VOZ_ES
    assert tts.elegir_voz("Abre el registrador y busca renovar dominio.") == tts.VOZ_ES
    # Ante la duda (una palabra suelta, sin señas), español: es el locale.
    assert tts.elegir_voz("Kiplink") == tts.VOZ_ES


def test_auto_elige_ingles_solo_si_el_texto_lo_es():
    import tts

    assert tts.elegir_voz("Hi, I'm Remi. I'm listening.") == tts.VOZ_EN
    assert tts.elegir_voz("Open the file and check that the tests pass now.") == tts.VOZ_EN


def test_una_voz_pedida_a_mano_gana_sobre_el_texto():
    import tts

    assert tts.resolver_voz("af_bella", "Hola, soy Remi.") == "af_bella"
    assert tts.resolver_voz("auto", "Hola, soy Remi.") == tts.VOZ_ES
    assert tts.resolver_voz(None, "Hola, soy Remi.") == tts.VOZ_ES
    assert tts.resolver_voz("no_existe", "Hola") is None


# — El endpoint —


def test_las_voces_son_exactamente_las_cuatro(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    cliente = TestClient(servidor.app)

    voces = cliente.get("/tts/voices").json()
    assert [v["id"] for v in voces] == ["em_alex", "ef_dora", "em_santa", "af_bella"]
    assert [v["label"] for v in voces] == ["Alex (ES)", "Dora (ES)", "Santa (ES)", "Bella (EN)"]
    assert [v["lang"] for v in voces] == ["es", "es", "es", "en"]


def test_devuelve_el_wav_y_dice_que_voz_uso(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    visto = {}

    def falsa_sintesis(texto, voz_id, velocidad=1.0):
        visto.update(texto=texto, voz_id=voz_id, velocidad=velocidad)
        return b"RIFF....WAVEfmt "

    monkeypatch.setattr(servidor.tts, "sintetizar", falsa_sintesis)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/tts", json={"text": "Hoy solo esto: la tarjeta."})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "audio/wav"
    assert respuesta.headers["x-remi-voz"] == "em_alex"
    assert respuesta.content == b"RIFF....WAVEfmt "
    # Se genera a 1.0: el estirado lo hace el reproductor, que conserva el tono.
    assert visto["velocidad"] == 1.0


def test_una_voz_a_mano_llega_al_motor(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    visto = {}
    monkeypatch.setattr(
        servidor.tts,
        "sintetizar",
        lambda texto, voz_id, velocidad=1.0: (visto.update(voz=voz_id), b"wav")[1],
    )
    cliente = TestClient(servidor.app)

    cliente.post("/tts", json={"text": "Hola", "voice": "em_santa"})
    assert visto["voz"] == "em_santa"


def test_texto_vacio_no_llama_al_motor(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()

    def explota(*_a, **_k):
        raise AssertionError("no debía sintetizar")

    monkeypatch.setattr(servidor.tts, "sintetizar", explota)
    cliente = TestClient(servidor.app)

    assert cliente.post("/tts", json={"text": "   "}).status_code == 204


def test_voz_desconocida_es_400_y_no_se_habla(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()

    def explota(*_a, **_k):
        raise AssertionError("no debía sintetizar")

    monkeypatch.setattr(servidor.tts, "sintetizar", explota)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/tts", json={"text": "Hola", "voice": "ninguna"})
    assert respuesta.status_code == 400
    # El detalle es para el log, no para decirlo en voz alta.
    assert respuesta.headers["content-type"].startswith("application/json")


def test_si_el_motor_falla_devuelve_503_sin_cuerpo(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    monkeypatch.setattr(servidor.tts, "sintetizar", lambda *_a, **_k: None)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/tts", json={"text": "Hola"})
    assert respuesta.status_code == 503
    assert respuesta.content == b""


def test_importar_el_servidor_no_carga_el_modelo(tmp_path, monkeypatch):
    """300 MB no se cargan por importar: el precalentado vive en __main__."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    _arrancar_servidor()
    import tts

    assert tts._pipelines == {}


def test_el_precalentado_corre_con_el_servidor_no_solo_con_python_servidor(tmp_path, monkeypatch):
    """launchd levanta `uvicorn servidor:app`, así que `__main__` nunca
    corre. Si el precalentado viviera ahí, Remi arrancaría siempre con la
    voz fría y la primera frase la diría el sistema."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_TTS_PRECALENTAR", "1")
    # F4.2b: con la base en una copia, el ciclo de vida exige la bóveda aislada.
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    servidor = _arrancar_servidor()
    llamadas = []
    monkeypatch.setattr(servidor.tts, "precalentar", lambda: llamadas.append(True))

    # Entrar al contexto del TestClient es lo que dispara el ciclo de vida.
    with TestClient(servidor.app):
        pass
    assert llamadas == [True]


def test_se_puede_apagar_el_precalentado(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_TTS_PRECALENTAR", "0")
    # F4.2b: con la base en una copia, el ciclo de vida exige la bóveda aislada.
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    servidor = _arrancar_servidor()
    llamadas = []
    monkeypatch.setattr(servidor.tts, "precalentar", lambda: llamadas.append(True))

    with TestClient(servidor.app):
        pass
    assert llamadas == []

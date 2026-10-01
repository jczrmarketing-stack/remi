"""conexiones.py: lista blanca, .env atómico, nunca un valor completo."""
import httpx
import pytest

import conexiones


def _env(tmp_path, monkeypatch, texto: str):
    ruta = tmp_path / ".env"
    ruta.write_text(texto)
    monkeypatch.setattr(conexiones, "RUTA_ENV", ruta)
    conexiones._ULTIMA_PRUEBA.clear()
    return ruta


ENV_ORIGINAL = """\
# Claves de Remi. No entra al repo.
REMI_PENSADOR=venice

VENICE_API_KEY=vieja-clave-venice
TELEGRAM_TOKEN=1234567890:abcdefghijklmnop
"""


def test_guardar_conserva_comentarios_y_lineas_ajenas(tmp_path, monkeypatch):
    ruta = _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    conexiones.guardar("TELEGRAM_TOKEN", "999:nuevotoken")

    texto = ruta.read_text()
    assert "# Claves de Remi. No entra al repo." in texto
    assert "REMI_PENSADOR=venice" in texto
    assert "VENICE_API_KEY=vieja-clave-venice" in texto
    assert "TELEGRAM_TOKEN=999:nuevotoken" in texto
    assert "TELEGRAM_TOKEN=1234567890:abcdefghijklmnop" not in texto


def test_guardar_un_nombre_nuevo_lo_agrega(tmp_path, monkeypatch):
    ruta = _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    conexiones.guardar("GROQ_API_KEY", "gsk-nueva")
    assert "GROQ_API_KEY=gsk-nueva" in ruta.read_text()


def test_guardar_vacio_quita_la_linea(tmp_path, monkeypatch):
    ruta = _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    conexiones.guardar("TELEGRAM_TOKEN", "")
    texto = ruta.read_text()
    assert "TELEGRAM_TOKEN" not in texto
    assert "VENICE_API_KEY=vieja-clave-venice" in texto  # el resto sigue igual


def test_guardar_deja_bak_con_el_contenido_anterior(tmp_path, monkeypatch):
    ruta = _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    conexiones.guardar("TELEGRAM_TOKEN", "999:nuevotoken")
    bak = tmp_path / ".env.bak"
    assert bak.exists()
    assert "TELEGRAM_TOKEN=1234567890:abcdefghijklmnop" in bak.read_text()


def test_guardar_deja_permisos_600(tmp_path, monkeypatch):
    import stat

    ruta = _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    conexiones.guardar("GROQ_API_KEY", "gsk-nueva")
    modo = stat.S_IMODE(ruta.stat().st_mode)
    assert modo == 0o600


def test_nombre_fuera_de_la_lista_blanca_es_invalido(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    with pytest.raises(conexiones.NombreInvalido):
        conexiones.guardar("AWS_SECRET_ACCESS_KEY", "x")
    with pytest.raises(conexiones.NombreInvalido):
        conexiones.probar("AWS_SECRET_ACCESS_KEY")


def test_estado_nunca_trae_el_valor_completo(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    estado = conexiones.estado()

    assert estado["TELEGRAM_TOKEN"].puesta is True
    assert estado["TELEGRAM_TOKEN"].termina_en == "mnop"
    for conexion in estado.values():
        texto = conexion.model_dump_json()
        assert "1234567890:abcdefghijklmnop" not in texto
        assert "vieja-clave-venice" not in texto


def test_estado_no_secreto_no_trae_termina_en(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "TELEGRAM_CHAT_ID=55555\n")
    estado = conexiones.estado()
    assert estado["TELEGRAM_CHAT_ID"].puesta is True
    assert estado["TELEGRAM_CHAT_ID"].termina_en is None


def test_estado_sin_env_dice_todo_sin_poner(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "")
    estado = conexiones.estado()
    assert all(c.puesta is False for c in estado.values())


def test_log_no_imprime_valores(tmp_path, monkeypatch, capsys):
    _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    conexiones.guardar("GROQ_API_KEY", "gsk-secreta-de-prueba")
    conexiones.estado()
    salida = capsys.readouterr()
    assert "gsk-secreta-de-prueba" not in salida.out
    assert "gsk-secreta-de-prueba" not in salida.err
    assert "1234567890:abcdefghijklmnop" not in salida.out
    assert "1234567890:abcdefghijklmnop" not in salida.err


def test_probar_sin_red_da_ok_false_sin_lanzar(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "GROQ_API_KEY=gsk-algo\n")

    def _sin_red(*_args, **_kwargs):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr(httpx, "get", _sin_red)
    resultado = conexiones.probar("GROQ_API_KEY")
    assert resultado.ok is False
    assert resultado.mensaje_humano  # algo humano, no una traza


def test_probar_timeout_da_ok_false_sin_lanzar(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "VENICE_API_KEY=algo\n")

    def _lento(*_args, **_kwargs):
        raise httpx.TimeoutException("se colgó")

    monkeypatch.setattr(httpx, "get", _lento)
    resultado = conexiones.probar("VENICE_API_KEY")
    assert resultado.ok is False


def test_probar_telegram_409_lo_dice_con_esas_palabras(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "TELEGRAM_TOKEN=123:abc\n")

    class _Respuesta409:
        status_code = 409
        headers: dict[str, str] = {}

        def json(self):
            return {}

    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _Respuesta409())
    resultado = conexiones.probar("TELEGRAM_TOKEN")
    assert resultado.ok is False
    assert "409" in resultado.mensaje_humano


def test_probar_llave_mala_devuelve_ok_false(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "GROQ_API_KEY=gsk-mala\n")

    class _Respuesta401:
        status_code = 401

    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _Respuesta401())
    resultado = conexiones.probar("GROQ_API_KEY")
    assert resultado.ok is False
    assert "Groq" in resultado.mensaje_humano


def test_probar_llave_buena_devuelve_ok_true(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "GROQ_API_KEY=gsk-buena\n")

    class _Respuesta200:
        status_code = 200

    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _Respuesta200())
    resultado = conexiones.probar("GROQ_API_KEY")
    assert resultado.ok is True


def test_probar_sin_nada_guardado_no_llama_a_la_red(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, "")

    def _no_deberia_llamarse(*_a, **_k):
        raise AssertionError("no debía llamar a la red sin llave guardada")

    monkeypatch.setattr(httpx, "get", _no_deberia_llamarse)
    resultado = conexiones.probar("GROQ_API_KEY")
    assert resultado.ok is False


def test_guardar_telegram_reinicia_el_hilo(tmp_path, monkeypatch):
    import telegram

    _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    llamado = []
    monkeypatch.setattr(telegram, "reiniciar_hilo", lambda: llamado.append(True))
    conexiones.guardar("TELEGRAM_CHAT_ID", "999")
    assert llamado == [True]


def test_guardar_otra_cosa_no_reinicia_el_hilo(tmp_path, monkeypatch):
    import telegram

    _env(tmp_path, monkeypatch, ENV_ORIGINAL)
    llamado = []
    monkeypatch.setattr(telegram, "reiniciar_hilo", lambda: llamado.append(True))
    conexiones.guardar("GROQ_API_KEY", "gsk-x")
    assert llamado == []


# — meta mensual: la edita el mismo Ajustes → Conexiones —


def _plata(tmp_path, monkeypatch, contenido: dict):
    import json

    ruta = tmp_path / "plata.json"
    ruta.write_text(json.dumps(contenido))
    monkeypatch.setattr(conexiones, "RUTA_PLATA", ruta)
    return ruta


def test_escribir_meta_mensual_conserva_moneda_y_comentario(tmp_path, monkeypatch):
    ruta = _plata(tmp_path, monkeypatch, {"$comment": "ojo", "meta_mensual": 2400, "moneda": "USD"})
    conexiones.escribir_meta_mensual(3000)

    import json

    guardado = json.loads(ruta.read_text())
    assert guardado["meta_mensual"] == 3000
    assert guardado["moneda"] == "USD"
    assert guardado["$comment"] == "ojo"


def test_escribir_meta_mensual_cero_o_negativa_es_invalida(tmp_path, monkeypatch):
    _plata(tmp_path, monkeypatch, {"meta_mensual": 2400, "moneda": "USD"})
    with pytest.raises(ValueError):
        conexiones.escribir_meta_mensual(0)
    with pytest.raises(ValueError):
        conexiones.escribir_meta_mensual(-100)

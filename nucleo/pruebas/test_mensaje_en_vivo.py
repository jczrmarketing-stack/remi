"""V3 (2/10/2026): la respuesta sale en frases, a medida que el motor la
escribe. Acá se prueba el corte en frases, la lectura del stream de la CLI
y del cliente OpenAI-compatible, la regla de no caer a otro modo después
de haber hablado, y el endpoint /mensaje/stream."""
import importlib
import io
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _pensar():
    sys.modules.pop("pensar", None)
    import pensar

    return pensar


def _servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _deltas(trozos, resultado="fin"):
    def gen():
        for t in trozos:
            yield t
        return resultado

    return gen()


def _recoger(frases):
    salida = []
    try:
        while True:
            salida.append(next(frases))
    except StopIteration as fin:
        return salida, fin.value


# — El corte en frases —


def test_en_frases_corta_en_puntuacion_y_devuelve_el_resultado():
    pensar = _pensar()
    frases, resultado = _recoger(
        pensar._en_frases(_deltas(["Parás ahora mismo,", " ya. Tomá agua y", " dormí temprano. Mañana", " seguimos con eso."]))
    )
    assert frases == ["Paras ahora mismo, ya.", "Tomá agua y dormí temprano.", "Mañana seguimos con eso."]
    assert resultado == "fin"


def test_en_frases_pega_las_cortas_y_no_corta_decimales_ni_sin_espacio():
    pensar = _pensar()
    frases, _ = _recoger(pensar._en_frases(_deltas(["Ajá. Son 3.5 horas de trabajo, más o menos.Y nada más"])))
    # «Ajá.» es corta: se pega a la siguiente. «3.5» no corta. «más.Y» no corta (sin espacio).
    assert frases == ["Ajá. Son 3.5 horas de trabajo, más o menos.Y nada más"]


def test_en_frases_los_renglones_de_una_lista_son_frases():
    pensar = _pensar()
    frases, _ = _recoger(pensar._en_frases(_deltas(["Hoy quedan dos cosas:\n- la tarjeta del banco\n- llamar a Alfonso por la fase"])))
    assert frases == ["Hoy quedan dos cosas:", "- la tarjeta del banco", "- llamar a Alfonso por la fase"]


def test_en_frases_sin_texto_no_rinde_nada():
    pensar = _pensar()
    assert _recoger(pensar._en_frases(_deltas([], None))) == ([], None)


# — La CLI en stream-json —


class _EntradaFalsa(io.StringIO):
    escrito = ""

    def close(self):
        self.escrito = self.getvalue()
        super().close()


class _ProcesoFalso:
    instancias: list = []

    def __init__(self, lineas, returncode=0):
        self.stdin = _EntradaFalsa()
        self.stdout = iter(lineas)
        self.returncode = returncode
        self.muerto = False
        _ProcesoFalso.instancias.append(self)

    def wait(self):
        return self.returncode

    def kill(self):
        self.muerto = True


def _evento(texto=None, tipo="content_block_delta"):
    if tipo == "message_stop":
        return json.dumps({"type": "stream_event", "event": {"type": "message_stop"}}) + "\n"
    return json.dumps({"type": "stream_event", "event": {"type": tipo, "delta": {"type": "text_delta", "text": texto}}}) + "\n"


def _resultado(texto, **usage):
    datos = {
        "type": "result",
        "subtype": "success",
        "result": texto,
        "usage": {"input_tokens": 3, "output_tokens": 40, "cache_read_input_tokens": 9000, "cache_creation_input_tokens": 500, **usage},
        "duration_api_ms": 1200,
        "modelUsage": {"claude-haiku-4-5-20251001": {"canonicalModel": "claude-haiku-4-5"}},
        "is_error": False,
    }
    return json.dumps(datos) + "\n"


def test_deltas_claude_rinde_el_texto_y_lee_el_resultado(monkeypatch, capsys):
    pensar = _pensar()
    lineas = [
        json.dumps({"type": "system", "subtype": "init"}) + "\n",
        _evento("Parás ahora"),
        _evento(" mismo. Tomá agua."),
        _evento(tipo="message_stop"),
        _resultado("Parás ahora mismo. Tomá agua."),
    ]
    vistos = {}

    def popen_falso(comando, **kwargs):
        vistos["comando"] = comando
        vistos["kwargs"] = kwargs
        return _ProcesoFalso(lineas)

    monkeypatch.setattr(pensar.subprocess, "Popen", popen_falso)
    m = pensar.MODOS["rapido"]
    deltas, pensado = _recoger(pensar._deltas_claude(m, "¿paro?", "sos Remi", []))

    assert deltas == ["Parás ahora", " mismo. Tomá agua.", "\n"]
    assert pensado is not None and pensado.paso_minimo == "Parás ahora mismo. Tomá agua."
    assert pensado.modelo == "claude-haiku-4-5" and pensado.motor_usado == "claude"
    comando = vistos["comando"]
    assert comando[comando.index("--output-format") + 1] == "stream-json"
    assert "--include-partial-messages" in comando and "--verbose" in comando
    # Lo demás es el encierro de siempre.
    assert comando[comando.index("--tools") + 1] == "Read,Grep,Glob" and "--strict-mcp-config" in comando
    assert vistos["kwargs"]["cwd"] == pensar.CARPETA_CWD
    assert _ProcesoFalso.instancias[-1].stdin.escrito == "¿paro?"
    linea = [l for l in capsys.readouterr().err.splitlines() if l.startswith("[claude] modo=")][0]
    assert "cache_leida=9000" in linea and "api=1200" in linea


def test_deltas_claude_sin_resultado_o_con_error_sigue_sin_ia(monkeypatch):
    pensar = _pensar()
    m = pensar.MODOS["rapido"]

    monkeypatch.setattr(pensar.subprocess, "Popen", lambda *a, **k: _ProcesoFalso([_evento("Hola.")], returncode=1))
    assert _recoger(pensar._deltas_claude(m, "x", "y", [])) == (["Hola."], None)

    monkeypatch.setattr(pensar.subprocess, "Popen", lambda *a, **k: _ProcesoFalso([_evento("Hola.")]))
    assert _recoger(pensar._deltas_claude(m, "x", "y", [])) == (["Hola."], None)

    error = json.dumps({"type": "result", "subtype": "error", "result": "API Error: boom", "is_error": True, "usage": {}}) + "\n"
    monkeypatch.setattr(pensar.subprocess, "Popen", lambda *a, **k: _ProcesoFalso([error]))
    assert _recoger(pensar._deltas_claude(m, "x", "y", [])) == ([], None)


def test_deltas_claude_el_limite_de_uso_levanta_limite_de_claude(monkeypatch):
    import pytest

    pensar = _pensar()
    limite = json.dumps({"type": "result", "subtype": "error", "result": "You've hit your usage limit", "is_error": True, "usage": {}}) + "\n"
    monkeypatch.setattr(pensar.subprocess, "Popen", lambda *a, **k: _ProcesoFalso([limite]))
    with pytest.raises(pensar.LimiteDeClaude):
        _recoger(pensar._deltas_claude(pensar.MODOS["rapido"], "x", "y", []))


# — En vivo no se cae a otro modo después de hablar —


def test_en_vivo_si_el_modo_fallo_sin_decir_nada_cae_al_anterior(monkeypatch):
    pensar = _pensar()
    llamados = []

    def deltas_falsos(m, *a, **k):
        llamados.append(m.nombre)
        if m.nombre == "equilibrio":
            return _deltas([], None)
        return _deltas(["Hoy solo esto: la tarjeta."], pensar.Pensado("Hoy solo esto: la tarjeta.", 1, 1, "haiku"))

    monkeypatch.setattr(pensar, "_deltas_claude", deltas_falsos)
    frases, pensado = _recoger(pensar._charla_claude("x", "y", [], pensar.MODOS["equilibrio"], en_vivo=True))
    assert llamados == ["equilibrio", "rapido"]
    assert frases == ["Hoy solo esto: la tarjeta."] and pensado is not None


def test_en_vivo_si_el_modo_fallo_despues_de_una_frase_no_cae_a_nada(monkeypatch, capsys):
    pensar = _pensar()
    llamados = []

    def deltas_falsos(m, *a, **k):
        llamados.append(m.nombre)
        return _deltas(["Parás ahora mismo, ya. Y después de eso"], None)

    monkeypatch.setattr(pensar, "_deltas_claude", deltas_falsos)
    frases, pensado = _recoger(pensar._charla_claude("x", "y", [], pensar.MODOS["equilibrio"], en_vivo=True))
    assert llamados == ["equilibrio"]
    assert frases == ["Paras ahora mismo, ya.", "Y después de eso"] and pensado is None
    assert "falló después de 2 frase(s)" in capsys.readouterr().err


def test_pensar_en_frases_guarda_los_turnos_igual_que_pensar(monkeypatch):
    pensar = _pensar()
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    monkeypatch.setattr(
        pensar,
        "_deltas_claude",
        lambda m, *a, **k: _deltas(["Tenés pendiente la Fase 1. Arrancá", " por ahí."], pensar.Pensado("Tenés pendiente la Fase 1. Arrancá por ahí.", 1, 1, "haiku")),
    )
    frases, pensado = _recoger(pensar.pensar_en_frases("¿qué tengo pendiente?", "claude", "rapido"))
    assert frases == ["Tienes pendiente la Fase 1.", "Arrancá por ahí."]
    assert pensado is not None
    assert pensado.paso_minimo == "Tienes pendiente la Fase 1. Arrancá por ahí."
    turnos = pensar._turnos()
    assert [t.texto for t in turnos][-2:] == ["¿qué tengo pendiente?", "Tienes pendiente la Fase 1. Arrancá por ahí."]


# — El cliente OpenAI-compatible en stream —


class _RespuestaFalsa:
    def __init__(self, lineas):
        self._lineas = lineas

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(self._lineas)


def test_deltas_openai_compatible_lee_sse_y_arma_el_json_de_siempre(monkeypatch):
    pensar = _pensar()
    vistos = {}

    def stream_falso(metodo, url, **kwargs):
        vistos.update(metodo=metodo, url=url, json=kwargs["json"])
        return _RespuestaFalsa(
            [
                'data: {"model":"openai/gpt-oss-120b","choices":[{"delta":{"content":"Parás"}}]}',
                "",
                'data: {"choices":[{"delta":{"content":" ahora."}}]}',
                'data: {"choices":[],"usage":{"prompt_tokens":50,"completion_tokens":4}}',
                "data: [DONE]",
            ]
        )

    monkeypatch.setattr(pensar.httpx, "stream", stream_falso)
    deltas, datos = _recoger(pensar._deltas_openai_compatible("http://x", "clave", "m", "sos Remi", "¿paro?", 5.0))
    assert deltas == ["Parás", " ahora."]
    assert vistos["json"]["stream"] is True and vistos["json"]["stream_options"] == {"include_usage": True}
    pensado = pensar._leer_respuesta_venice(datos, "m", 0, proveedor="groq")
    assert pensado is not None and pensado.paso_minimo == "Parás ahora."
    assert (pensado.tokens_entrada, pensado.tokens_salida, pensado.modelo) == (50, 4, "groq/openai/gpt-oss-120b")


# — POST /mensaje/stream —


def _leer_ndjson(cliente, cuerpo):
    with cliente.stream("POST", "/mensaje/stream", json=cuerpo) as respuesta:
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("application/x-ndjson")
        return [json.loads(l) for l in respuesta.iter_lines() if l.strip()]


def test_mensaje_stream_una_linea_por_frase_y_al_final_la_respuesta_entera(tmp_path, monkeypatch):
    servidor = _servidor(tmp_path, monkeypatch)
    texto = "**Parás** ahora mismo. Tomá agua. Dormí temprano. Mañana seguimos con la tarjeta. Nada más por hoy."

    def frases_falsas(frase, motor=None, modo=None, **kwargs):
        assert kwargs.get("en_vivo") is True
        for f in texto.split(". "):
            yield f if f.endswith(".") else f + "."
        return servidor.pensar.Pensado(paso_minimo=texto, tokens_entrada=10, tokens_salida=20, modelo="haiku")

    monkeypatch.setattr(servidor.pensar, "pensar_en_frases", frases_falsas)
    lineas = _leer_ndjson(TestClient(servidor.app), {"texto": "tengo sueño, ¿paro?", "think": True, "origen": "voz"})

    assert [l["frase"] for l in lineas[:-1]] == [
        "**Parás** ahora mismo.", "Tomá agua.", "Dormí temprano.", "Mañana seguimos con la tarjeta.", "Nada más por hoy.",
    ]
    # La voz: sin markdown y solo las primeras 3 (como para_hablar).
    assert [l["voz"] for l in lineas[:-1]] == ["Parás ahora mismo.", "Tomá agua.", "Dormí temprano.", None, None]
    fin = lineas[-1]["fin"]
    assert fin["tipo"] == "pregunta" and fin["texto"] == texto
    assert fin["voz"] == "Parás ahora mismo. Tomá agua. Dormí temprano."
    assert fin["tokens"] == {"entrada": 10, "salida": 20, "modelo": "haiku"}


def test_mensaje_stream_sin_think_solo_manda_fin(tmp_path, monkeypatch):
    servidor = _servidor(tmp_path, monkeypatch)
    monkeypatch.setattr(servidor.pensar, "pensar_en_frases", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía pensar")))
    lineas = _leer_ndjson(TestClient(servidor.app), {"texto": "voy a llamar al banco"})
    assert len(lineas) == 1 and lineas[0]["fin"]["voz"] == "Hoy solo esto: voy a llamar al banco."


def test_mensaje_stream_si_el_motor_falla_a_mitad_fin_trae_la_respuesta_sin_ia(tmp_path, monkeypatch):
    servidor = _servidor(tmp_path, monkeypatch)

    def frases_rotas(frase, motor=None, modo=None, **kwargs):
        yield "Parás ahora mismo."
        return None

    monkeypatch.setattr(servidor.pensar, "pensar_en_frases", frases_rotas)
    lineas = _leer_ndjson(TestClient(servidor.app), {"texto": "tengo sueño, ¿paro?", "think": True, "origen": "voz"})
    assert lineas[0]["frase"] == "Parás ahora mismo."
    assert lineas[-1]["fin"]["texto"] == "Sin pensar no puedo contestarte eso. No guardé nada."


def test_mensaje_stream_si_revienta_se_cierra_sin_fin(tmp_path, monkeypatch, capsys):
    servidor = _servidor(tmp_path, monkeypatch)

    def frases_que_revientan(frase, motor=None, modo=None, **kwargs):
        yield "Parás ahora mismo."
        raise RuntimeError("se cayó la CLI")

    monkeypatch.setattr(servidor.pensar, "pensar_en_frases", frases_que_revientan)
    lineas = _leer_ndjson(TestClient(servidor.app), {"texto": "tengo sueño, ¿paro?", "think": True, "origen": "voz"})
    assert [list(l) for l in lineas] == [["frase", "voz"]]
    assert "[mensaje/stream] falló a mitad (RuntimeError: se cayó la CLI)" in capsys.readouterr().err

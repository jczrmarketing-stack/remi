"""Los agentes de la línea: una llamada a `claude -p` con salida fija, Portero y eventos."""

import json

import pytest

import coding
import consumo
from fabrica import agentes, expediente


def _linea(evento):
    return json.dumps(evento)


def _resultado(estructura, entrada=100, salida=20, **extra):
    return _linea({"type": "result", "subtype": "success", "is_error": False, "result": json.dumps(estructura),
                   "structured_output": estructura,
                   "usage": {"input_tokens": entrada, "output_tokens": salida}, **extra})


def _falso(lineas, grabado=None):
    def ejecutar(comando, stdin, cwd, env):
        if grabado is not None:
            grabado.update(comando=comando, stdin=stdin, cwd=cwd, env=env)
        yield from lineas
    return ejecutar


@pytest.fixture
def pedido(tmp_path, monkeypatch):
    monkeypatch.setattr(expediente, "RAIZ", tmp_path / "pedidos")
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setattr(agentes.agentes_estado, "avisar", lambda *a, **k: None)
    return expediente.crear("Una idea", "remi", "main")


def test_llamar_devuelve_la_salida_estructurada_y_cuenta_tokens(tmp_path, pedido):
    estructura = {"estado": "hecho", "motivo": "m", "spec": "s", "escenarios": [], "preguntas": [], "toca": [], "riesgo": "bajo"}
    salida = agentes.llamar("planificador", "haz", tmp_path, pedido, ejecutar=_falso([_resultado(estructura)]))
    assert salida.estado == "hecho"
    assert salida.motivo == "m"
    assert salida.datos["spec"] == "s"
    assert salida.tokens == 120
    assert consumo.tokens_del_pedido(pedido) == 120


def test_llamar_guarda_eventos_de_texto_herramienta_y_resultado(tmp_path, pedido):
    lineas = [
        _linea({"type": "system", "subtype": "init"}),
        _linea({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Leo el archivo"},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/x/consumo.py"}},
        ]}}),
        _linea({"type": "user", "message": {"content": [{"type": "tool_result", "content": "a" * 2000}]}}),
        _resultado({"estado": "hecho", "motivo": "listo", "resumen": "r", "archivos": []}),
    ]
    agentes.llamar("constructor", "haz", tmp_path, pedido, ejecutar=_falso(lineas))
    eventos = [json.loads(l) for l in (expediente.carpeta(pedido) / "eventos.jsonl").read_text().splitlines()]
    assert [e["tipo"] for e in eventos] == ["texto", "herramienta", "resultado", "fin"]
    assert [e["n"] for e in eventos] == [0, 1, 2, 3]
    assert eventos[1]["herramienta"] == "Read"
    assert "/x/consumo.py" in eventos[1]["texto"]
    assert len(eventos[2]["texto"]) <= 600
    assert all(e["rol"] == "constructor" for e in eventos)


def test_eventos_siguen_la_cuenta_entre_agentes(tmp_path, pedido):
    fin = _resultado({"estado": "hecho", "motivo": "m", "hallazgos": []})
    agentes.llamar("revisor", "a", tmp_path, pedido, ejecutar=_falso([fin]))
    agentes.llamar("revisor", "b", tmp_path, pedido, ejecutar=_falso([fin]))
    eventos = [json.loads(l) for l in (expediente.carpeta(pedido) / "eventos.jsonl").read_text().splitlines()]
    assert [e["n"] for e in eventos] == [0, 1]


def test_salida_rota_es_no_puedo(tmp_path, pedido):
    salida = agentes.llamar("tester", "haz", tmp_path, pedido, ejecutar=_falso(["no es json", _linea({"type": "system"})]))
    assert salida.estado == "no_puedo"
    assert "CLI" in salida.motivo


def test_estado_fuera_del_esquema_es_no_puedo(tmp_path, pedido):
    salida = agentes.llamar("tester", "haz", tmp_path, pedido,
                            ejecutar=_falso([_resultado({"estado": "quizas", "motivo": "m"})]))
    assert salida.estado == "no_puedo"


def test_sin_structured_output_lee_el_result_como_json(tmp_path, pedido):
    linea = _linea({"type": "result", "is_error": False, "result": json.dumps({"estado": "necesito_dato", "motivo": "¿cuál?"}),
                    "usage": {"input_tokens": 1, "output_tokens": 1}})
    salida = agentes.llamar("tester", "haz", tmp_path, pedido, ejecutar=_falso([linea]))
    assert salida.estado == "necesito_dato"


def test_limite_de_max_levanta(tmp_path, pedido):
    with pytest.raises(coding.LimiteDeMax):
        agentes.llamar("tester", "haz", tmp_path, pedido, ejecutar=_falso(["Claude AI usage limit reached|1730000000"]))


def test_comando_trae_json_schema_settings_y_stream_json(tmp_path):
    tester = agentes.comando("tester", "sonnet", tmp_path)
    assert tester[tester.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in tester
    esquema = json.loads(tester[tester.index("--json-schema") + 1])
    assert esquema["required"][:2] == ["estado", "motivo"]
    assert tester[tester.index("--settings") + 1].endswith("fabrica/portero/settings.json")
    assert tester[tester.index("--max-turns") + 1] == "30"
    permitidas = tester[tester.index("--allowedTools") + 1]
    assert "Edit" in permitidas and "Bash(" in permitidas and "pytest" in permitidas
    planificador = agentes.comando("planificador", "opus", tmp_path)
    assert "Edit" not in planificador[planificador.index("--allowedTools") + 1]


def test_llamar_pasa_worktree_y_portero_en_el_entorno(tmp_path, pedido):
    grabado: dict = {}
    agentes.llamar("revisor", "mira", tmp_path, pedido,
                   ejecutar=_falso([_resultado({"estado": "hecho", "motivo": "m", "hallazgos": []})], grabado))
    assert grabado["env"]["FABRICA_WORKTREE"] == str(tmp_path)
    assert grabado["env"]["FABRICA_PORTERO"].endswith("fabrica/portero/portero.py")
    assert grabado["stdin"].endswith("mira")
    assert grabado["comando"][grabado["comando"].index("--model") + 1] == "sonnet"


def test_entorno_de_los_agentes_no_puede_empujar(monkeypatch):
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agente.sock")
    monkeypatch.setenv("GH_TOKEN", "x")
    entorno = agentes.entorno_encerrado({"SSH_AUTH_SOCK": "/tmp/agente.sock", "GH_TOKEN": "x", "HOME": "/Users/x"})
    assert "SSH_AUTH_SOCK" not in entorno and "GH_TOKEN" not in entorno
    assert entorno["GIT_SSH_COMMAND"] == "false"
    claves = {entorno[f"GIT_CONFIG_KEY_{i}"]: entorno[f"GIT_CONFIG_VALUE_{i}"] for i in range(int(entorno["GIT_CONFIG_COUNT"]))}
    assert claves["credential.helper"] == ""
    assert claves["remote.origin.pushurl"].startswith("fabrica-sin-push")
    assert entorno["HOME"] == "/Users/x"


def test_llamar_usa_el_entorno_encerrado(tmp_path, pedido, monkeypatch):
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agente.sock")
    grabado: dict = {}
    agentes.llamar("tester", "haz", tmp_path, pedido,
                   ejecutar=_falso([_resultado({"estado": "hecho", "motivo": "m", "tests": [], "resumen": ""})], grabado))
    assert "SSH_AUTH_SOCK" not in grabado["env"]


def test_settings_del_portero_prende_el_sandbox():
    settings = json.loads(agentes.SETTINGS.read_text())
    assert settings["sandbox"]["enabled"] is True
    assert settings["hooks"]["PreToolUse"]


def test_el_planificador_puede_partir_o_decir_fuera_de_alcance():
    esquema = agentes.ESQUEMAS["planificador"]
    assert {"partir", "fuera_de_alcance"} <= set(esquema["properties"]["estado"]["enum"])
    assert {"partes", "como_se_demuestra"} <= set(esquema["required"])
    assert "partir" not in agentes.ESQUEMAS["constructor"]["properties"]["estado"]["enum"]


def test_reglas_para_todos_y_mision_para_planificador_y_revisor(tmp_path):
    for rol in agentes.ROLES:
        sistema = agentes._sistema(rol, tmp_path)
        assert "Reglas de la fábrica (más estrictas que el CLAUDE.md)" in sistema
        assert ("Misión de la fábrica" in sistema) == (rol in ("planificador", "revisor"))


def test_salida_partir_del_planificador_es_valida():
    final = {"type": "result", "structured_output": {"estado": "partir", "motivo": "dos cosas", "partes": ["a", "b"]}}
    assert agentes._salida_de(final).estado == "partir"

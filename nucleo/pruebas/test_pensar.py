import importlib
import json
import subprocess
import sys

from fastapi.testclient import TestClient


def _arrancar_servidor():
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_sin_think_no_toca_a_claude(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()

    def explota(_frase, _motor=None):
        raise AssertionError("no debía pensar con Claude")

    monkeypatch.setattr(servidor.pensar, "pensar", explota)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "voy a llamar al banco"}).json()
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["voz"] == "Hoy solo esto: voy a llamar al banco."
    assert creada["tokens"] is None


def test_con_think_el_paso_minimo_lo_ordena_claude(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    llamadas = []

    def falso_pensar(frase, motor=None):
        llamadas.append(frase)
        return servidor.pensar.Pensado(
            paso_minimo="Abre la app del banco y busca el teléfono.",
            tokens_entrada=120,
            tokens_salida=14,
            modelo="modelo-de-prueba",
        )

    monkeypatch.setattr(servidor.pensar, "pensar", falso_pensar)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "voy a llamar al banco", "think": True}).json()
    assert llamadas == ["voy a llamar al banco"]
    assert creada["tarea"]["paso_minimo"] == "Abre la app del banco y busca el teléfono."
    assert creada["voz"] == "Abre la app del banco y busca el teléfono."
    assert creada["tokens"] == {"entrada": 120, "salida": 14, "modelo": "modelo-de-prueba"}
    # Se guarda con el paso de Claude, no con el universal.
    hoy = cliente.get("/hoy").json()
    assert hoy[0]["tarea"]["paso_minimo"] == "Abre la app del banco y busca el teléfono."


def test_con_think_pero_claude_no_puede_sigue_sin_ia(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    monkeypatch.setattr(servidor.pensar, "pensar", lambda _frase, _motor=None: None)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "voy a llamar al banco", "think": True}).json()
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["voz"] == "Hoy solo esto: voy a llamar al banco."
    assert creada["tokens"] is None


def test_la_voz_de_claude_tambien_se_recorta_a_20_palabras(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    largo = " ".join(f"p{i}" for i in range(30))
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda _frase, _motor=None: servidor.pensar.Pensado(largo, 1, 1, "m"),
    )
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "arranco con x", "think": True}).json()
    assert len(creada["voz"].split()) <= servidor.MAX_PALABRAS_VOZ


# — El módulo pensar.py: va por la CLI de Claude Code, nunca por la API —


def _importar_pensar():
    sys.modules.pop("pensar", None)
    import pensar

    return pensar


def _salida_cli(**cambios):
    datos = {
        "result": "Busca el número del banco en tu tarjeta.",
        "usage": {"input_tokens": 544, "output_tokens": 29},
        "modelUsage": {"claude-haiku-4-5-20251001": {"canonicalModel": "claude-haiku-4-5"}},
        "is_error": False,
    }
    datos.update(cambios)
    return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout=json.dumps(datos), stderr="")


def test_pensar_lee_el_paso_y_los_tokens_de_la_cli(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: _salida_cli())

    pensado = pensar.pensar("voy a llamar al banco")
    assert pensado is not None
    assert pensado.paso_minimo == "Busca el número del banco en tu tarjeta."
    assert (pensado.tokens_entrada, pensado.tokens_salida) == (544, 29)
    assert pensado.modelo == "claude-haiku-4-5"


def test_la_frase_va_por_stdin_con_haiku_y_sin_herramientas(monkeypatch):
    pensar = _importar_pensar()
    visto = {}

    def espiar(comando, **kwargs):
        visto["comando"] = comando
        visto["kwargs"] = kwargs
        return _salida_cli()

    monkeypatch.setattr(pensar.subprocess, "run", espiar)
    pensar.pensar("voy a llamar al banco")

    comando = visto["comando"]
    assert comando[0] == "claude" and "-p" in comando
    assert comando[comando.index("--model") + 1] == "haiku"
    assert comando[comando.index("--output-format") + 1] == "json"
    assert comando[comando.index("--tools") + 1] == ""
    assert comando[comando.index("--system-prompt") + 1] == pensar.INSTRUCCIONES
    # La frase entra por stdin, no por argumento (nunca en la lista de procesos).
    assert visto["kwargs"]["input"] == "voy a llamar al banco"


def test_nunca_hereda_la_clave_de_api(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-no-usar")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tampoco")
    visto = {}

    def espiar(_comando, **kwargs):
        visto.update(kwargs)
        return _salida_cli()

    monkeypatch.setattr(pensar.subprocess, "run", espiar)
    pensar.pensar("algo")

    entorno = visto["env"]
    assert "ANTHROPIC_API_KEY" not in entorno
    assert "ANTHROPIC_AUTH_TOKEN" not in entorno
    # El razonamiento cuenta contra el techo de salida, así que va apagado.
    assert entorno["MAX_THINKING_TOKENS"] == "0"
    # 1500, no 200: el JSON de una llamada a `guardar` cuenta como salida y
    # con 200 se corta a la mitad — la CLI devuelve "exceeded the 200 output
    # token maximum" y no guarda nada. La voz la recorta el servidor a 20
    # palabras, no este techo.
    assert entorno["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "1500"


def test_modelo_configurable(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_CLAUDE_MODELO", "sonnet")
    visto = {}
    monkeypatch.setattr(
        pensar.subprocess, "run", lambda comando, **k: (visto.update(c=comando), _salida_cli())[1]
    )
    pensar.pensar("algo")
    assert visto["c"][visto["c"].index("--model") + 1] == "sonnet"


def test_error_de_la_cli_no_se_convierte_en_la_voz_de_remi(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(
        pensar.subprocess,
        "run",
        lambda *a, **k: _salida_cli(is_error=True, result="API Error: 400 max_tokens…"),
    )
    assert pensar.pensar("algo") is None


def test_sin_cli_en_el_path_sigue_sin_ia(monkeypatch):
    pensar = _importar_pensar()

    def no_esta(*_a, **_k):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(pensar.subprocess, "run", no_esta)
    assert pensar.pensar("algo") is None


def test_si_tarda_demasiado_sigue_sin_ia(monkeypatch):
    pensar = _importar_pensar()

    def lenta(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=pensar.TIMEOUT_SEGUNDOS)

    monkeypatch.setattr(pensar.subprocess, "run", lenta)
    assert pensar.pensar("algo") is None


def test_respuesta_ilegible_o_vacia_sigue_sin_ia(monkeypatch):
    pensar = _importar_pensar()
    rota = subprocess.CompletedProcess(args=["claude"], returncode=0, stdout="no es json", stderr="")
    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: rota)
    assert pensar.pensar("algo") is None

    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: _salida_cli(result="   "))
    assert pensar.pensar("algo") is None


def test_codigo_de_salida_distinto_de_cero_sigue_sin_ia(monkeypatch):
    pensar = _importar_pensar()
    fallo = subprocess.CompletedProcess(args=["claude"], returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr(pensar.subprocess, "run", lambda *a, **k: fallo)
    assert pensar.pensar("algo") is None


# — El motor de Venice —


def test_el_motor_por_defecto_es_claude(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.delenv("REMI_PENSADOR", raising=False)
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    assert pensar.motor() == "claude"


def test_un_motor_desconocido_cae_a_claude(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "gpt-lo-que-sea")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    assert pensar.motor() == "claude"


def test_venice_sin_clave_sigue_sin_ia(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "venice")
    monkeypatch.delenv("VENICE_API_KEY", raising=False)
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    assert pensar.pensar("algo") is None


def test_venice_lee_el_texto_y_los_tokens(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "venice")
    monkeypatch.setenv("VENICE_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("REMI_VENICE_MODELO", "modelo-x")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    visto = {}

    def falsa_llamada(clave, nombre_modelo, instrucciones, frase):
        visto.update(clave=clave, modelo=nombre_modelo, instrucciones=instrucciones, frase=frase)
        return {
            "model": "modelo-x-1-2",
            "choices": [{"message": {"content": "  Abrí el correo y respondé el primero.  "}}],
            "usage": {"prompt_tokens": 1578, "completion_tokens": 9},
        }

    monkeypatch.setattr(pensar, "_llamar_venice", falsa_llamada)
    pensado = pensar.pensar("tengo el correo lleno")
    assert pensado is not None
    assert pensado.paso_minimo == "Abrí el correo y respondé el primero."
    assert (pensado.tokens_entrada, pensado.tokens_salida) == (1578, 9)
    assert pensado.modelo == "venice/modelo-x-1-2"
    assert pensado.leyo_memoria is False
    assert visto["clave"] == "clave-de-prueba" and visto["modelo"] == "modelo-x"
    assert visto["frase"] == "tengo el correo lleno"
    assert visto["instrucciones"].startswith(pensar.INSTRUCCIONES[:40])


def test_venice_con_respuesta_vacia_sigue_sin_ia(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "venice")
    monkeypatch.setenv("VENICE_API_KEY", "clave")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    monkeypatch.setattr(pensar, "_llamar_venice", lambda *a: {"choices": []})
    assert pensar.pensar("algo") is None


def test_la_clave_de_venice_no_se_exporta_a_la_cli_de_claude(monkeypatch, tmp_path):
    """La clave se lee del .env a un dict; el subproceso de Claude no la ve."""
    pensar = _importar_pensar()
    ruta = tmp_path / ".env"
    ruta.write_text("VENICE_API_KEY=secreta\nREMI_PENSADOR=claude\n")
    monkeypatch.setattr(pensar, "RUTA_ENV", ruta)
    monkeypatch.delenv("VENICE_API_KEY", raising=False)
    assert pensar._ajuste("VENICE_API_KEY", "") == "secreta"
    assert "VENICE_API_KEY" not in pensar._entorno()


# — El motor elegido desde la ventanita —


def test_el_motor_pedido_gana_sobre_el_env(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "claude")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    assert pensar.motor("venice") == "venice"
    assert pensar.motor(None) == "claude"
    assert pensar.motor("otro") == "claude"


def test_los_motores_disponibles_dicen_que_les_falta(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.delenv("VENICE_API_KEY", raising=False)
    monkeypatch.setattr(pensar.shutil if hasattr(pensar, "shutil") else __import__("shutil"), "which", lambda _b: None)
    motores = {m.id: m for m in pensar.motores_disponibles()}
    assert set(motores) == {"claude", "venice"}
    assert motores["claude"].disponible is False and "claude" in motores["claude"].detalle
    assert motores["venice"].disponible is False and "VENICE_API_KEY" in motores["venice"].detalle

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

    def explota(_frase, _motor=None, _modo=None):
        raise AssertionError("no debía pensar con Claude")

    monkeypatch.setattr(servidor.pensar, "pensar", explota)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "voy a llamar al banco"}).json()
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["voz"] == "Hoy solo esto: voy a llamar al banco."
    assert creada["tokens"] is None


def test_con_think_contesta_el_modelo_y_el_paso_minimo_nace_universal(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    llamadas = []

    def falso_pensar(frase, motor=None, modo=None, nivel=None, **_k):
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
    # Desde la Fase 3a el modelo contesta; el paso_minimo sigue universal.
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["texto"] == "Abre la app del banco y busca el teléfono."
    assert creada["voz"] == "Abre la app del banco y busca el teléfono."
    assert creada["tokens"] == {"entrada": 120, "salida": 14, "modelo": "modelo-de-prueba"}


def test_con_think_pero_claude_no_puede_sigue_sin_ia(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    monkeypatch.setattr(servidor.pensar, "pensar", lambda _frase, _motor=None, _modo=None, nivel=None, **_k: None)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "voy a llamar al banco", "think": True}).json()
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["voz"] == "Hoy solo esto: voy a llamar al banco."
    assert creada["tokens"] is None


def test_sin_techo_de_palabras_y_hablado_hasta_tres_frases(tmp_path, monkeypatch):
    """Fase 3a: el carácter define el largo. En pantalla va entero; en voz
    alta, solo si entró por voz, hasta 3 frases."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    largo = (
        "Uno dos tres cuatro cinco seis siete ocho nueve diez once doce. "
        "Trece catorce quince dieciséis diecisiete. Tercera frase. Cuarta frase. Quinta."
    )
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda _frase, _motor=None, _modo=None, nivel=None, **_k: servidor.pensar.Pensado(largo.strip(), 1, 1, "m"),
    )
    cliente = TestClient(servidor.app)

    escrita = cliente.post("/mensaje", json={"texto": "arranco con x", "think": True}).json()
    assert escrita["texto"] == largo.strip()
    assert escrita["voz"] == largo.strip()
    assert len(escrita["texto"].split()) > servidor.MAX_PALABRAS_VOZ

    hablada = cliente.post(
        "/mensaje", json={"texto": "arranco con y", "think": True, "origen": "voz"}
    ).json()
    assert hablada["texto"] == largo.strip()
    assert hablada["voz"].count(".") == 3
    assert hablada["voz"].endswith("Tercera frase.")


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


def test_la_frase_va_por_stdin_con_sonnet_y_sin_herramientas(monkeypatch):
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
    assert comando[comando.index("--model") + 1] == "sonnet"
    assert comando[comando.index("--output-format") + 1] == "json"
    assert comando[comando.index("--tools") + 1] == "Read,Grep,Glob"
    assert comando[comando.index("--system-prompt") + 1] == pensar.instrucciones_con_indice([])
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
    assert entorno["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "4000"


def test_el_modo_cambia_el_model(monkeypatch):
    pensar = _importar_pensar()
    vistos = []

    def espiar(comando, **kwargs):
        vistos.append((comando[comando.index("--model") + 1], kwargs["env"]))
        return _salida_cli()

    monkeypatch.setattr(pensar.subprocess, "run", espiar)
    casos = (("rapido", "haiku"), ("equilibrio", "sonnet"), ("inteligente", "opus"), (None, "sonnet"))
    for modo, esperado in casos:
        vistos.clear()
        pensar.pensar("algo", "claude", modo)
        modelo, entorno = vistos[0]
        assert modelo == esperado, modo
        # Solo inteligente razona.
        assert (entorno["MAX_THINKING_TOKENS"] != "0") == (modo == "inteligente"), modo


def test_inteligente_cae_a_equilibrio_y_despues_a_rapido(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    modelos = []

    def falso_run(comando, **kwargs):
        m = comando[comando.index("--model") + 1]
        modelos.append(m)
        if m != "haiku":
            raise subprocess.TimeoutExpired(cmd="claude", timeout=kwargs["timeout"])
        return _salida_cli(result="Rápido contestó.")

    monkeypatch.setattr(pensar.subprocess, "run", falso_run)
    pensado = pensar.pensar("algo", "claude", "inteligente")
    assert pensado is not None and pensado.paso_minimo == "Rápido contestó."
    assert modelos == ["opus", "sonnet", "haiku"]


def test_el_nivel_solo_cambia_al_elegido(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    llamadas = []

    def falso_run(comando, **kwargs):
        m = comando[comando.index("--model") + 1]
        llamadas.append((m, kwargs["env"]["MAX_THINKING_TOKENS"], kwargs["timeout"]))
        if m != "haiku":
            raise subprocess.TimeoutExpired(cmd="claude", timeout=kwargs["timeout"])
        return _salida_cli(result="ok")

    monkeypatch.setattr(pensar.subprocess, "run", falso_run)
    pensar.pensar("algo", "claude", "equilibrio", nivel="alto")
    # Sonnet con alto piensa 16000 y espera 60 s; Haiku, al caer, va con lo suyo.
    assert llamadas == [("sonnet", "16000", 60.0), ("haiku", "0", 20.0)]


def test_opus_en_bajo_no_razona_y_el_peor_caso_no_crece():
    pensar = _importar_pensar()
    bajo = pensar.con_nivel(pensar.MODOS["inteligente"], "bajo")
    assert bajo.razonamiento_tokens == 0 and bajo.techo_segundos == 60.0
    for n in pensar.NIVELES:
        for m in pensar.MODOS.values():
            assert pensar.con_nivel(m, n).techo_segundos <= pensar.TECHO_EXTRA
    assert pensar.con_nivel(pensar.MODOS["inteligente"], "extra").razonamiento_tokens == 32000
    assert pensar.con_nivel(pensar.MODOS["rapido"], None) == pensar.MODOS["rapido"]


def test_rapido_no_cae_a_nada(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    modelos = []

    def falla(comando, **kwargs):
        modelos.append(comando[comando.index("--model") + 1])
        raise subprocess.TimeoutExpired(cmd="claude", timeout=kwargs["timeout"])

    monkeypatch.setattr(pensar.subprocess, "run", falla)
    assert pensar.pensar("algo", "claude", "rapido") is None
    assert modelos == ["haiku"]


def test_error_de_la_cli_no_se_convierte_en_la_voz_de_remi(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(
        pensar.subprocess,
        "run",
        lambda *a, **k: _salida_cli(is_error=True, result="API Error: 400 max_tokens…"),
    )
    assert pensar.pensar("algo") is None


# — El respaldo de charla (límite de Claude alcanzado) —


def test_limite_alcanzado_reintenta_con_openrouter_y_lo_dice_en_motor_usado(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(
        pensar.subprocess,
        "run",
        lambda *a, **k: _salida_cli(is_error=True, result="Claude AI usage limit reached|1234567890"),
    )
    visto = {}

    def falsa_llamada(proveedor, modelo, instrucciones, frase):
        visto.update(proveedor=proveedor, modelo=modelo, frase=frase)
        return {
            "model": modelo,
            "choices": [{"message": {"content": "Seguí con lo de hoy."}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4},
        }

    monkeypatch.setattr(pensar, "_llamar_proveedor", falsa_llamada)
    pensado = pensar.pensar("¿cómo sigo?")

    assert pensado is not None
    assert pensado.paso_minimo == "Seguí con lo de hoy."
    assert pensado.motor_usado == "openrouter"
    assert pensado.modelo == "openrouter/deepseek-v4-pro"
    assert visto["proveedor"] == "openrouter" and visto["modelo"] == "deepseek-v4-pro"
    assert visto["frase"] == "¿cómo sigo?"


def test_limite_alcanzado_no_reintenta_con_otro_modo_de_claude(monkeypatch):
    """Los tres modos de Claude comparten el mismo límite de la membresía
    Max: no tiene sentido que `cadena_de_modos` los pruebe a todos."""
    pensar = _importar_pensar()
    llamadas_a_claude = []

    def falsa_cli(comando, **_k):
        llamadas_a_claude.append(comando[comando.index("--model") + 1])
        return _salida_cli(is_error=True, result="Claude AI usage limit reached|1234567890")

    monkeypatch.setattr(pensar.subprocess, "run", falsa_cli)
    monkeypatch.setattr(
        pensar,
        "_llamar_proveedor",
        lambda *a, **k: {"choices": [{"message": {"content": "Listo."}}], "usage": {}},
    )
    pensar.pensar("algo", modo_pedido="inteligente")
    assert llamadas_a_claude == ["opus"]


def test_si_el_respaldo_tampoco_contesta_sigue_sin_ia(monkeypatch):
    pensar = _importar_pensar()
    monkeypatch.setattr(
        pensar.subprocess,
        "run",
        lambda *a, **k: _salida_cli(is_error=True, result="límite alcanzado"),
    )
    monkeypatch.setattr(pensar, "_llamar_proveedor", lambda *a, **k: {"choices": []})
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
        raise subprocess.TimeoutExpired(cmd="claude", timeout=8)

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
    assert visto["instrucciones"].startswith(pensar.caracter()[:40])


def test_venice_el_chip_elige_entre_los_dos(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("VENICE_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("REMI_VENICE_MODELO", "modelo-x")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    visto = {}

    def falsa_llamada(clave, nombre_modelo, instrucciones, frase):
        visto["modelo"] = nombre_modelo
        return {"model": nombre_modelo, "choices": [{"message": {"content": "Listo."}}], "usage": {}}

    monkeypatch.setattr(pensar, "_llamar_venice", falsa_llamada)
    pensar.pensar("cómo funciona", "venice", modelo_venice="grok-4-7")
    assert visto["modelo"] == "grok-4-7"
    pensar.pensar("cómo funciona", "venice", modelo_venice="z-ai-glm-5-3-flash")
    assert visto["modelo"] == "z-ai-glm-5-3-flash"
    pensar.pensar("cómo funciona", "venice", modelo_venice="otro")
    assert visto["modelo"] == "modelo-x"


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


# — El motor de DeepSeek —


def test_deepseek_sin_clave_sigue_sin_ia(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    assert pensar.pensar("algo") is None


def test_deepseek_nunca_es_el_motor_por_defecto(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-de-prueba")
    monkeypatch.delenv("REMI_PENSADOR", raising=False)
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    assert pensar.motor() == "claude"


def test_deepseek_lee_el_texto_y_los_tokens(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("REMI_DEEPSEEK_MODELO", "modelo-x")
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

    monkeypatch.setattr(pensar, "_llamar_deepseek", falsa_llamada)
    pensado = pensar.pensar("tengo el correo lleno")
    assert pensado is not None
    assert pensado.paso_minimo == "Abrí el correo y respondé el primero."
    assert (pensado.tokens_entrada, pensado.tokens_salida) == (1578, 9)
    assert pensado.modelo == "deepseek/modelo-x-1-2"
    assert pensado.leyo_memoria is False
    assert visto["clave"] == "clave-de-prueba" and visto["modelo"] == "modelo-x"
    assert visto["frase"] == "tengo el correo lleno"
    assert visto["instrucciones"].startswith(pensar.caracter()[:40])


def test_deepseek_el_chip_elige_entre_flash_y_pro(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("REMI_DEEPSEEK_MODELO", "modelo-x")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    visto = {}

    def falsa_llamada(clave, nombre_modelo, instrucciones, frase):
        visto["modelo"] = nombre_modelo
        return {"model": nombre_modelo, "choices": [{"message": {"content": "Listo."}}], "usage": {}}

    monkeypatch.setattr(pensar, "_llamar_deepseek", falsa_llamada)
    pensar.pensar("cómo funciona", "deepseek", modelo_deepseek="deepseek-v4-pro")
    assert visto["modelo"] == "deepseek-v4-pro"
    pensar.pensar("cómo funciona", "deepseek", modelo_deepseek="deepseek-flash")
    assert visto["modelo"] == "deepseek-flash"
    pensar.pensar("cómo funciona", "deepseek", modelo_deepseek="otro")
    assert visto["modelo"] == "modelo-x"


def test_deepseek_con_respuesta_vacia_sigue_sin_ia(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setenv("REMI_PENSADOR", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave")
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    monkeypatch.setattr(pensar, "_llamar_deepseek", lambda *a: {"choices": []})
    assert pensar.pensar("algo") is None


def test_la_clave_de_deepseek_no_se_exporta_a_la_cli_de_claude(monkeypatch, tmp_path):
    """La clave se lee del .env a un dict; el subproceso de Claude no la ve."""
    pensar = _importar_pensar()
    ruta = tmp_path / ".env"
    ruta.write_text("DEEPSEEK_API_KEY=secreta\nREMI_PENSADOR=claude\n")
    monkeypatch.setattr(pensar, "RUTA_ENV", ruta)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert pensar._ajuste("DEEPSEEK_API_KEY", "") == "secreta"
    assert "DEEPSEEK_API_KEY" not in pensar._entorno()


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
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(pensar.shutil if hasattr(pensar, "shutil") else __import__("shutil"), "which", lambda _b: None)
    motores = {m.id: m for m in pensar.motores_disponibles()}
    assert set(motores) == {"claude", "venice", "deepseek", "ollama"}
    assert motores["claude"].disponible is False and "claude" in motores["claude"].detalle
    assert motores["venice"].disponible is False and "VENICE_API_KEY" in motores["venice"].detalle
    assert motores["deepseek"].disponible is False and "DEEPSEEK_API_KEY" in motores["deepseek"].detalle


def test_deepseek_disponible_cuando_hay_clave(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-de-prueba")
    motores = {m.id: m for m in pensar.motores_disponibles()}
    assert motores["deepseek"].disponible is True
    assert "DeepSeek" in motores["deepseek"].detalle


# — Ollama, local —


def test_ollama_lee_el_texto_y_marca_local(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setenv("REMI_OLLAMA_MODELO", "gemma3:4b")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    visto = {}

    def falsa(nombre_modelo, instrucciones, frase):
        visto.update(modelo=nombre_modelo, frase=frase)
        return {"model": "gemma3:4b", "choices": [{"message": {"content": "Abre el correo."}}],
                "usage": {"prompt_tokens": 400, "completion_tokens": 5}}

    monkeypatch.setattr(pensar, "_llamar_ollama", falsa)
    pensado = pensar.pensar("tengo el correo lleno", "ollama")
    assert pensado is not None
    assert pensado.paso_minimo == "Abre el correo."
    assert pensado.modelo == "ollama/gemma3:4b"
    assert visto["modelo"] == "gemma3:4b"


def test_ollama_apagado_sigue_sin_ia(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])

    def caido(*_a):
        raise pensar.httpx.ConnectError("connection refused")

    monkeypatch.setattr(pensar, "_llamar_ollama", caido)
    assert pensar.pensar("algo", "ollama") is None


def test_ollama_sin_pedir_clave_alguna(monkeypatch, tmp_path):
    """Local: nunca manda Authorization."""
    pensar = _importar_pensar()
    visto = {}

    def falso_post(url, headers=None, json=None, timeout=None):
        visto.update(url=url, headers=headers)

        class R:
            def raise_for_status(self): pass
            def json(self): return {"choices": [{"message": {"content": "ok"}}]}
        return R()

    monkeypatch.setattr(pensar.httpx, "post", falso_post)
    pensar._llamar_ollama("gemma3:4b", "instr", "frase")
    assert visto["url"].startswith("http://127.0.0.1:11434")
    assert "Authorization" not in visto["headers"]


def test_motores_disponibles_incluye_ollama_y_dice_que_le_falta(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_modelos_de_ollama", lambda: None)
    m = {x.id: x for x in pensar.motores_disponibles()}
    assert m["ollama"].disponible is False and "no está sirviendo" in m["ollama"].detalle

    monkeypatch.setattr(pensar, "_modelos_de_ollama", lambda: ["llama3.2:latest"])
    m = {x.id: x for x in pensar.motores_disponibles()}
    assert m["ollama"].disponible is False and "ollama pull" in m["ollama"].detalle

    monkeypatch.setattr(pensar, "_modelos_de_ollama", lambda: ["gemma3:4b"])
    m = {x.id: x for x in pensar.motores_disponibles()}
    assert m["ollama"].disponible is True and "local" in m["ollama"].detalle


# — Sonnet con Haiku de respaldo —


def test_si_sonnet_tarda_o_falla_contesta_haiku(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    modelos = []

    def falso_run(comando, **kwargs):
        m = comando[comando.index("--model") + 1]
        modelos.append((m, kwargs["timeout"]))
        if m == "sonnet":
            raise subprocess.TimeoutExpired(cmd="claude", timeout=kwargs["timeout"])
        return _salida_cli(result="Respuesta de respaldo.")

    monkeypatch.setattr(pensar.subprocess, "run", falso_run)
    pensado = pensar.pensar("algo")
    assert pensado is not None and pensado.paso_minimo == "Respuesta de respaldo."
    # equilibrio (25 s) cae a rápido (8 s).
    assert modelos == [("sonnet", 45.0), ("haiku", 20.0)]


def test_si_sonnet_contesta_no_se_llama_a_haiku(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    modelos = []

    def falso_run(comando, **kwargs):
        modelos.append(comando[comando.index("--model") + 1])
        return _salida_cli()

    monkeypatch.setattr(pensar.subprocess, "run", falso_run)
    assert pensar.pensar("algo") is not None
    assert modelos == ["sonnet"]


def test_el_log_dice_modo_cacheados_y_libros(monkeypatch, capsys):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "_indice", lambda: [])

    def falso_run(comando, **kwargs):
        # El estante deja la marca con el tema que se leyó.
        import json as _json
        ruta_cfg = comando[comando.index("--mcp-config") + 1]
        marca = _json.loads(open(ruta_cfg).read())["mcpServers"]["memoria"]["env"]["REMI_MARCA_LECTURA"]
        open(marca, "a").write("upvisuals\n")
        return _salida_cli(usage={"input_tokens": 4, "output_tokens": 300,
                                  "cache_read_input_tokens": 5200, "cache_creation_input_tokens": 900})

    monkeypatch.setattr(pensar.subprocess, "run", falso_run)
    pensado = pensar.pensar("¿qué tengo pendiente con Alfonso?", "claude", "equilibrio")
    assert pensado is not None and pensado.leyo_memoria
    linea = [l for l in capsys.readouterr().err.splitlines() if l.startswith("[claude] modo=")][0]
    for pedazo in ("modo=equilibrio", "entrada=4", "cache_leida=5200", "cache_escrita=900",
                   "salida=300", "leyó=sí", "libros=upvisuals", "ms="):
        assert pedazo in linea, pedazo


def test_buscar_solo_cuando_se_pide():
    import clasificar

    assert clasificar.pide_busqueda("Buscá el precio del dominio remi.co")
    assert clasificar.pide_busqueda("buscame cómo se instala whisper-server")
    assert not clasificar.pide_busqueda("¿qué tengo pendiente con Alfonso?")
    assert not clasificar.pide_busqueda("voy a buscar las llaves")


def test_websearch_solo_en_el_mensaje_que_busca(tmp_path):
    pensar = _importar_pensar()
    sin = pensar._comando("sonnet", "x", tmp_path / "mcp.json")
    con = pensar._comando("sonnet", "x", tmp_path / "mcp.json", buscar=True)
    assert "WebSearch" not in sin[sin.index("--tools") + 1]
    assert "WebSearch" not in sin[sin.index("--allowedTools") + 1]
    assert con[con.index("--tools") + 1] == "Read,Grep,Glob,WebSearch"
    assert "WebSearch" in con[con.index("--allowedTools") + 1]


# — La trastienda (config/motores.json) —


def test_trastienda_lee_config_motores_json(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    ruta = tmp_path / "motores.json"
    ruta.write_text('{"trastienda": ["groq/kimi-k2", "openrouter/deepseek-flash", "ollama/gemma3:4b"]}')
    monkeypatch.setattr(pensar, "RUTA_MOTORES", ruta)
    assert pensar.trastienda() == [
        ("groq", "kimi-k2"),
        ("openrouter", "deepseek-flash"),
        ("ollama", "gemma3:4b"),
    ]


def test_trastienda_sin_archivo_o_mal_formado_cae_a_la_cadena_por_defecto(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_MOTORES", tmp_path / "no-existe.json")
    assert pensar.trastienda() == list(pensar.TRASTIENDA_POR_DEFECTO)

    rota = tmp_path / "rota.json"
    rota.write_text("esto no es json")
    monkeypatch.setattr(pensar, "RUTA_MOTORES", rota)
    assert pensar.trastienda() == list(pensar.TRASTIENDA_POR_DEFECTO)

    vacia = tmp_path / "vacia.json"
    vacia.write_text('{"trastienda": []}')
    monkeypatch.setattr(pensar, "RUTA_MOTORES", vacia)
    assert pensar.trastienda() == list(pensar.TRASTIENDA_POR_DEFECTO)


def test_pensar_con_trastienda_cae_al_siguiente_si_uno_no_contesta(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_MOTORES", tmp_path / "no-existe.json")
    llamados = []

    def falsa_llamada(proveedor, modelo, instrucciones, frase):
        llamados.append(proveedor)
        if proveedor == "groq":
            raise pensar.httpx.ConnectError("no hay red")
        if proveedor == "openrouter":
            return {"choices": []}  # respuesta vacía
        return {"choices": [{"message": {"content": "de ollama"}}], "usage": {}}

    monkeypatch.setattr(pensar, "_llamar_proveedor", falsa_llamada)
    pensado = pensar.pensar_con_trastienda("pedido", "instrucciones")
    assert pensado is not None
    assert pensado.paso_minimo == "de ollama"
    assert pensado.motor_usado == "ollama"
    assert llamados == ["groq", "openrouter", "ollama"]


def test_pensar_con_trastienda_usa_aceptar_para_seguir_cayendo(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_MOTORES", tmp_path / "no-existe.json")

    def falsa_llamada(proveedor, modelo, instrucciones, frase):
        return {"choices": [{"message": {"content": proveedor}}], "usage": {}}

    monkeypatch.setattr(pensar, "_llamar_proveedor", falsa_llamada)
    pensado = pensar.pensar_con_trastienda(
        "pedido", "instrucciones", aceptar=lambda p: p.paso_minimo == "ollama"
    )
    assert pensado is not None and pensado.motor_usado == "ollama"


def test_pensar_con_trastienda_ninguno_sirve_devuelve_none(monkeypatch, tmp_path):
    pensar = _importar_pensar()
    monkeypatch.setattr(pensar, "RUTA_MOTORES", tmp_path / "no-existe.json")
    monkeypatch.setattr(pensar, "_llamar_proveedor", lambda *a, **k: {"choices": []})
    assert pensar.pensar_con_trastienda("pedido", "instrucciones") is None

"""Fase 3a: Remi piensa de verdad. Lo que no puede romperse."""
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _pensar():
    for nombre in ("pensar", "db", "modelos", "sembrar_conocimiento"):
        sys.modules.pop(nombre, None)
    import pensar

    return pensar


# — El carácter es el system prompt —


def test_el_prompt_contiene_caracter_md(tmp_path, monkeypatch):
    caracter = tmp_path / "caracter.md"
    caracter.write_text("Sos Remi. Frase única de prueba: LUCHO-7731.")
    monkeypatch.setenv("REMI_CARACTER", str(caracter))
    pensar = _pensar()

    prompt = pensar.instrucciones_con_indice([])
    assert "LUCHO-7731" in prompt

    # Se lee en cada mensaje: editarlo cambia a Remi sin reiniciar.
    caracter.write_text("Sos Remi. Ahora dice OTRA-2244.")
    assert "OTRA-2244" in pensar.instrucciones_con_indice([])
    assert "LUCHO-7731" not in pensar.instrucciones_con_indice([])


def test_sin_caracter_usa_el_de_respaldo(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CARACTER", str(tmp_path / "no-existe.md"))
    pensar = _pensar()
    assert pensar.instrucciones_con_indice([]).startswith(pensar.CARACTER_DE_RESPALDO)


# — Una línea del índice por archivo de proyecto —


def _ficha(carpeta, nombre, tema, cuerpo="Detalle."):
    (carpeta / nombre).write_text(
        f"---\ntitulo: Proyecto {tema}\ntema: {tema}\nresumen: Resumen de {tema}.\n---\n{cuerpo}\n"
    )


def test_el_indice_tiene_una_linea_por_archivo_de_proyecto(tmp_path, monkeypatch):
    carpeta = tmp_path / "proyectos"
    carpeta.mkdir()
    for tema in ("upvisuals", "malik", "omniway"):
        _ficha(carpeta, f"{tema}.md", tema)
    (carpeta / "suelto.md").write_text("sin frontmatter\n")
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    pensar = _pensar()
    import db
    import sembrar_conocimiento

    assert sembrar_conocimiento.sembrar() == {"creadas": 3, "actualizadas": 0, "iguales": 0, "saltadas": 1}
    conexion = db.conectar()
    indice = db.indice_memoria(conexion)
    conexion.close()
    prompt = pensar.instrucciones_con_indice(indice)
    for tema in ("upvisuals", "malik", "omniway"):
        assert sum(1 for linea in prompt.splitlines() if f"· {tema} · Proyecto {tema}" in linea) == 1
    # El cuerpo no: para eso está `leer`.
    assert "Detalle." not in prompt


def test_sembrar_es_idempotente_por_tema_y_actualiza_si_cambio(tmp_path, monkeypatch):
    carpeta = tmp_path / "proyectos"
    carpeta.mkdir()
    _ficha(carpeta, "upvisuals.md", "upvisuals", cuerpo="Fase 1 USD 5.000.")
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    _pensar()
    import db
    import sembrar_conocimiento

    assert sembrar_conocimiento.sembrar()["creadas"] == 1
    assert sembrar_conocimiento.sembrar()["iguales"] == 1
    _ficha(carpeta, "upvisuals.md", "upvisuals", cuerpo="Fase 1 USD 5.500.")
    assert sembrar_conocimiento.sembrar()["actualizadas"] == 1

    conexion = db.conectar()
    entradas = db.memorias_por_tema(conexion, "upvisuals")
    conexion.close()
    assert len(entradas) == 1
    assert entradas[0].cuerpo == "Fase 1 USD 5.500."
    assert entradas[0].fuente == "manual"


# — La conversación: 12 turnos de la última hora —


def test_con_13_turnos_viajan_los_ultimos_10(monkeypatch):
    pensar = _pensar()
    import db

    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    for i in range(13):
        db.guardar_turno(conexion, "juan" if i % 2 == 0 else "remi", f"turno-{i:02d}", ahora - timedelta(minutes=13 - i))
    conexion.close()

    turnos = pensar._turnos()
    assert len(turnos) == 10
    # Viajan literales los 10 más nuevos, del más viejo al más nuevo.
    assert [t.texto for t in turnos] == [f"turno-{i:02d}" for i in range(3, 13)]

    mensaje = pensar.mensaje_con_historia("¿y cuándo arranco?", turnos)
    assert "turno-02" not in mensaje
    assert "turno-12" in mensaje
    assert mensaje.rstrip().endswith("¿y cuándo arranco?")


def test_pasada_la_hora_la_conversacion_es_nueva(monkeypatch):
    pensar = _pensar()
    import db

    conexion = db.conectar()
    db.guardar_turno(conexion, "juan", "de hace dos horas", datetime.now(timezone.utc) - timedelta(hours=2))
    conexion.close()
    assert pensar._turnos() == []
    assert pensar.mensaje_con_historia("hola", []) == "hola"


def test_pensar_guarda_los_dos_turnos_y_el_segundo_lleva_el_primero(monkeypatch, tmp_path):
    pensar = _pensar()
    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    vistos = []

    def falso_claude(mensaje, instrucciones, indice, modo=None, nivel=None, buscar=False):
        vistos.append(mensaje)
        return pensar.Pensado("Tenés pendiente la Fase 1.", 1, 1, "sonnet")

    monkeypatch.setattr(pensar, "_pensar_con_claude", falso_claude)
    pensar.pensar("¿qué tengo pendiente con Alfonso?", "claude")
    pensar.pensar("¿y cuándo arranco?", "claude")

    assert vistos[0] == "¿qué tengo pendiente con Alfonso?"
    assert "Juan Camilo: ¿qué tengo pendiente con Alfonso?" in vistos[1]
    assert "Remi: Tenés pendiente la Fase 1." in vistos[1]


# — «sin pensar» no llama al modelo —


def test_sin_pensar_no_llama_al_modelo(monkeypatch):
    for nombre in ("servidor", "pensar", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import servidor

    def explota(*_a, **_k):
        raise AssertionError("«sin pensar» no puede llamar al modelo")

    monkeypatch.setattr(servidor.pensar, "pensar", explota)
    cliente = TestClient(servidor.app)
    for texto in ("¿qué tengo pendiente con Alfonso?", "voy a revisar el contrato", "listo"):
        respuesta = cliente.post("/mensaje", json={"texto": texto, "think": False})
        assert respuesta.status_code == 200
        assert respuesta.json()["tokens"] is None


# — Cerebro v1: 10 literales + resumen vivo —


def _catorce_turnos(db):
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    for i in range(14):
        conversacion = db.guardar_turno(
            conexion, "juan" if i % 2 == 0 else "remi", f"turno-{i:02d}", ahora - timedelta(minutes=14 - i)
        )
    conexion.close()
    return conversacion


def test_con_14_turnos_viajan_10_literales_y_el_resumen(monkeypatch):
    pensar = _pensar()
    import db

    conversacion = _catorce_turnos(db)
    vistos = []

    def resumidor(resumen, salientes):
        vistos.append([t.texto for t in salientes])
        return "Hablaron de Alfonso: Fase 1 de USD 5.000, arranca pagada completa."

    assert pensar.actualizar_resumen(conversacion, resumidor) is True
    # Salieron de los 10 literales los 4 primeros, y solo esos se resumieron.
    assert vistos == [["turno-00", "turno-01", "turno-02", "turno-03"]]
    # Volver a llamar sin turnos nuevos no resume de nuevo.
    assert pensar.actualizar_resumen(conversacion, resumidor) is False

    turnos, resumen = pensar._conversacion()
    assert [t.texto for t in turnos] == [f"turno-{i:02d}" for i in range(4, 14)]
    mensaje = pensar.mensaje_con_historia("¿y cuándo arranco?", turnos, resumen)
    assert "Fase 1 de USD 5.000" in mensaje
    for i in range(4, 14):
        assert f"turno-{i:02d}" in mensaje
    for i in range(4):
        assert f"turno-{i:02d}" not in mensaje
    assert mensaje.rstrip().endswith("¿y cuándo arranco?")


def test_si_el_resumidor_falla_no_se_pierde_nada(monkeypatch):
    pensar = _pensar()
    import db

    conversacion = _catorce_turnos(db)
    assert pensar.actualizar_resumen(conversacion, lambda r, s: None) is False
    # Queda para la próxima: con un resumidor que anda, entran los mismos 4.
    vistos = []
    pensar.actualizar_resumen(conversacion, lambda r, s: (vistos.append(len(s)), "ok")[1])
    assert vistos == [4]


def test_el_resumen_va_por_la_trastienda(monkeypatch):
    pensar = _pensar()
    visto = {}

    def falsa_trastienda(pedido, instrucciones, aceptar=None):
        visto["pedido"] = pedido
        visto["instrucciones"] = instrucciones
        return pensar.Pensado("resumen nuevo", 0, 0, "kimi-k2", motor_usado="groq")

    monkeypatch.setattr(pensar, "pensar_con_trastienda", falsa_trastienda)
    assert pensar.resumir("lo de antes", []) == "resumen nuevo"
    assert visto["instrucciones"] == pensar.INSTRUCCIONES_RESUMEN
    assert "lo de antes" in visto["pedido"]


def test_tras_60_minutos_sin_turnos_la_conversacion_es_nueva(monkeypatch):
    _pensar()
    import db

    antes = datetime.now(timezone.utc) - timedelta(minutes=90)
    conexion = db.conectar()
    vieja = db.guardar_turno(conexion, "juan", "hace hora y media", antes)
    nueva = db.guardar_turno(conexion, "juan", "ahora", datetime.now(timezone.utc))
    conexion.close()
    assert vieja != nueva



# — Modo Prompt (3b) —


def test_modo_prompt_arma_un_encargo_sin_guardar_nada(monkeypatch):
    for nombre in ("servidor", "pensar", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import servidor

    visto = {}

    def falso_pensar(frase, motor=None, modo=None, sistema=None, nivel=None, **_k):
        visto.update(frase=frase, modo=modo, sistema=sistema)
        return servidor.pensar.Pensado("QUÉ\nArreglar la X.\n\nDÓNDE\napps/ventanita", 1, 1, "sonnet")

    monkeypatch.setattr(servidor.pensar, "pensar", falso_pensar)
    cliente = TestClient(servidor.app)
    cuerpo = cliente.post(
        "/mensaje",
        json={"texto": "voy a arreglar la x de la ventanita", "think": True, "modo": "prompt"},
    ).json()
    assert cuerpo["tipo"] == "encargo"
    assert cuerpo["texto"].startswith("QUÉ")
    assert cuerpo["voz"] == "Listo, lo tenés para copiar."
    assert cuerpo["tarea"] is None
    # Aunque dice «voy a…», no abrió un bloque: el modo Prompt no clasifica.
    assert visto["modo"] == "equilibrio"
    assert "LISTO CUANDO" in visto["sistema"]
    import db
    conexion = db.conectar()
    assert conexion.execute("select count(*) from tareas").fetchone()[0] == 0
    assert conexion.execute("select count(*) from ideas").fetchone()[0] == 0
    conexion.close()


def test_el_encargo_usa_su_system_prompt_con_la_mente(monkeypatch):
    pensar = _pensar()
    prompt = pensar.instrucciones_con_indice([], pensar.sistema_encargo())
    assert "LISTO CUANDO" in prompt and "QUÉ NO HACER" in prompt
    assert pensar.caracter()[:40] not in prompt



# — Markdown: Kokoro no lee los símbolos (3b) —


def test_la_voz_llega_sin_markdown():
    sys.modules.pop("servidor", None)
    import servidor

    crudo = "Lo que está abierto:\n\n- **Pagos de Fase 1 (USD 5.000):** USD 1.500 al inicio\n## Contrato\n`ley` de *Wyoming*"
    voz = servidor.sin_markdown(crudo)
    for simbolo in ("*", "#", "`", "- "):
        assert simbolo not in voz, simbolo
    assert "Pagos de Fase 1 (USD 5.000): USD 1.500 al inicio." in voz
    assert "ley de Wyoming" in voz
    assert "*" not in servidor.para_hablar(crudo)

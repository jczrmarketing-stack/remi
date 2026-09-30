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
    assert pensar.instrucciones_con_indice([]) == pensar.CARACTER_DE_RESPALDO


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


def test_con_13_turnos_solo_viajan_12(monkeypatch):
    pensar = _pensar()
    import db

    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    for i in range(13):
        db.guardar_turno(conexion, "juan" if i % 2 == 0 else "remi", f"turno-{i:02d}", ahora - timedelta(minutes=13 - i))
    conexion.close()

    turnos = pensar._turnos()
    assert len(turnos) == 12
    # Viajan los 12 más nuevos, del más viejo al más nuevo: el 00 se cae.
    assert [t.texto for t in turnos] == [f"turno-{i:02d}" for i in range(1, 13)]

    mensaje = pensar.mensaje_con_historia("¿y cuándo arranco?", turnos)
    assert "turno-00" not in mensaje
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

    def falso_claude(mensaje, instrucciones, indice, modo=None):
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

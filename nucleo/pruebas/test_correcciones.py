"""Aprender de las correcciones (Biblia Parte VI, Fase S punto 4).

Remi propone, nunca guarda solo (ley 3): el flujo completo con git real de
la bóveda, como test_boveda_git.py — no se simula git ni el commit.
"""
import importlib
import subprocess
import sys
from datetime import datetime, timezone

import pytest

import correcciones
import db
import sembrar_conocimiento


def _preparar_boveda(tmp_path, monkeypatch):
    boveda = tmp_path / "boveda"
    proyectos = boveda / "proyectos"
    oficios = boveda / "oficios"
    proyectos.mkdir(parents=True)
    oficios.mkdir(parents=True)
    (oficios / "mi-voz.md").write_text(
        "---\ntitulo: Mi voz\ntema: oficio-mi-voz\nresumen: Cómo escribe Juan Camilo.\n"
        "claves: [voz, tono, estilo]\ntipo: oficio\n---\n\n## Nunca\n- Formal de más.\n"
    )
    (oficios / "mantenimiento.md").write_text(
        "---\ntitulo: Mantenimiento\ntema: oficio-mantenimiento\n"
        "resumen: La mensualidad y el soporte.\nclaves: [mensualidad, retainer, soporte]\n"
        "tipo: oficio\n---\n\n## Qué es\nLa cuota mensual.\n"
    )
    subprocess.run(["git", "init", "-q", str(boveda)], check=True)
    subprocess.run(["git", "-C", str(boveda), "config", "user.email", "remi@local"], check=True)
    subprocess.run(["git", "-C", str(boveda), "config", "user.name", "Remi"], check=True)
    subprocess.run(["git", "-C", str(boveda), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(boveda), "commit", "-q", "-m", "inicial"], check=True)

    monkeypatch.setenv("REMI_CONOCIMIENTO", str(proyectos))
    import boveda_git

    monkeypatch.setattr(boveda_git.libros, "carpeta", lambda: proyectos)
    return boveda, oficios


def _git_log(carpeta):
    return subprocess.run(
        ["git", "-C", str(carpeta), "log", "--oneline"], capture_output=True, text=True, check=True
    ).stdout


# — Detección, sin IA —


@pytest.mark.parametrize(
    "frase",
    ["no, así no", "No, así no.", "yo no diría eso", "yo no diría así", "acordate: nunca prometas fecha sin alcance"],
)
def test_es_correccion(frase):
    assert correcciones.es_correccion(frase)


@pytest.mark.parametrize("frase", ["armame un encargo para el executor", "me escribió Alfonso: hola", "voy a llamar"])
def test_no_es_correccion(frase):
    assert not correcciones.es_correccion(frase)


@pytest.mark.parametrize("frase", ["sí", "si, dale", "dale", "guardala", "anotalo", "confirmo"])
def test_es_confirmacion(frase):
    assert correcciones.es_confirmacion(frase)


@pytest.mark.parametrize("frase", ["no", "ahora no", "mejor no"])
def test_no_es_confirmacion(frase):
    assert not correcciones.es_confirmacion(frase)


# — La regla nunca inventa: cita literal —


def test_acordate_cita_literal_sin_necesitar_turno_anterior():
    resultado = correcciones.proponer_regla("acordate: nunca prometas fecha sin ver el alcance", None)
    assert resultado is not None
    _oficio, regla = resultado
    assert regla == "nunca prometas fecha sin ver el alcance"


def test_asi_no_cita_lo_que_remi_dijo():
    resultado = correcciones.proponer_regla("no, así no", "Quedate tranquilo, esto es urgente.")
    assert resultado is not None
    _oficio, regla = resultado
    assert regla == "No decir: «Quedate tranquilo, esto es urgente.»."


def test_asi_no_sin_turno_anterior_no_propone_nada():
    """Sin nada de Remi para citar, no hay cómo proponer sin inventar."""
    assert correcciones.proponer_regla("no, así no", None) is None
    assert correcciones.proponer_regla("no, así no", "") is None


def test_oficio_destino_matchea_por_claves(tmp_path, monkeypatch):
    _preparar_boveda(tmp_path, monkeypatch)
    assert correcciones.oficio_destino("la mensualidad y el retainer") == "mantenimiento"
    assert correcciones.oficio_destino("algo que no matchea nada") == "mi-voz"


# — El flujo completo, con DB y git reales —


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("correcciones", "db"):
        sys.modules.pop(nombre, None)
    import db as db_mod
    import correcciones as correcciones_mod

    importlib.reload(db_mod)
    importlib.reload(correcciones_mod)
    return correcciones_mod, db_mod


def test_flujo_completo_propone_confirma_y_commitea(tmp_path, monkeypatch):
    boveda, oficios = _preparar_boveda(tmp_path, monkeypatch)
    correcciones_mod, db_mod = _arrancar(tmp_path, monkeypatch)

    ahora = datetime.now(timezone.utc)
    conexion = db_mod.conectar()
    try:
        conversacion_id = db_mod.guardar_turno(conexion, "juan", "¿cómo le contesto a Alfonso?", ahora)
        db_mod.guardar_turno(conexion, "remi", "Quedate tranquilo, esto es urgente.", ahora)
    finally:
        conexion.close()

    antes = _git_log(boveda)
    propuesta = correcciones_mod.proponer("no, así no", ahora)
    assert propuesta == ("mi-voz", "No decir: «Quedate tranquilo, esto es urgente.».")
    # Proponer no escribe nada todavía: sin confirmación, no hay commit.
    assert _git_log(boveda) == antes

    aplicada = correcciones_mod.revisar_confirmacion("dale", ahora)
    assert aplicada == ("mi-voz", "No decir: «Quedate tranquilo, esto es urgente.».")

    contenido = (oficios / "mi-voz.md").read_text()
    assert "No decir: «Quedate tranquilo, esto es urgente.»." in contenido

    log = _git_log(boveda)
    assert "regla nueva de una corrección" in log


def test_sin_confirmacion_no_se_guarda_nada(tmp_path, monkeypatch):
    boveda, oficios = _preparar_boveda(tmp_path, monkeypatch)
    correcciones_mod, db_mod = _arrancar(tmp_path, monkeypatch)

    ahora = datetime.now(timezone.utc)
    conexion = db_mod.conectar()
    try:
        db_mod.guardar_turno(conexion, "juan", "¿cómo le contesto a Alfonso?", ahora)
        db_mod.guardar_turno(conexion, "remi", "Quedate tranquilo, esto es urgente.", ahora)
    finally:
        conexion.close()

    correcciones_mod.proponer("no, así no", ahora)
    antes = _git_log(boveda)
    contenido_antes = (oficios / "mi-voz.md").read_text()

    resultado = correcciones_mod.revisar_confirmacion("mejor sigamos con otra cosa", ahora)
    assert resultado is None

    assert (oficios / "mi-voz.md").read_text() == contenido_antes
    assert _git_log(boveda) == antes

    # La propuesta ya se descartó: una segunda «dale» no revive nada.
    assert db_mod.propuesta_pendiente(db_mod.conectar(), "cualquiera") is None


def test_endpoint_mensaje_flujo_de_correccion_de_punta_a_punta(tmp_path, monkeypatch):
    boveda, oficios = _preparar_boveda(tmp_path, monkeypatch)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar", "correcciones"):
        sys.modules.pop(nombre, None)
    import db as db_mod
    import servidor as servidor_mod
    from fastapi.testclient import TestClient

    importlib.reload(db_mod)
    importlib.reload(servidor_mod)

    def falso_pensar(frase, motor=None, modo=None, base=None, **_k):
        # La real `pensar.pensar()` guarda los dos turnos (juan y remi) en
        # la conversación vigente; el mock lo simula para que la detección
        # de correcciones tenga de dónde citar lo que "dijo" Remi.
        ahora = datetime.now(timezone.utc)
        conexion = db_mod.conectar()
        try:
            db_mod.guardar_turno(conexion, "juan", frase, ahora)
            db_mod.guardar_turno(conexion, "remi", "Quedate tranquilo, esto es urgente.", ahora)
        finally:
            conexion.close()
        return servidor_mod.pensar.Pensado(
            paso_minimo="Quedate tranquilo, esto es urgente.",
            tokens_entrada=10,
            tokens_salida=8,
            modelo="modelo-de-prueba",
        )

    monkeypatch.setattr(servidor_mod.pensar, "pensar", falso_pensar)
    cliente = TestClient(servidor_mod.app)

    primero = cliente.post("/mensaje", json={"texto": "¿cómo le contesto a Alfonso?", "think": True}).json()
    assert primero["texto"] == "Quedate tranquilo, esto es urgente."

    segundo = cliente.post("/mensaje", json={"texto": "no, así no"}).json()
    assert segundo["tipo"] == "correccion"
    assert "Quedate tranquilo, esto es urgente." in segundo["texto"]

    tercero = cliente.post("/mensaje", json={"texto": "dale"}).json()
    assert tercero["tipo"] == "correccion"
    assert "Guardado" in tercero["texto"]

    contenido = (oficios / "mi-voz.md").read_text()
    assert "No decir: «Quedate tranquilo, esto es urgente.»." in contenido
    assert "regla nueva de una corrección" in _git_log(boveda)

    # Nunca pasó por ideas ni tareas: es aprendizaje, no un pedido.
    conexion = db_mod.conectar()
    try:
        ideas = conexion.execute("select count(*) from ideas").fetchone()[0]
        tareas = conexion.execute("select count(*) from tareas").fetchone()[0]
    finally:
        conexion.close()
    assert ideas == 0
    assert tareas == 0

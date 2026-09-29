"""Lo que decís no siempre es una tarea.

Ley 6: lo suelto enfría 48 h en la Bandeja. Ley 1: solo un bloque que
alguien abrió y cerró tiene duración. Estas pruebas cuidan que /mensaje no
vuelva a convertir cada frase en una tarea con un cronómetro corriendo.
"""
import importlib
import sys
from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar", "clasificar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _contar(servidor):
    import db

    conexion = db.conectar()
    try:
        tareas = conexion.execute("SELECT COUNT(*) c FROM tareas").fetchone()["c"]
        sesiones = conexion.execute("SELECT COUNT(*) c FROM sesiones").fetchone()["c"]
        ideas = conexion.execute("SELECT COUNT(*) c FROM ideas").fetchone()["c"]
    finally:
        conexion.close()
    return {"tareas": tareas, "sesiones": sesiones, "ideas": ideas}


# — Una idea enfría; no abre nada —


def test_una_idea_va_a_la_bandeja_y_no_crea_tarea_ni_sesion(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "se me ocurrió vender plantillas"})
    cuerpo = respuesta.json()

    assert cuerpo["tipo"] == "idea"
    assert cuerpo["tarea"] is None
    assert cuerpo["sesion"] is None
    assert cuerpo["voz"] == "Guardada. La miramos en dos días."
    assert _contar(servidor) == {"tareas": 0, "sesiones": 0, "ideas": 1}


def test_la_idea_enfria_48_horas_y_queda_enfriando(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    import db

    cliente.post("/mensaje", json={"texto": "y si hacemos un bot para la agencia", "origen": "voz"})

    conexion = db.conectar()
    idea = db.listar_ideas(conexion)[0]
    conexion.close()

    assert idea.estado == "enfriando"
    assert idea.origen == "voz"
    espera = idea.enfria_hasta - idea.creada_en
    assert timedelta(hours=47, minutes=59) < espera < timedelta(hours=48, minutes=1)


# — Un arranque abre el bloque; «listo» lo cierra —


def test_ciclo_completo_abrir_y_cerrar(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    import db

    abierto = cliente.post("/mensaje", json={"texto": "voy a escribir la propuesta ahora"}).json()
    assert abierto["tipo"] == "hoy"
    assert abierto["tarea"]["estado"] == "hoy"
    assert abierto["sesion"]["fin"] is None
    assert _contar(servidor) == {"tareas": 1, "sesiones": 1, "ideas": 0}

    cerrado = cliente.post("/mensaje", json={"texto": "listo"}).json()
    assert cerrado["tipo"] == "hecha"
    assert cerrado["sesion"]["fin"] is not None
    assert cerrado["tarea"]["estado"] == "hecha"
    assert cerrado["sesion"]["id"] == abierto["sesion"]["id"]
    # Cerrar no crea nada nuevo.
    assert _contar(servidor) == {"tareas": 1, "sesiones": 1, "ideas": 0}

    conexion = db.conectar()
    assert db.sesion_abierta_mas_reciente(conexion) is None
    conexion.close()


def test_al_cerrar_dice_cuanto_tardo(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    import db

    abierto = cliente.post("/mensaje", json={"texto": "arranco con el contrato"}).json()

    # Mover el inicio hacia atrás es la única forma de probar la duración
    # sin esperar de verdad.
    conexion = db.conectar()
    inicio = datetime.fromisoformat(abierto["sesion"]["inicio"]) - timedelta(minutes=100)
    conexion.execute(
        "UPDATE sesiones SET inicio = ? WHERE id = ?",
        (inicio.isoformat(), abierto["sesion"]["id"]),
    )
    conexion.commit()
    conexion.close()

    assert cliente.post("/mensaje", json={"texto": "listo"}).json()["voz"] == "Cerrada. 1 h 40."


def test_cerrar_sin_nada_abierto_no_regana(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "listo"})
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["tipo"] == "hecha"
    assert cuerpo["voz"] == "No había nada abierto."
    # Ley 3: sin contar el fallo, sin «deberías», sin urgir.
    for palabra in ("error", "nada que", "deberías", "otra vez", "fallo"):
        assert palabra not in cuerpo["voz"].lower()
    assert _contar(servidor) == {"tareas": 0, "sesiones": 0, "ideas": 0}


def test_cerrar_dos_veces_es_idempotente(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "voy a revisar el contrato"})
    primera = cliente.post("/mensaje", json={"texto": "listo"}).json()
    segunda = cliente.post("/mensaje", json={"texto": "listo"}).json()

    assert primera["sesion"]["fin"] is not None
    assert segunda["voz"] == "No había nada abierto."
    assert _contar(servidor) == {"tareas": 1, "sesiones": 1, "ideas": 0}


def test_un_listo_cierra_el_bloque_mas_reciente_aunque_sea_de_otra_tarea(tmp_path, monkeypatch):
    """No hace falta decir cuál: cierra el último que quedó abierto."""
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "voy a escribir la propuesta"})
    segundo = cliente.post("/mensaje", json={"texto": "me pongo con los proxies"}).json()

    cerrado = cliente.post("/mensaje", json={"texto": "listo"}).json()
    assert cerrado["sesion"]["id"] == segundo["sesion"]["id"]


# — El formato del tiempo, el mismo de la ventanita —


def test_formato_de_duracion(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)

    assert servidor.formatear_duracion(0) == "0 min"
    assert servidor.formatear_duracion(2) == "2 min"
    assert servidor.formatear_duracion(40) == "40 min"
    assert servidor.formatear_duracion(59) == "59 min"
    assert servidor.formatear_duracion(60) == "1 h"
    assert servidor.formatear_duracion(100) == "1 h 40"
    assert servidor.formatear_duracion(125) == "2 h 05"


# — El tipo lo decide el clasificador, nunca el modelo —


def test_pensar_no_elige_el_tipo(tmp_path, monkeypatch):
    """Aunque el modelo conteste cualquier cosa, una idea sigue siendo idea
    y se guarda: pensar solo cambia lo que Remi contesta."""
    servidor = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda _frase: servidor.pensar.Pensado("Es una tarea urgentísima, hacela ya.", 1, 1, "m"),
    )
    cliente = TestClient(servidor.app)

    cuerpo = cliente.post(
        "/mensaje", json={"texto": "se me ocurrió una app de recetas", "think": True}
    ).json()
    assert cuerpo["tipo"] == "idea"
    assert cuerpo["tarea"] is None
    assert _contar(servidor) == {"tareas": 0, "sesiones": 0, "ideas": 1}


def test_una_idea_sin_think_no_gasta_un_token(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)

    def explota(_frase):
        raise AssertionError("sin think no se piensa")

    monkeypatch.setattr(servidor.pensar, "pensar", explota)
    cliente = TestClient(servidor.app)
    cuerpo = cliente.post("/mensaje", json={"texto": "se me ocurrió una app de recetas"}).json()
    assert cuerpo["voz"] == "Guardada. La miramos en dos días."
    assert cuerpo["tokens"] is None


def test_en_dialogo_una_idea_contesta_pensando(tmp_path, monkeypatch):
    """think=true sobre una idea: se guarda igual y la voz es lo que pensó."""
    servidor = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda _frase: servidor.pensar.Pensado("Empezá por una receta, la que más hacés.", 300, 12, "venice/x"),
    )
    cliente = TestClient(servidor.app)
    cuerpo = cliente.post(
        "/mensaje", json={"texto": "se me ocurrió una app de recetas", "think": True}
    ).json()
    assert cuerpo["voz"] == "Empezá por una receta, la que más hacés."
    assert cuerpo["tokens"] == {"entrada": 300, "salida": 12, "modelo": "venice/x"}
    assert _contar(servidor)["ideas"] == 1


def test_ultima_vez_es_el_bloque_medido_mas_reciente(tmp_path, monkeypatch):
    """El reposo muestra lo último que se midió de verdad. No mira las
    tareas de hoy: al decir «listo» la tarea pasa a `hecha` y sale de esa
    lista, así que ahí nunca estaría el bloque recién cerrado."""
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    import db

    # Sin nada cerrado todavía no hay dato: no se inventa.
    assert cliente.get("/ultima-vez").json()["minutos"] is None

    abierto = cliente.post("/mensaje", json={"texto": "voy a revisar el contrato"}).json()
    assert cliente.get("/ultima-vez").json()["minutos"] is None

    conexion = db.conectar()
    inicio = datetime.fromisoformat(abierto["sesion"]["inicio"]) - timedelta(minutes=2)
    conexion.execute(
        "UPDATE sesiones SET inicio = ? WHERE id = ?",
        (inicio.isoformat(), abierto["sesion"]["id"]),
    )
    conexion.commit()
    conexion.close()

    assert cliente.post("/mensaje", json={"texto": "listo"}).json()["voz"] == "Cerrada. 2 min."
    assert cliente.get("/ultima-vez").json()["minutos"] == 2

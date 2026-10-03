"""T3.5: la pregunta «en el aire» al abrir un bloque — el mensaje siguiente
que no sea arranque, cierre ni pregunta es la respuesta."""
import importlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

SIN_TIPO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo.
"""


def _arrancar(tmp_path, monkeypatch, en_el_chat=True):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in (
        "servidor", "db", "modelos", "libros", "preguntas", "boveda_git", "iniciativa",
        "trabajo", "bandeja", "pensar", "clasificar",
    ):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    # El mecanismo se prueba prendido; por defecto está apagado (3-oct).
    monkeypatch.setattr(servidor.preguntas, "EN_EL_CHAT", en_el_chat)
    return servidor, db


def _marcar_malik_activo(db_mod) -> None:
    conexion = db_mod.conectar()
    try:
        conexion.execute(
            "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), "commit", "/tmp/malik", "malik", "{}", datetime.now(timezone.utc).isoformat()),
        )
        conexion.commit()
    finally:
        conexion.close()


def test_abrir_un_bloque_del_proyecto_deja_la_pregunta_en_el_aire(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    assert respuesta.status_code == 200
    assert "cliente o es tuyo" in respuesta.json()["voz"]


def test_la_siguiente_frase_normal_es_la_respuesta(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    respuesta = cliente.post("/mensaje", json={"texto": "es propio"})

    assert respuesta.json()["tipo"] == "pregunta_respondida"
    assert "tipo: propio" in (tmp_path / "libros" / "malik.md").read_text()


def test_un_arranque_no_se_toma_como_respuesta(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    respuesta = cliente.post("/mensaje", json={"texto": "voy a escribir el contrato"})

    assert respuesta.json()["tipo"] == "hoy"
    assert "tipo:" not in (tmp_path / "libros" / "malik.md").read_text()

    # La pregunta sigue en el aire: una frase normal más tarde la contesta.
    siguiente = cliente.post("/mensaje", json={"texto": "es de un cliente"})
    assert siguiente.json()["tipo"] == "pregunta_respondida"
    assert "tipo: cliente" in (tmp_path / "libros" / "malik.md").read_text()


# — 3-oct: la frase de Juan Camilo terminó como «cliente» de BeaM —
# «No, todo bien… quiero saber qué te falta para dejarlo haciendo mientras
# duermo… el panel web como ventanita» se tomó como la respuesta a una
# pregunta que llevaba horas en el aire.

FRASE_REAL = (
    "No, todo bien, todo bien. Quiero saber qué te falta para dejarlo haciendo mientras duermo "
    "para terminar por completo ... todo el apartado de Remy tanto el panel web como ventanita"
)


def test_una_frase_larga_o_que_pide_algo_no_es_una_respuesta(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    respuesta = cliente.post("/mensaje", json={"texto": FRASE_REAL})

    assert respuesta.json()["tipo"] != "pregunta_respondida"
    assert "tipo:" not in (tmp_path / "libros" / "malik.md").read_text()


def test_la_pregunta_en_el_aire_vence_a_los_10_minutos(tmp_path, monkeypatch):
    from datetime import timedelta

    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})
    import preguntas

    conexion = db_mod.conectar()
    try:
        hace = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        conexion.execute("UPDATE pregunta_en_el_aire SET desde = ?", (hace,))
        conexion.commit()
        assert preguntas.en_el_aire(conexion, datetime.now(timezone.utc)) is None
    finally:
        conexion.close()
    respuesta = cliente.post("/mensaje", json={"texto": "es propio"})
    assert respuesta.json()["tipo"] != "pregunta_respondida"


def test_la_confirmacion_dice_que_guardo_y_donde(tmp_path, monkeypatch):
    servidor, db_mod = _arrancar(tmp_path, monkeypatch)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"})

    voz = cliente.post("/mensaje", json={"texto": "es propio"}).json()["voz"]

    assert voz.startswith("Anotado en Malik") and "es propio" in voz


def test_por_defecto_remi_no_pregunta_en_el_chat(tmp_path, monkeypatch):
    """3-oct, Juan Camilo: los chats son de lo que se está hablando."""
    import preguntas as modulo

    assert modulo.EN_EL_CHAT is False
    servidor, db_mod = _arrancar(tmp_path, monkeypatch, en_el_chat=False)
    _marcar_malik_activo(db_mod)
    cliente = TestClient(servidor.app)

    voz = cliente.post("/mensaje", json={"texto": "voy a revisar la estrategia"}).json()["voz"]
    assert "cliente o es tuyo" not in voz
    assert cliente.post("/mensaje", json={"texto": "es propio"}).json()["tipo"] != "pregunta_respondida"
    assert "tipo:" not in (tmp_path / "libros" / "malik.md").read_text()

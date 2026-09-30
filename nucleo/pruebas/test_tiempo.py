"""«¿Cuánto le metí a X esta semana?» suma Claude y los bloques de Remi."""
import importlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_ESTADO", "0")
    monkeypatch.setenv("REMI_CIERRE", "0")
    for nombre in ("servidor", "db", "trabajo", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _libro(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir()
    (carpeta / "malik.md").write_text(
        "---\ntitulo: Malik — estrategia\ntema: malik\nresumen: Las cuentas.\n"
        "ruta: /tmp/malik\n---\n"
    )


def test_suma_claude_y_el_bloque_de_remi(tmp_path, monkeypatch) -> None:
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    import db
    from modelos import Sesion, Tarea
    from uuid import uuid4

    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        conexion.execute(
            """
            INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin)
            VALUES ('s1', 'malik', '/tmp/malik', ?, ?)
            """,
            ((ahora - timedelta(minutes=40)).isoformat(), ahora.isoformat()),
        )
        tarea = Tarea(
            id=uuid4(),
            titulo="el mosaico",
            proyecto_id=None,
            estado="hoy",
            paso_minimo="un paso",
            estimado_min=None,
            real_min=None,
            compartible=False,
        )
        db.crear_tarea(conexion, tarea)
        db.crear_sesion(
            conexion,
            Sesion(
                id=uuid4(),
                tarea_id=tarea.id,
                inicio=ahora - timedelta(minutes=60),
                fin=ahora,
                real_min=60,
                app_contexto="malik",
            ),
        )
    finally:
        conexion.close()
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "¿cuánto le metí a malik esta semana?", "think": True})

    assert respuesta.json()["tokens"] is None
    assert respuesta.json()["texto"] == "A Malik esta semana: 1 h 40."


def test_sin_inicio_no_inventa_y_cero_no_regaña(tmp_path, monkeypatch) -> None:
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post(
        "/evento",
        json={"tipo": "sesion_fin", "ruta": "/tmp/malik", "datos": {"session_id": "huerfana"}},
    )

    respuesta = cliente.post("/mensaje", json={"texto": "¿cuánto le metí a malik esta semana?"})

    assert respuesta.json()["texto"] == "A Malik esta semana no tengo tiempo medido."
    assert "no trabajaste" not in respuesta.json()["texto"]
    import db

    conexion = db.conectar()
    try:
        filas = conexion.execute("SELECT * FROM trabajo_claude").fetchall()
    finally:
        conexion.close()
    assert filas == []


def test_la_semana_pasada_no_entra_y_un_bloque_abierto_si(tmp_path, monkeypatch) -> None:
    _libro(tmp_path)
    _arrancar(tmp_path, monkeypatch)
    import db
    import trabajo

    ahora = datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    try:
        conexion.execute(
            """
            INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin)
            VALUES ('vieja', 'malik', '/tmp/malik', ?, ?)
            """,
            (
                datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc).isoformat(),
                datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc).isoformat(),
            ),
        )
        conexion.execute(
            """
            INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin)
            VALUES ('abierta', 'malik', '/tmp/malik', ?, NULL)
            """,
            ((ahora - timedelta(minutes=30)).isoformat(),),
        )
        conexion.commit()
    finally:
        conexion.close()

    assert trabajo.minutos_esta_semana("malik", ahora) == 30


def test_un_bloque_nuevo_queda_en_el_proyecto_activo(tmp_path, monkeypatch) -> None:
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/evento", json={"tipo": "commit", "ruta": "/tmp/malik", "datos": {}})
    cliente.post("/mensaje", json={"texto": "vamos con el mosaico", "think": False})
    import db

    conexion = db.conectar()
    try:
        fila = conexion.execute("SELECT app_contexto FROM sesiones").fetchone()
    finally:
        conexion.close()
    assert fila["app_contexto"] == "malik"

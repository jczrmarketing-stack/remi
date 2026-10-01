"""J1 · datos del núcleo (Biblia v3.7): hora y fecha de una tarea, «mañana»
y «vence» para la pantalla Hoy, y la migración que agrega las columnas sin
tocar ninguna fila que ya existía."""
import importlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("servidor", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _dia(servidor, delta: int) -> str:
    return (servidor.hoy_en_bogota() + timedelta(days=delta)).isoformat()


def test_la_migracion_agrega_columnas_y_no_toca_las_filas_viejas(tmp_path, monkeypatch):
    # Una base de antes de la v3.7: las tres tablas sin las columnas nuevas,
    # con una fila cada una.
    ruta = tmp_path / "remi.db"
    vieja = sqlite3.connect(ruta)
    vieja.executescript(
        """
        CREATE TABLE tareas (id TEXT PRIMARY KEY, titulo TEXT NOT NULL, proyecto_id TEXT, estado TEXT NOT NULL,
            paso_minimo TEXT NOT NULL, estimado_min INTEGER, real_min INTEGER, compartible INTEGER NOT NULL);
        CREATE TABLE ideas (id TEXT PRIMARY KEY, texto TEXT NOT NULL, origen TEXT NOT NULL, creada_en TEXT NOT NULL,
            enfria_hasta TEXT NOT NULL, estado TEXT NOT NULL, problema_vision INTEGER);
        CREATE TABLE entregas (id TEXT PRIMARY KEY, cliente TEXT NOT NULL, proyecto_id TEXT NOT NULL, fecha TEXT NOT NULL,
            monto REAL, estado TEXT NOT NULL, compartible INTEGER NOT NULL);
        INSERT INTO tareas VALUES ('11111111-1111-1111-1111-111111111111', 'la de antes', NULL, 'hoy', 'un paso', NULL, NULL, 0);
        INSERT INTO ideas VALUES ('22222222-2222-2222-2222-222222222222', 'una idea de antes', 'texto',
            '2026-09-29T10:00:00+00:00', '2026-10-01T10:00:00+00:00', 'enfriando', NULL);
        INSERT INTO entregas VALUES ('33333333-3333-3333-3333-333333333333', 'Alfonso',
            '44444444-4444-4444-4444-444444444444', '2026-10-18T00:00:00+00:00', 5000, 'camino', 1);
        """
    )
    vieja.commit()
    vieja.close()

    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    hoy = cliente.get("/hoy").json()
    assert [t["tarea"]["titulo"] for t in hoy] == ["la de antes"]
    assert hoy[0]["tarea"]["hora"] is None and hoy[0]["tarea"]["fecha_limite"] is None

    entregas = cliente.get("/entregas").json()
    assert entregas[0]["cliente"] == "Alfonso" and entregas[0]["monto"] == 5000 and entregas[0]["linea"] is None

    import db

    conexion = db.conectar()
    try:
        assert conexion.execute("SELECT COUNT(*) FROM tareas").fetchone()[0] == 1
        assert conexion.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == 1
        assert conexion.execute("SELECT COUNT(*) FROM entregas").fetchone()[0] == 1
        assert conexion.execute("SELECT texto, tema FROM ideas").fetchone()[:] == ("una idea de antes", None)
    finally:
        conexion.close()


def test_planear_una_tarea_no_abre_bloque(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/tarea", json={"titulo": "Enviar factura a Alfonso", "hora": "15:00"})

    assert respuesta.status_code == 201
    tarea = respuesta.json()
    assert tarea["estado"] == "hoy" and tarea["hora"] == "15:00" and tarea["fecha_limite"] is None
    hoy = cliente.get("/hoy").json()
    assert hoy[0]["tarea"]["id"] == tarea["id"]
    # Ley 1: sin bloque abierto no hay sesión que medir.
    assert hoy[0]["sesiones"] == []


def test_una_hora_mal_escrita_no_entra(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    for hora in ("3 pm", "25:00", "9:5", "15:60"):
        assert cliente.post("/tarea", json={"titulo": "x", "hora": hora}).status_code == 422
    assert cliente.post("/tarea", json={"titulo": ""}).status_code == 422


def test_hoy_ordena_por_hora_y_deja_al_final_las_que_no_tienen(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/tarea", json={"titulo": "sin hora"})
    cliente.post("/tarea", json={"titulo": "a las tres", "hora": "15:00"})
    cliente.post("/tarea", json={"titulo": "a las ocho", "hora": "08:00"})

    assert [t["tarea"]["titulo"] for t in cliente.get("/hoy").json()] == ["a las ocho", "a las tres", "sin hora"]


def test_lo_de_manana_nace_en_camino_y_asoma_en_la_agenda(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    manana = cliente.post("/tarea", json={"titulo": "Llamada con el banco", "fecha_limite": _dia(servidor, 1)}).json()

    assert manana["estado"] == "camino"
    # Todavía no es de hoy…
    assert cliente.get("/hoy").json() == []
    # …pero asoma.
    agenda = cliente.get("/hoy/agenda").json()
    assert [t["titulo"] for t in agenda["manana"]] == ["Llamada con el banco"]


def test_cuando_llega_el_dia_la_tarea_aparece_sola_en_hoy(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/tarea", json={"titulo": "Formulario del IRS", "fecha_limite": _dia(servidor, 1)})

    # Pasa un día: «hoy» es el que era mañana.
    siguiente = servidor.hoy_en_bogota() + timedelta(days=1)
    monkeypatch.setattr(servidor, "hoy_en_bogota", lambda ahora=None: siguiente)

    hoy = cliente.get("/hoy").json()
    assert [t["tarea"]["titulo"] for t in hoy] == ["Formulario del IRS"]
    # Nadie le cambió el estado: sigue en `camino`, solo que su día llegó.
    assert hoy[0]["tarea"]["estado"] == "camino"


def test_vence_junta_tareas_y_entregas_por_fecha_y_solo_habla_de_tiempo(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/tarea", json={"titulo": "Formulario del IRS", "fecha_limite": _dia(servidor, 5)})
    cliente.post("/tarea", json={"titulo": "Pagar el dominio", "fecha_limite": _dia(servidor, 0)})
    cliente.post("/tarea", json={"titulo": "sin fecha"})

    import db

    en_tres_dias = datetime.now(timezone.utc) + timedelta(days=3)
    conexion = db.conectar()
    try:
        conexion.execute(
            "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) VALUES (?, ?, ?, ?, ?, ?, 1)",
            ("55555555-5555-5555-5555-555555555555", "Alfonso", "66666666-6666-6666-6666-666666666666",
             en_tres_dias.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(), 1000.0, "camino"),
        )
        conexion.execute(
            "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) VALUES (?, ?, ?, ?, ?, ?, 1)",
            ("77777777-7777-7777-7777-777777777777", "Beto", "66666666-6666-6666-6666-666666666666",
             en_tres_dias.isoformat(), 500.0, "pagada"),
        )
        conexion.commit()
    finally:
        conexion.close()

    vence = cliente.get("/hoy/agenda").json()["vence"]

    assert [v["titulo"] for v in vence] == ["Pagar el dominio", "Entrega Alfonso", "Formulario del IRS"]
    assert [v["vence_hoy"] for v in vence] == [True, False, False]
    assert [v["origen"] for v in vence] == ["tarea", "entrega", "tarea"]
    assert vence[1]["monto"] == 1000.0
    # Ley 3: ni contadores ni «días de atraso» en lo que sale de acá.
    assert set(vence[0]) == {"titulo", "fecha", "monto", "origen", "vence_hoy"}


def test_lo_hecho_ya_no_vence(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    tarea = cliente.post("/tarea", json={"titulo": "Pagar el dominio", "fecha_limite": _dia(servidor, 2)}).json()

    cliente.post(f"/tarea/{tarea['id']}/estado", json={"estado": "hecha"})

    assert cliente.get("/hoy/agenda").json() == {"manana": [], "vence": []}


def test_fijar_y_quitar_la_agenda_de_una_tarea_que_ya_existe(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    tarea = cliente.post("/tarea", json={"titulo": "Revisión y correo"}).json()

    con_hora = cliente.post(f"/tarea/{tarea['id']}/agenda", json={"hora": "08:00", "fecha_limite": _dia(servidor, 0)})
    assert con_hora.status_code == 200
    assert con_hora.json()["hora"] == "08:00" and con_hora.json()["fecha_limite"].startswith(_dia(servidor, 0))

    sin_nada = cliente.post(f"/tarea/{tarea['id']}/agenda", json={"hora": None, "fecha_limite": None}).json()
    assert sin_nada["hora"] is None and sin_nada["fecha_limite"] is None

    desconocida = cliente.post("/tarea/99999999-9999-9999-9999-999999999999/agenda", json={"hora": "08:00"})
    assert desconocida.status_code == 404


def test_abrir_un_bloque_por_mensaje_sigue_naciendo_sin_agenda(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "voy a revisar el contrato de Alfonso"}).json()

    assert respuesta["tipo"] == "hoy"
    assert respuesta["tarea"]["hora"] is None and respuesta["tarea"]["fecha_limite"] is None

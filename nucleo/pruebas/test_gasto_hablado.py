"""B6.1: el «listo cuando» del plan final — «gasté 40 en el servidor de
UpVisuals» deja gastado en 40 y por_hora recalculado."""
import importlib
import sys

from fastapi.testclient import TestClient

LIBRO_UPVISUALS = """---
titulo: UpVisuals
tema: upvisuals
resumen: Plataforma de Alfonso.
tipo: cliente
cliente: Alfonso
claves: [upvisuals, alfonso]
fases:
  - nombre: Fase 1
    alcance: a
    monto: 5000
    listo_cuando: Demo
    estado: pagando
---

Cuerpo.
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_UPVISUALS)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "modelos", "libros", "temas", "gastos", "ficha", "trabajo", "preguntas", "clasificar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_gasto_claro_deja_gastado_en_el_libro(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "gasté 40 en el servidor de upvisuals"})

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] == "gasto"
    libro = cliente.get("/libros/upvisuals").json()
    assert libro["gastado"] == 40.0
    assert len(libro["gastos"]) == 1
    assert libro["gastos"][0]["concepto"] == "servidor de upvisuals"
    assert libro["gastos"][0]["monto"] == 40.0
    assert libro["gastos"][0]["id"] is not None


def test_gasto_dudoso_deja_una_pregunta_no_adivina(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "gasté 15 en el almuerzo"})

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] != "gasto"
    libro = cliente.get("/libros/upvisuals").json()
    assert libro["gastado"] == 0.0


def test_gasto_comun_se_reparte_por_minutos_del_mes(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    import gastos as _gastos  # noqa: F401 — asegura el módulo cargado
    import trabajo

    # upvisuals trabajado este mes, para que le toque parte del común.
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    ahora = datetime.now(timezone.utc)
    tarea_id = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible) "
        "VALUES (?, 'x', NULL, 'hecha', 'paso', NULL, NULL, 0)",
        (tarea_id,),
    )
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, ?, 0, 'upvisuals')",
        (str(uuid4()), tarea_id, (ahora - timedelta(hours=1)).isoformat(), ahora.isoformat()),
    )
    conexion.commit()
    conexion.close()

    cliente = TestClient(servidor.app)
    respuesta = cliente.post("/mensaje", json={"texto": "la membresía de Claude: 100 al mes"})

    assert respuesta.json()["tipo"] == "gasto"
    libro = cliente.get("/libros/upvisuals").json()
    # Único proyecto con minutos este mes: se lleva el 100% del común.
    assert libro["gastado"] == 100.0


def test_responder_la_pregunta_de_gasto_dudoso_lo_anota(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "gasté 15 en el almuerzo"})
    pregunta = next(p for p in cliente.get("/preguntas", params={"tema": "_gastos"}).json())

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "es común"})

    assert respuesta.status_code == 200
    assert respuesta.json()["pregunta"]["estado"] == "respondida"
    import db

    conexion = db.conectar()
    from datetime import datetime, timedelta, timezone

    comunes = db.gastos_comunes_desde(conexion, datetime.now(timezone.utc) - timedelta(days=1))
    conexion.close()
    assert [c.concepto for c in comunes] == ["almuerzo"]
    assert comunes[0].monto == 15.0


def test_corregir_un_gasto_a_mano_queda(tmp_path, monkeypatch):
    """B6.5: «cada número se toca y se corrige» — el «listo cuando» del
    plan final."""
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "gasté 40 en el servidor de upvisuals"})
    libro = cliente.get("/libros/upvisuals").json()
    gasto_id = libro["gastos"][0]["id"]
    assert gasto_id is not None

    respuesta = cliente.patch(f"/gastos/{gasto_id}", json={"monto": 45.0})

    assert respuesta.status_code == 200
    assert respuesta.json()["monto"] == 45.0
    libro_de_nuevo = cliente.get("/libros/upvisuals").json()
    assert libro_de_nuevo["gastado"] == 45.0


def test_corregir_un_gasto_que_no_existe_es_404(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    respuesta = cliente.patch("/gastos/no-existe", json={"monto": 10.0})
    assert respuesta.status_code == 404


def test_corregir_un_gasto_con_monto_negativo_es_422(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "gasté 40 en el servidor de upvisuals"})
    libro = cliente.get("/libros/upvisuals").json()
    gasto_id = libro["gastos"][0]["id"]
    respuesta = cliente.patch(f"/gastos/{gasto_id}", json={"monto": -5.0})
    assert respuesta.status_code == 422


def test_un_cobro_no_se_confunde_con_un_gasto(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "Alfonso pagó 1500"})

    assert respuesta.json()["tipo"] == "cobro"
    libro = cliente.get("/libros/upvisuals").json()
    assert libro["gastado"] == 0.0

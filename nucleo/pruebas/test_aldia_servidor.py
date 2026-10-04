"""GET /hoy/aldia (B2.5): el endpoint real, contra un libro de fixture."""
import importlib
import json
import sys
from datetime import timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

LIBRO = """---
titulo: UpVisuals
tema: upvisuals
cliente: UpVisuals
tipo: cliente
resumen: El dashboard.
---

## Camino

- [x] Intake
- [ ] Descubrimiento (5 preguntas)
- [ ] Cobro y cierre
"""


def _libro(tmp_path, cuerpo: str = LIBRO) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(cuerpo)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("servidor", "aldia", "caminos", "libros", "db", "entregas", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_sin_nada_todo_viene_null_y_vacio(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.get("/hoy/aldia")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo == {"estamos_en": None, "lo_ultimo": None, "sigue": None, "mientras_no_estabas": []}


def test_con_un_commit_reciente_trae_el_libro_activo(tmp_path, monkeypatch):
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'commit', '', 'upvisuals', ?, ?)",
        (str(uuid4()), json.dumps({"mensaje": "algo"}), servidor.datetime.now(timezone.utc).isoformat()),
    )
    conexion.commit()
    conexion.close()

    cliente = TestClient(servidor.app)
    cuerpo = cliente.get("/hoy/aldia").json()

    assert cuerpo["estamos_en"]["tema"] == "upvisuals"
    assert cuerpo["estamos_en"]["paso"] == "Descubrimiento (5 preguntas)"
    assert cuerpo["lo_ultimo"]["evidencia"]["tipo"] == "commit"
    assert cuerpo["sigue"]["texto"] == "Descubrimiento (5 preguntas)"
    assert cuerpo["sigue"]["borrador"] is None  # este hito no avisa a un cliente


def test_hito_de_aviso_pide_el_borrador_una_vez_no_en_cada_get(tmp_path, monkeypatch):
    libro_en_cobro = LIBRO.replace(
        "- [x] Intake\n- [ ] Descubrimiento (5 preguntas)\n- [ ] Cobro y cierre",
        "- [x] Intake\n- [x] Descubrimiento (5 preguntas)\n- [ ] Cobro y cierre",
    )
    _libro(tmp_path, libro_en_cobro)
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'commit', '', 'upvisuals', ?, ?)",
        (str(uuid4()), json.dumps({"mensaje": "algo"}), servidor.datetime.now(timezone.utc).isoformat()),
    )
    conexion.commit()
    conexion.close()

    llamadas = []
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda *a, **k: (llamadas.append(1), servidor.pensar.Pensado(
            paso_minimo="Te mando la factura de esta fase.", tokens_entrada=0, tokens_salida=0,
            modelo="claude", entradas_en_indice=0, leyo_memoria=False, motor_usado="claude",
        ))[1],
    )
    cliente = TestClient(servidor.app)

    primero = cliente.get("/hoy/aldia").json()
    segundo = cliente.get("/hoy/aldia").json()

    assert primero["sigue"]["borrador"] == "Te mando la factura de esta fase."
    assert segundo["sigue"]["borrador"] == "Te mando la factura de esta fase."
    assert len(llamadas) == 1


def test_segunda_llamada_no_repite_mientras_no_estabas_de_lo_ya_visto(tmp_path, monkeypatch):
    """El primer GET marca «visto»; sin eventos nuevos, el segundo no trae
    nada en mientras_no_estabas (nada pasó desde el primero)."""
    _libro(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.get("/hoy/aldia")
    cuerpo = cliente.get("/hoy/aldia").json()

    assert cuerpo["mientras_no_estabas"] == []

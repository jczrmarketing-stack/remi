"""J2 · POST /bloque: el botón del panel que abre un bloque («Empezar con
eso», «Seguir con…»), y la fase actual de un libro."""
import importlib
import sys

from fastapi.testclient import TestClient

LIBRO = """---
titulo: UpVisuals — cliente Alfonso
tema: upvisuals
resumen: Plataforma de contenido.
tipo: cliente
fases:
  - nombre: Fase 1
    alcance: Distribución + seguridad
    monto: 5000
    listo_cuando: la demo corre
    estado: {estado_1}
  - nombre: Fase 2
    alcance: Generador de imágenes
    monto: 3700
    listo_cuando: genera
    estado: propuesta
---
- Cliente: Alfonso.

## Camino

- [x] Intake
- [ ] Pago antes de arrancar
"""


def _arrancar(tmp_path, monkeypatch, estado_1: str = "pagando"):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    (tmp_path / "libros").mkdir(exist_ok=True)
    (tmp_path / "libros" / "upvisuals.md").write_text(LIBRO.format(estado_1=estado_1))
    for nombre in ("servidor", "db", "modelos", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return TestClient(servidor.app)


def test_el_boton_abre_un_bloque_con_el_libro_como_contexto(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch)

    respuesta = cliente.post("/bloque", json={"titulo": "UpVisuals · Pago antes de arrancar", "tema": "upvisuals"})

    assert respuesta.status_code == 201
    bloque = respuesta.json()
    assert bloque["tarea"]["titulo"] == "UpVisuals · Pago antes de arrancar"
    assert bloque["tarea"]["estado"] == "hoy"
    assert bloque["sesion"]["fin"] is None
    assert bloque["sesion"]["app_contexto"] == "upvisuals"
    hoy = cliente.get("/hoy").json()
    assert [t["tarea"]["id"] for t in hoy] == [bloque["tarea"]["id"]]
    assert hoy[0]["sesiones"][0]["fin"] is None


def test_tocar_el_boton_dos_veces_no_duplica(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch)

    primero = cliente.post("/bloque", json={"titulo": "Pago", "tema": "upvisuals"}).json()
    segundo = cliente.post("/bloque", json={"titulo": "Pago", "tema": "upvisuals"})

    assert segundo.status_code == 201
    assert segundo.json()["sesion"]["id"] == primero["sesion"]["id"]
    assert len(cliente.get("/hoy").json()) == 1


def test_una_cosa_a_la_vez_con_otro_bloque_abierto_no_abre(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch)
    cliente.post("/bloque", json={"titulo": "Pago", "tema": "upvisuals"})

    otro = cliente.post("/bloque", json={"titulo": "Otra cosa"})

    assert otro.status_code == 409
    assert [t["tarea"]["titulo"] for t in cliente.get("/hoy").json()] == ["Pago"]


def test_volver_a_lo_mismo_abre_el_bloque_sobre_la_misma_tarea(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch)
    primero = cliente.post("/bloque", json={"titulo": "Pago", "tema": "upvisuals"}).json()
    cliente.post(f"/sesion/{primero['sesion']['id']}/cerrar")

    segundo = cliente.post("/bloque", json={"titulo": "Pago", "tema": "upvisuals"}).json()

    # Ley 1: la misma tarea junta todas las veces.
    assert segundo["tarea"]["id"] == primero["tarea"]["id"]
    assert segundo["sesion"]["id"] != primero["sesion"]["id"]
    historial = cliente.get(f"/tarea/{primero['tarea']['id']}/historial").json()
    assert len(historial["sesiones"]) == 1  # la cerrada; la nueva sigue abierta


def test_un_titulo_vacio_no_abre_nada(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch)

    assert cliente.post("/bloque", json={"titulo": "   "}).status_code == 422
    assert cliente.post("/bloque", json={"titulo": ""}).status_code == 422
    assert cliente.get("/hoy").json() == []


def test_la_fase_actual_es_la_primera_sin_entregar(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch, estado_1="pagando")
    assert cliente.get("/libros/upvisuals").json()["fase_actual_n"] == 1

    cliente = _arrancar(tmp_path, monkeypatch, estado_1="entregada")
    libro = cliente.get("/libros/upvisuals").json()
    assert libro["fase_actual_n"] == 2
    assert [f["nombre"] for f in libro["fases"]] == ["Fase 1", "Fase 2"]


def test_un_libro_sin_fases_no_tiene_fase_actual(tmp_path, monkeypatch):
    cliente = _arrancar(tmp_path, monkeypatch)
    (tmp_path / "libros" / "malik.md").write_text("---\ntitulo: Malik\ntema: malik\nresumen: Cuentas.\n---\n- x\n")

    assert cliente.get("/libros/malik").json()["fase_actual_n"] is None

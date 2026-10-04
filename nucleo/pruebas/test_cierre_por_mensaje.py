"""B3.1: «ya le mandé el avance a Alfonso» cierra el hito de avance de
UpVisuals y no el de BeaM — el «listo cuando» del plan final."""
import importlib
import sys

from fastapi.testclient import TestClient

LIBRO_UPVISUALS = """---
titulo: UpVisuals
tema: upvisuals
cliente: Alfonso
tipo: cliente
resumen: El dashboard.
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [x] Propuesta por fases
- [x] Contrato
- [x] Pago antes de arrancar
- [x] Entregas medidas
- [x] Cobro y cierre
- [x] Producción
- [ ] Entrega y capacitación
"""

LIBRO_BEAM = """---
titulo: BeaM
tema: beam
cliente: Milo
tipo: cliente
resumen: El bot.
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [x] Propuesta por fases
- [x] Contrato
- [x] Pago antes de arrancar
- [x] Entregas medidas
- [x] Cobro y cierre
- [x] Producción
- [ ] Entrega y capacitación
"""


def _libros(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_UPVISUALS)
    (carpeta / "beam.md").write_text(LIBRO_BEAM)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("servidor", "caminos", "libros", "db", "mensaje_cliente"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_ya_le_mande_el_avance_cierra_solo_upvisuals(tmp_path, monkeypatch):
    _libros(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    import caminos
    import db
    import libros

    cliente = TestClient(servidor.app)
    respuesta = cliente.post("/mensaje", json={"texto": "ya le mandé el avance a Alfonso"})

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] == "hito_cerrado"

    up = next(l for l in libros.listar() if l.tema == "upvisuals")
    beam = next(l for l in libros.listar() if l.tema == "beam")
    assert caminos.leer_hitos(up.archivo)[8].hecho is True
    assert caminos.leer_hitos(beam.archivo)[8].hecho is False

    conexion = db.conectar()
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 9)
    conexion.close()
    assert cerrado is not None and cerrado.tipo == "mensaje"


def test_sin_cliente_reconocido_sigue_su_camino_normal(tmp_path, monkeypatch):
    _libros(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "ya le avisé a alguien"})

    assert respuesta.json()["tipo"] != "hito_cerrado"

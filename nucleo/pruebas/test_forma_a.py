"""T2.1 · Forma A: `cliente` en el libro, `cobrado` por fase en cascada,
`detalle` por hito (la línea del SOP)."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import entregas
import servidor

CLIENTE_3_FASES = """---
titulo: UpVisuals
tema: upvisuals
resumen: Plataforma de Alfonso.
tipo: cliente
cliente: Alfonso
fases:
  - nombre: Fase 1
    alcance: Distribución
    monto: 5000
    listo_cuando: Demo aprobada
    estado: pagando
  - nombre: Fase 2
    alcance: Generador
    monto: 3700
    listo_cuando: Demo aprobada
    estado: propuesta
  - nombre: Fase 3
    alcance: Multi-cliente
    monto:
    listo_cuando:
    estado: sin alcance
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [x] Propuesta por fases
- [x] Contrato
- [ ] Pago antes de arrancar
- [ ] Entregas medidas
- [ ] Cobro y cierre
- [ ] Producción
- [ ] Entrega y capacitación
- [ ] Mensualidad
"""

SIN_TIPO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo.
"""


def _boveda(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(CLIENTE_3_FASES)
    (carpeta / "malik.md").write_text(SIN_TIPO)


def _cliente(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    return TestClient(servidor.app)


def _pagar(proyecto_id, monto) -> None:
    import db

    conexion = db.conectar()
    try:
        conexion.execute(
            "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
            "VALUES (?, 'Alfonso', ?, ?, ?, 'pagada', 1)",
            (str(uuid4()), str(proyecto_id), datetime.now(timezone.utc).isoformat(), monto),
        )
        conexion.commit()
    finally:
        conexion.close()


def test_cliente_del_libro_y_detalle_del_hito(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.get("/libros")
    por_tema = {l["tema"]: l for l in respuesta.json()}

    upvisuals = por_tema["upvisuals"]
    assert upvisuals["cliente"] == "Alfonso"
    assert por_tema["malik"]["cliente"] is None

    assert upvisuals["hito_actual"]["texto"] == "Pago antes de arrancar"
    assert upvisuals["hito_actual"]["detalle"] == (
        "En cuotas, con tolerancia de días. El trabajo empieza cuando el pago está completo."
    )
    assert upvisuals["hitos"][0]["detalle"].startswith("Qué pide")
    assert upvisuals["siguientes"][0]["detalle"]  # Entregas medidas, no vacío


def test_un_hito_fuera_del_sop_trae_detalle_vacio(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "x.md").write_text(
        "---\ntitulo: X\ntema: x\nresumen: r\ntipo: propio\n---\n\n## Camino\n\n- [ ] Un hito a mano\n"
    )
    cliente = _cliente(tmp_path, monkeypatch)
    libro = cliente.get("/libros").json()[0]
    assert libro["hito_actual"]["detalle"] == ""


def test_cobrado_llena_la_fase_1_y_lo_que_sobra_pasa_a_la_2(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    proyecto_id = entregas._proyecto_id_de_tema("upvisuals")
    _pagar(proyecto_id, 1500)
    _pagar(proyecto_id, 4000)  # total 5500: llena Fase 1 (5000), sobran 500 a la Fase 2

    upvisuals = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]

    assert [f["cobrado"] for f in upvisuals["fases"]] == [5000.0, 500.0, 0.0]


def test_fase_sin_monto_queda_en_cero(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    proyecto_id = entregas._proyecto_id_de_tema("upvisuals")
    _pagar(proyecto_id, 9999999)

    upvisuals = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert upvisuals["fases"][2]["cobrado"] == 0.0


def test_sin_pagos_el_cobrado_es_cero(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    upvisuals = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert [f["cobrado"] for f in upvisuals["fases"]] == [0.0, 0.0, 0.0]

"""GET /libros: la constelación de proyectos para el panel, un resumen por
libro — nunca el cuerpo completo. Contra una bóveda falsa, nunca remi-mente."""
from fastapi.testclient import TestClient

import servidor

CON_ESTADO_Y_CAMINO = """---
titulo: Upvisuals
tema: upvisuals
resumen: Distribución de contenido.
compartible: true
---

## Estado

Quedaste: armando el contrato.
Decisiones: ninguna nueva.
Próximo paso: mandar la propuesta.

## Camino

- [x] Contrato firmado
- [ ] Distribución
"""

SIN_ESTADO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo sin ## Estado ni ## Camino todavía.
"""


def _boveda(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(CON_ESTADO_Y_CAMINO)
    (carpeta / "malik.md").write_text(SIN_ESTADO)


def _cliente(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    return TestClient(servidor.app)


def test_libros_devuelve_los_dos_con_estado_y_camino(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.get("/libros")

    assert respuesta.status_code == 200
    por_tema = {l["tema"]: l for l in respuesta.json()}
    assert set(por_tema) == {"upvisuals", "malik"}

    upvisuals = por_tema["upvisuals"]
    assert upvisuals["titulo"] == "Upvisuals"
    assert upvisuals["resumen"] == "Distribución de contenido."
    assert upvisuals["compartible"] is True
    assert upvisuals["quedaste"] == "armando el contrato."
    assert upvisuals["proximo_paso"] == "mandar la propuesta."
    assert upvisuals["hitos"] == [
        {"texto": "Contrato firmado", "hecho": True},
        {"texto": "Distribución", "hecho": False},
    ]


def test_libro_sin_estado_ni_camino_viene_vacio_no_ausente(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.get("/libros")

    por_tema = {l["tema"]: l for l in respuesta.json()}
    malik = por_tema["malik"]
    assert malik["compartible"] is False
    assert malik["quedaste"] == ""
    assert malik["proximo_paso"] == ""
    assert malik["hitos"] == []
    # Nunca el cuerpo completo del libro.
    assert "Cuerpo sin ## Estado" not in respuesta.text


def test_libros_trae_la_entrega_cercana_y_el_mtime(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    import db
    import entregas
    from datetime import datetime, timezone
    from uuid import uuid4

    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
        "VALUES (?, ?, ?, ?, ?, 'camino', 1)",
        (
            str(uuid4()),
            "Alfonso",
            str(entregas._proyecto_id_de_tema("upvisuals")),
            datetime(2026, 10, 18, tzinfo=timezone.utc).isoformat(),
            5000,
        ),
    )
    conexion.commit()
    conexion.close()

    respuesta = cliente.get("/libros")
    por_tema = {l["tema"]: l for l in respuesta.json()}

    upvisuals = por_tema["upvisuals"]
    assert upvisuals["entrega_cercana"]["cliente"] == "Alfonso"
    assert upvisuals["entrega_cercana"]["monto"] == 5000
    assert upvisuals["ultimo_estado_en"]  # un ISO no vacío

    assert por_tema["malik"]["entrega_cercana"] is None


def test_libros_vacio_sin_bitacora(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "no-existe"))
    cliente = TestClient(servidor.app)
    respuesta = cliente.get("/libros")
    assert respuesta.status_code == 200
    assert respuesta.json() == []

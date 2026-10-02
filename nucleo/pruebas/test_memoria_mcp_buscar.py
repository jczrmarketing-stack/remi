"""T10.1b: buscar_memoria como herramienta MCP."""
import sys
from datetime import datetime, timezone
from uuid import uuid4


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("memoria_mcp", "db"):
        sys.modules.pop(nombre, None)
    import memoria_mcp

    return memoria_mcp


def test_encuentra_lo_que_el_indice_no_trae(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)
    import db
    from modelos import Memoria

    conexion = db.conectar()
    db.guardar_memoria(
        conexion,
        Memoria(
            id=uuid4(), titulo="El 401 de malik", resumen="token vencido", tema="malik",
            fecha=datetime.now(timezone.utc), cuerpo="x", fuente="manual", claves=None, nivel=None,
        ),
    )

    respuesta = mcp.buscar_memoria("401")

    assert "El 401 de malik" in respuesta


def test_sin_resultados_no_rompe(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)

    assert "No encontré nada" in mcp.buscar_memoria("algo que no existe")

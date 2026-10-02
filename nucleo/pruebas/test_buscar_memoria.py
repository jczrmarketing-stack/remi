"""T10.1a: lo que el presupuesto del índice deja afuera sigue en la base —
buscar_memoria lo encuentra por tema o por una palabra."""
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("db",):
        sys.modules.pop(nombre, None)
    import db

    return db


def _memoria(titulo, resumen, tema, cuerpo="x", fecha=None):
    from modelos import Memoria

    return Memoria(
        id=uuid4(),
        titulo=titulo,
        resumen=resumen,
        tema=tema,
        fecha=fecha or datetime.now(timezone.utc),
        cuerpo=cuerpo,
        fuente="manual",
        claves=None,
        nivel=None,
    )


def test_encuentra_por_una_palabra_del_titulo(tmp_path, monkeypatch):
    db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    db.guardar_memoria(conexion, _memoria("El 401 de malik", "se resolvió con el token", "malik"))
    db.guardar_memoria(conexion, _memoria("Otra cosa", "sin relación", "upvisuals"))

    resultados = db.buscar_memoria(conexion, "401")

    assert len(resultados) == 1
    assert resultados[0].titulo == "El 401 de malik"


def test_encuentra_por_tema_exacto(tmp_path, monkeypatch):
    db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    db.guardar_memoria(conexion, _memoria("A", "resumen a", "malik"))
    db.guardar_memoria(conexion, _memoria("B", "resumen b", "upvisuals"))

    resultados = db.buscar_memoria(conexion, "resumen", tema="malik")

    assert [r.titulo for r in resultados] == ["A"]


def test_no_encuentra_nada_no_rompe(tmp_path, monkeypatch):
    db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    db.guardar_memoria(conexion, _memoria("A", "resumen a", "malik"))

    assert db.buscar_memoria(conexion, "esto no existe") == []


def test_respeta_el_limite(tmp_path, monkeypatch):
    db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    for i in range(5):
        db.guardar_memoria(
            conexion,
            _memoria(f"Nota {i}", "palabra-clave", "malik", fecha=datetime.now(timezone.utc) - timedelta(minutes=i)),
        )

    resultados = db.buscar_memoria(conexion, "palabra-clave", k=3)

    assert len(resultados) == 3

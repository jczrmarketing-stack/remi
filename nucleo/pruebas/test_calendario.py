"""B10.1: Google Calendar — conversión evento↔Tarea. ESPERA PERMISO: el
OAuth real no se prueba acá (no hay credenciales); estas pruebas pasan
eventos ya traídos, como lo haría el cliente real una vez conectado."""
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

import calendario
import servidor
from calendario import EventoInvalido
from modelos import Tarea


def test_evento_con_hora_se_vuelve_tarea_con_hora():
    evento = {"summary": "Reunión con Alfonso", "start": {"dateTime": "2026-11-03T15:00:00-05:00"}}
    tarea = calendario.evento_a_tarea(evento)
    assert isinstance(tarea, Tarea)
    assert tarea.titulo == "Reunión con Alfonso"
    assert tarea.hora == "15:00"  # -05:00 ya es hora de Bogotá
    assert tarea.fecha_limite is not None


def test_evento_con_hora_en_otra_zona_se_convierte_a_bogota():
    evento = {"summary": "Llamada con un cliente de otro país", "start": {"dateTime": "2026-11-03T15:00:00+00:00"}}
    tarea = calendario.evento_a_tarea(evento)
    assert isinstance(tarea, Tarea)
    assert tarea.hora == "10:00"  # UTC 15:00 → Bogotá (UTC-5) 10:00


def test_evento_de_dia_completo_sin_hora():
    evento = {"summary": "Vence el dominio", "start": {"date": "2026-11-10"}}
    tarea = calendario.evento_a_tarea(evento)
    assert isinstance(tarea, Tarea)
    assert tarea.hora is None
    assert tarea.fecha_limite == datetime.combine(date(2026, 11, 10), datetime.min.time(), tzinfo=timezone.utc)


def test_evento_sin_titulo_es_invalido():
    assert isinstance(calendario.evento_a_tarea({"start": {"date": "2026-11-10"}}), EventoInvalido)


def test_evento_sin_fecha_es_invalido():
    assert isinstance(calendario.evento_a_tarea({"summary": "x"}), EventoInvalido)


def test_tarea_no_compartible_no_sale_como_evento():
    tarea = Tarea(
        id="11111111-1111-1111-1111-111111111111", titulo="algo privado", proyecto_id=None, estado="hoy",
        paso_minimo="x", estimado_min=None, real_min=None, hora=None,
        fecha_limite=datetime(2026, 11, 10, tzinfo=timezone.utc), tipo=None, compartible=False,
    )
    assert calendario.tarea_a_evento(tarea) is None


def test_tarea_compartible_con_hora_sale_como_evento():
    tarea = Tarea(
        id="11111111-1111-1111-1111-111111111111", titulo="entrega a Beam", proyecto_id=None, estado="hoy",
        paso_minimo="x", estimado_min=None, real_min=None, hora="14:30",
        fecha_limite=datetime(2026, 11, 10, tzinfo=timezone.utc), tipo=None, compartible=True,
    )
    evento = calendario.tarea_a_evento(tarea)
    assert evento is not None
    assert evento["summary"] == "entrega a Beam"
    assert "14:30" in evento["start"]["dateTime"]  # type: ignore[index]


def test_importar_citas_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    r = cliente.post(
        "/calendario/importar",
        json={"eventos": [{"summary": "cita 1", "start": {"date": "2026-12-01"}}, {"summary": "sin fecha"}]},
    )
    assert r.status_code == 201
    assert r.json()["creadas"] == 1  # la segunda es inválida, no se cuenta


def test_estado_conexion_siempre_falso_sin_oauth(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    assert cliente.get("/calendario/estado").json() == {"conectado": False}

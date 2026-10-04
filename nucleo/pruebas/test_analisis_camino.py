"""R3 (forma Q): el análisis de un camino. `investigador` y `confirmador`
son dobles aquí — nunca una llamada real de pago en pytest (regla del
mega prompt)."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import analisis_camino
import db
import servidor
from analisis_camino import FuenteCruda, ResultadoInvestigacion


def _investigador_feliz(idea_texto: str) -> ResultadoInvestigacion:
    return ResultadoInvestigacion(
        mercado="Mercado de 10 mil usuarios [f1]", competidores="Dos competidores grandes",
        juego="Juego de suma positiva", a_favor="Hay demanda probada", en_contra="Margen bajo",
        dominio="aprendiz", base_texto="10 mil usuarios activos [f1]", palancas="precio, distribución",
        objeciones="muy competido", prueba="una landing con 10 registros",
        fuentes=[FuenteCruda(url="https://ejemplo.com/reporte", fecha=datetime.now(timezone.utc), fragmento="10.000 usuarios activos este año")],
    )


def _investigador_sin_fragmento(idea_texto: str) -> ResultadoInvestigacion:
    return ResultadoInvestigacion(
        mercado="Mercado grande", competidores=None, juego=None, a_favor=None, en_contra=None, dominio=None,
        base_texto="una cifra sin respaldo", palancas=None, objeciones=None, prueba=None,
        fuentes=[FuenteCruda(url="https://ejemplo.com/sin-fragmento", fecha=datetime.now(timezone.utc), fragmento="")],
    )


def _confirmador_siempre_si(fragmento: str, lo_citado: str) -> bool:
    return True


def _confirmador_siempre_no(fragmento: str, lo_citado: str) -> bool:
    return False


def test_fuente_sin_fragmento_queda_supuesto(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        analisis = db.crear_analisis(conexion, str(uuid4()), datetime.now(timezone.utc))
        resultado = analisis_camino.ejecutar_investigacion(
            conexion, str(analisis.id), "una idea", _investigador_sin_fragmento, _confirmador_siempre_si
        )
        assert resultado.estado == "listo"
        fuentes = db.fuentes_de_analisis(conexion, str(analisis.id))
        assert len(fuentes) == 1
        assert fuentes[0].verificada is False  # sin fragmento: nunca se verifica
    finally:
        conexion.close()


def test_fuente_con_fragmento_y_confirmador_que_dice_si_queda_verificada(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        analisis = db.crear_analisis(conexion, str(uuid4()), datetime.now(timezone.utc))
        resultado = analisis_camino.ejecutar_investigacion(
            conexion, str(analisis.id), "otra idea", _investigador_feliz, _confirmador_siempre_si
        )
        assert resultado.estado == "listo"
        assert resultado.mercado is not None and "[f1]" in resultado.mercado
        fuentes = db.fuentes_de_analisis(conexion, str(analisis.id))
        assert fuentes[0].verificada is True
    finally:
        conexion.close()


def test_confirmador_que_dice_no_deja_la_fuente_sin_verificar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    conexion = db.conectar()
    try:
        analisis = db.crear_analisis(conexion, str(uuid4()), datetime.now(timezone.utc))
        analisis_camino.ejecutar_investigacion(conexion, str(analisis.id), "idea", _investigador_feliz, _confirmador_siempre_no)
        fuentes = db.fuentes_de_analisis(conexion, str(analisis.id))
        assert fuentes[0].verificada is False
    finally:
        conexion.close()


def test_investigador_que_falla_deja_el_analisis_en_fallo(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))

    def _investigador_roto(idea_texto: str) -> ResultadoInvestigacion:
        raise RuntimeError("la búsqueda se cayó")

    conexion = db.conectar()
    try:
        analisis = db.crear_analisis(conexion, str(uuid4()), datetime.now(timezone.utc))
        resultado = analisis_camino.ejecutar_investigacion(conexion, str(analisis.id), "idea", _investigador_roto, _confirmador_siempre_si)
        assert resultado.estado == "fallo"
    finally:
        conexion.close()


def test_post_y_get_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    cliente = TestClient(servidor.app)
    r = cliente.post("/rumbo/caminos", json={"idea_id": str(uuid4())})
    assert r.status_code == 202
    analisis_id = r.json()["id"]

    vista = cliente.get(f"/rumbo/caminos/{analisis_id}").json()
    assert vista["estado"] == "investigando"
    assert vista["fuentes"] == []

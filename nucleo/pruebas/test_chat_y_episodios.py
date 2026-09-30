"""3c: el chat de la ventanita, la lista de Ollama y las charlas pegadas."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import db
import episodios
import pensar
import servidor

CHARLA = "Juan: hablemos de UpVisuals y la fase dos.\nRemi: dale.\n" * 60


def test_una_charla_queda_en_la_boveda_y_en_memoria(tmp_path):
    resumidor = lambda _t: ({"titulo": "Fase 2 de UpVisuals", "tema": "UpVisuals", "resumen": "Alcance y fecha."}, "ollama/gemma3:4b")
    ahora = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    episodio = episodios.guardar(CHARLA, ahora, resumidor)

    assert episodio.ruta.name == "2026-10-01-fase-2-de-upvisuals.md"
    nota = episodio.ruta.read_text()
    assert nota.startswith('---\ntitulo: "Fase 2 de UpVisuals"\ntema: upvisuals\nresumen: "Alcance y fecha."\n---\n')
    assert "hablemos de UpVisuals" in nota

    conexion = db.conectar()
    try:
        [memoria] = db.memorias_por_tema(conexion, "upvisuals")
    finally:
        conexion.close()
    assert memoria.titulo == "Fase 2 de UpVisuals" and memoria.fuente == "ollama" and memoria.nivel == 2


def test_dos_charlas_con_el_mismo_titulo_no_se_pisan():
    resumidor = lambda _t: ({"titulo": "Lo mismo", "tema": "remi", "resumen": "x"}, "haiku")
    ahora = datetime(2026, 10, 1, tzinfo=timezone.utc)
    a = episodios.guardar(CHARLA, ahora, resumidor)
    b = episodios.guardar(CHARLA, ahora, resumidor)
    assert a.ruta != b.ruta and b.ruta.name.endswith("-2.md")


def test_sin_resumen_igual_se_guarda():
    episodio = episodios.guardar(CHARLA, datetime(2026, 10, 1, tzinfo=timezone.utc), lambda _t: (None, "haiku"))
    assert episodio.ruta.exists() and episodio.titulo.startswith("Juan: hablemos")


def test_una_charla_corta_no_se_acepta():
    cliente = TestClient(servidor.app)
    assert cliente.post("/episodio", json={"texto": "hola"}).status_code == 422


def test_el_chat_trae_la_conversacion_vigente():
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        db.guardar_turno(conexion, "juan", "hola", ahora)
        db.guardar_turno(conexion, "remi", "Hola. ¿Qué hacemos?", ahora)
    finally:
        conexion.close()
    turnos = TestClient(servidor.app).get("/conversacion").json()
    assert [(t["rol"], t["texto"]) for t in turnos] == [("juan", "hola"), ("remi", "Hola. ¿Qué hacemos?")]


def test_sin_conversacion_el_chat_esta_vacio():
    assert TestClient(servidor.app).get("/conversacion").json() == []


def test_ollama_apagado_da_lista_vacia(monkeypatch):
    def caido(*_a, **_k):
        raise pensar.httpx.ConnectError("no")

    monkeypatch.setattr(pensar.httpx, "get", caido)
    assert pensar.modelos_de_ollama() == []


def test_el_resumen_largo_se_corta_en_una_palabra():
    largo = "palabra " * 60
    episodio = episodios.guardar(CHARLA, datetime(2026, 10, 1, tzinfo=timezone.utc), lambda _t: ({"titulo": "t", "tema": "remi", "resumen": largo}, "haiku"))
    assert len(episodio.resumen) <= 240 and episodio.resumen.endswith("palabra…")

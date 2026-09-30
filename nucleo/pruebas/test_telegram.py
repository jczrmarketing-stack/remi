"""Telegram (Biblia Parte IV): el teléfono. Todo con transporte falso —
ninguna prueba toca la red ni el TELEGRAM_TOKEN real."""
from __future__ import annotations

import re
from datetime import datetime

from fastapi.testclient import TestClient

import db
import servidor
import telegram


class _TransporteFalso:
    def __init__(self) -> None:
        self.enviados: list[tuple[int | str, str]] = []

    def obtener_actualizaciones(self, offset):
        return []

    def enviar_mensaje(self, chat_id, texto):
        self.enviados.append((chat_id, texto))


def _actualizacion(chat_id: int, texto: str) -> dict:
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": texto}}


# — 1. sin token no arranca —


def test_sin_token_no_arranca(monkeypatch, capsys):
    monkeypatch.setattr(telegram, "token", lambda: None)
    llamado = {"n": 0}
    monkeypatch.setattr(
        telegram.threading, "Thread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía arrancar un hilo"))
    )
    telegram.arrancar_hilo()
    assert "TELEGRAM_TOKEN" in capsys.readouterr().err


def test_arranca_hilo_cuando_hay_token(monkeypatch):
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: "transporte-falso")
    arrancado = {}

    class HiloFalso:
        def __init__(self, target, args, daemon):
            arrancado["target"] = target
            arrancado["args"] = args
            arrancado["daemon"] = daemon

        def start(self):
            arrancado["iniciado"] = True

    monkeypatch.setattr(telegram.threading, "Thread", HiloFalso)
    telegram.arrancar_hilo()
    assert arrancado["args"] == ("transporte-falso",)
    assert arrancado["daemon"] is True
    assert arrancado["iniciado"] is True


def test_remi_telegram_0_apaga_el_hilo_aunque_haya_token(monkeypatch):
    monkeypatch.setenv("REMI_TELEGRAM", "0")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(
        telegram.threading, "Thread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía arrancar"))
    )
    telegram.arrancar_hilo()  # no revienta: no llegó a crear el hilo


# — 1. chat ajeno ignorado —


def test_chat_ajeno_se_ignora_en_silencio(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()
    telegram._manejar_actualizacion(transporte, _actualizacion(999, "hola"))
    assert transporte.enviados == []


# — 1. /start sin CHAT_ID solo loguea —


def test_start_sin_chat_id_solo_loguea(monkeypatch, capsys):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: None)
    transporte = _TransporteFalso()
    telegram._manejar_actualizacion(transporte, _actualizacion(555, "/start"))
    assert transporte.enviados == []
    assert "555" in capsys.readouterr().err


def test_start_con_chat_id_ya_configurado_no_loguea_de_nuevo(monkeypatch, capsys):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "555")
    transporte = _TransporteFalso()
    telegram._manejar_actualizacion(transporte, _actualizacion(555, "/start"))
    assert transporte.enviados == []
    assert capsys.readouterr().err == ""


def test_texto_sin_chat_id_configurado_no_contesta_a_nadie(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: None)
    transporte = _TransporteFalso()
    telegram._manejar_actualizacion(transporte, _actualizacion(555, "idea: lo que sea"))
    assert transporte.enviados == []


# — 2. charla corta: pasa por /mensaje, una idea entra a la Bandeja, ≤3 frases —


def test_idea_por_texto_entra_a_la_bandeja_y_responde_corto(monkeypatch):
    monkeypatch.setattr(servidor.pensar, "pensar", lambda *a, **k: None)
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()

    telegram._manejar_actualizacion(transporte, _actualizacion(123, "idea: app de recetas"))

    assert len(transporte.enviados) == 1
    chat_id, texto = transporte.enviados[0]
    assert chat_id == 123
    frases = [f for f in re.split(r"(?<=[.!?…])\s+", texto.strip()) if f]
    assert len(frases) <= 3

    conexion = db.conectar()
    try:
        fila = conexion.execute("SELECT COUNT(*) c FROM ideas").fetchone()
        assert fila["c"] == 1
        idea = conexion.execute("SELECT texto, origen FROM ideas").fetchone()
        assert idea["texto"] == "idea: app de recetas"
        assert idea["origen"] == "texto"
    finally:
        conexion.close()


# — 3. entrega por texto: misma vía que POST /entregas —


def test_entrega_por_texto_crea_entrega_y_confirma(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()

    texto = "entrega para Alfonso el 18 de octubre por 5.000"
    telegram._manejar_actualizacion(transporte, _actualizacion(123, texto))

    assert len(transporte.enviados) == 1
    _, respuesta = transporte.enviados[0]
    assert respuesta == "Entrega para Alfonso: 18 de octubre, $5.000"

    listadas = TestClient(servidor.app).get("/entregas").json()
    assert len(listadas) == 1
    assert listadas[0]["cliente"] == "Alfonso"
    assert listadas[0]["monto"] == 5000.0


def test_texto_sin_forma_de_entrega_no_crea_nada(monkeypatch):
    monkeypatch.setattr(servidor.pensar, "pensar", lambda *a, **k: None)
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()

    telegram._manejar_actualizacion(transporte, _actualizacion(123, "entrega a medias, sin fecha ni monto"))

    listadas = TestClient(servidor.app).get("/entregas").json()
    assert listadas == []


# — 4. avisos salientes: /telegram/avisar, respeta el silencio —


def test_avisar_manda_fuera_del_silencio(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "en_silencio", lambda *_a, **_k: False)
    transporte = _TransporteFalso()
    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: transporte)

    respuesta = TestClient(servidor.app).post("/telegram/avisar", json={"texto": "prueba"})

    assert respuesta.status_code == 204
    assert transporte.enviados == [("123", "prueba")]


def test_avisar_respeta_el_silencio_salvo_urgente(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "en_silencio", lambda *_a, **_k: True)
    transporte = _TransporteFalso()
    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: transporte)
    cliente = TestClient(servidor.app)

    cliente.post("/telegram/avisar", json={"texto": "no debería salir de noche"})
    assert transporte.enviados == []

    cliente.post("/telegram/avisar", json={"texto": "urgente de verdad", "urgente": True})
    assert transporte.enviados == [("123", "urgente de verdad")]


def test_en_silencio_23_a_7_en_bogota():
    assert telegram.en_silencio(datetime(2026, 1, 1, 23, 30, tzinfo=telegram.BOGOTA))
    assert telegram.en_silencio(datetime(2026, 1, 1, 6, 0, tzinfo=telegram.BOGOTA))
    assert not telegram.en_silencio(datetime(2026, 1, 1, 7, 0, tzinfo=telegram.BOGOTA))
    assert not telegram.en_silencio(datetime(2026, 1, 1, 12, 0, tzinfo=telegram.BOGOTA))


# — el loop de polling avanza el offset y no revienta con un error de red —


def test_escuchar_avanza_el_offset_con_cada_tanda(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: None)  # nada que contestar: solo probamos el offset
    pedidos = []

    class TransporteDeDosTandas:
        def __init__(self):
            self._veces = 0

        def obtener_actualizaciones(self, offset):
            pedidos.append(offset)
            self._veces += 1
            if self._veces == 1:
                return [{"update_id": 10, "message": {"chat": {"id": 1}, "text": "hola"}}]
            return []

        def enviar_mensaje(self, chat_id, texto):
            raise AssertionError("no debía contestar")

    contador = {"n": 0}

    def seguir():
        contador["n"] += 1
        return contador["n"] <= 2

    telegram.escuchar(TransporteDeDosTandas(), seguir)
    assert pedidos == [None, 11]


# — reporte de la noche: mensaje que manda noche.py por /telegram/avisar —


def test_reporte_noche_sin_cambios():
    assert telegram.mensaje_reporte_noche([]) == "Anoche no toqué nada"


def test_reporte_noche_con_un_libro():
    texto = telegram.mensaje_reporte_noche([("Malik", "-Quedaste: nada.\n+Quedaste: se arregló el webhook.")])
    assert texto.startswith("Anoche cambié 1 libro\n\n")
    assert "Malik:" in texto
    assert "se arregló el webhook" in texto
    assert "más" not in texto


def test_reporte_noche_con_varios_libros_dice_libros_en_plural():
    texto = telegram.mensaje_reporte_noche([("Malik", "diff a"), ("Organic", "diff b")])
    assert texto.startswith("Anoche cambié 2 libros\n\n")


def test_reporte_noche_muestra_maximo_3_y_avisa_los_que_sobran():
    cambios = [(f"Libro {i}", f"diff {i}") for i in range(5)]
    texto = telegram.mensaje_reporte_noche(cambios)
    assert texto.startswith("Anoche cambié 5 libros")
    for i in range(3):
        assert f"Libro {i}:" in texto
    for i in (3, 4):
        assert f"Libro {i}:" not in texto
    assert texto.endswith("y 2 más")


def test_escuchar_no_se_cae_si_obtener_actualizaciones_falla(monkeypatch):
    monkeypatch.setattr(telegram.time, "sleep", lambda _s: None)
    intentos = {"n": 0}

    class TransporteRoto:
        def obtener_actualizaciones(self, offset):
            intentos["n"] += 1
            raise RuntimeError("sin red")

    contador = {"n": 0}

    def seguir():
        contador["n"] += 1
        return contador["n"] <= 2

    telegram.escuchar(TransporteRoto(), seguir)
    assert intentos["n"] == 2

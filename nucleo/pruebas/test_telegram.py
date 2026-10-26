"""Telegram (Biblia Parte IV): el teléfono. Todo con transporte falso —
ninguna prueba toca la red ni el TELEGRAM_TOKEN real."""
from __future__ import annotations

import importlib
import re
import time
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


class _HiloInmediato:
    """Reemplaza a threading.Thread en las pruebas de avisar() que no son
    sobre tiempos: corre el target ahí mismo, en el hilo de la prueba, para
    que el resultado del envío de fondo quede listo antes del assert."""

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)


def _actualizacion(chat_id: int, texto: str) -> dict:
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": texto}}


# — 1. sin token no arranca —


def test_sin_token_no_arranca(monkeypatch, capsys):
    # Prueban el arranque mismo, con hilo y cliente falsos: sin el REMI_TELEGRAM=0 de conftest.
    monkeypatch.delenv("REMI_TELEGRAM", raising=False)
    monkeypatch.setattr(telegram, "token", lambda: None)
    llamado = {"n": 0}
    monkeypatch.setattr(
        telegram.threading, "Thread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía arrancar un hilo"))
    )
    telegram.arrancar_hilo()
    assert "TELEGRAM_TOKEN" in capsys.readouterr().err


def test_arranca_hilo_cuando_hay_token(monkeypatch):
    # Prueban el arranque mismo, con hilo y cliente falsos: sin el REMI_TELEGRAM=0 de conftest.
    monkeypatch.delenv("REMI_TELEGRAM", raising=False)
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
    transporte, seguir = arrancado["args"]
    assert transporte == "transporte-falso"
    assert callable(seguir)
    assert arrancado["daemon"] is True
    assert arrancado["iniciado"] is True


def test_remi_telegram_0_apaga_el_hilo_aunque_haya_token(monkeypatch):
    monkeypatch.setenv("REMI_TELEGRAM", "0")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(
        telegram.threading, "Thread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía arrancar"))
    )
    telegram.arrancar_hilo()  # no revienta: no llegó a crear el hilo


# — reiniciar_hilo: el gancho que llama conexiones.guardar() —


def test_reiniciar_hilo_para_el_evento_viejo_y_arranca_uno_nuevo(monkeypatch):
    # Prueban el arranque mismo, con hilo y cliente falsos: sin el REMI_TELEGRAM=0 de conftest.
    monkeypatch.delenv("REMI_TELEGRAM", raising=False)
    monkeypatch.setattr(telegram, "token", lambda: "token-nuevo")
    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: "transporte-falso")

    class HiloFalso:
        def __init__(self, target, args, daemon):
            self.args = args

        def start(self):
            pass

    monkeypatch.setattr(telegram.threading, "Thread", HiloFalso)

    evento_viejo = telegram.threading.Event()
    monkeypatch.setattr(telegram, "_evento_detener", evento_viejo)
    assert not evento_viejo.is_set()

    telegram.reiniciar_hilo()

    assert evento_viejo.is_set()  # el polling de antes ya sabe que debe parar
    assert telegram._evento_detener is not evento_viejo  # y hay uno nuevo para el hilo nuevo


def test_reiniciar_hilo_sin_token_apaga_y_lo_dice(monkeypatch, capsys):
    # Prueban el arranque mismo, con hilo y cliente falsos: sin el REMI_TELEGRAM=0 de conftest.
    monkeypatch.delenv("REMI_TELEGRAM", raising=False)
    monkeypatch.setattr(telegram, "token", lambda: None)
    monkeypatch.setattr(
        telegram.threading, "Thread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía arrancar"))
    )
    telegram.reiniciar_hilo()
    assert "TELEGRAM_TOKEN" in capsys.readouterr().err


def test_reiniciar_hilo_respeta_remi_telegram_0(monkeypatch):
    monkeypatch.setenv("REMI_TELEGRAM", "0")
    monkeypatch.setattr(
        telegram.threading, "Thread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía arrancar"))
    )
    telegram.reiniciar_hilo()  # no revienta: no llegó a tocar nada


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


# — 3. entrega por texto: lleva monto, así que va al Mac (26-oct-2026) —


def test_entrega_por_texto_no_se_crea_y_va_al_mac(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()

    telegram._manejar_actualizacion(transporte, _actualizacion(123, "entrega para Alfonso el 18 de octubre por 5.000"))

    assert transporte.enviados == [(123, "Eso lo vemos en el Mac.")]
    assert TestClient(servidor.app).get("/entregas").json() == []


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
    monkeypatch.setattr(telegram.threading, "Thread", _HiloInmediato)
    transporte = _TransporteFalso()
    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: transporte)

    respuesta = TestClient(servidor.app).post("/telegram/avisar", json={"texto": "prueba"})

    assert respuesta.status_code == 204
    assert transporte.enviados == [("123", "prueba")]


def test_avisar_respeta_el_silencio_salvo_urgente(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "en_silencio", lambda *_a, **_k: True)
    monkeypatch.setattr(telegram.threading, "Thread", _HiloInmediato)
    transporte = _TransporteFalso()
    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: transporte)
    cliente = TestClient(servidor.app)

    cliente.post("/telegram/avisar", json={"texto": "no debería salir de noche"})
    assert transporte.enviados == []

    cliente.post("/telegram/avisar", json={"texto": "urgente de verdad", "urgente": True})
    assert transporte.enviados == [("123", "urgente de verdad")]


# — avisar() no bloquea: el envío real corre en un hilo de fondo —


def test_avisar_no_bloquea_aunque_el_transporte_tarde(monkeypatch):
    """avisar() debe volver en menos de 100ms aunque el transporte (falso)
    tarde 3 segundos en responder — medimos el tiempo de la llamada a
    avisar(), nunca el del hilo de fondo."""
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "en_silencio", lambda *_a, **_k: False)

    class _TransporteLento:
        def enviar_mensaje(self, chat_id, texto):
            time.sleep(3)

    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: _TransporteLento())

    inicio = time.perf_counter()
    respuesta = TestClient(servidor.app).post(
        "/telegram/avisar", json={"texto": "prueba lenta", "urgente": True}
    )
    duracion_ms = (time.perf_counter() - inicio) * 1000

    assert respuesta.status_code == 204
    assert duracion_ms < 100


def test_avisar_reintenta_una_vez_si_falla(monkeypatch):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "en_silencio", lambda *_a, **_k: False)
    monkeypatch.setattr(telegram.time, "sleep", lambda _s: None)
    monkeypatch.setattr(telegram.threading, "Thread", _HiloInmediato)

    llamadas = {"n": 0}

    class _TransporteFallaUnaVez:
        def enviar_mensaje(self, chat_id, texto):
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                raise RuntimeError("timeout simulado")

    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: _TransporteFallaUnaVez())

    respuesta = TestClient(servidor.app).post("/telegram/avisar", json={"texto": "prueba"})

    assert respuesta.status_code == 204
    assert llamadas["n"] == 2


def test_avisar_con_transporte_siempre_roto_nunca_lanza(monkeypatch, capsys):
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "en_silencio", lambda *_a, **_k: False)
    monkeypatch.setattr(telegram.time, "sleep", lambda _s: None)
    monkeypatch.setattr(telegram.threading, "Thread", _HiloInmediato)

    class _TransporteRoto:
        def enviar_mensaje(self, chat_id, texto):
            raise RuntimeError("siempre falla")

    monkeypatch.setattr(telegram, "ClienteBotAPI", lambda tok: _TransporteRoto())

    respuesta = TestClient(servidor.app).post("/telegram/avisar", json={"texto": "prueba"})

    assert respuesta.status_code == 204
    assert "falló avisar" in capsys.readouterr().err


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


def test_reporte_noche_con_un_libro_solo_dice_el_titulo():
    texto = telegram.mensaje_reporte_noche([("Malik", "-Quedaste: nada.\n+Quedaste: se arregló el webhook.")])
    assert texto == "Anoche cambié 1 libro: Malik."


def test_reporte_noche_con_varios_libros_dice_libros_en_plural():
    texto = telegram.mensaje_reporte_noche([("Malik", "diff a"), ("Organic", "diff b")])
    assert texto == "Anoche cambié 2 libros: Malik, Organic."


def test_reporte_noche_muestra_maximo_3_y_avisa_los_que_sobran():
    cambios = [(f"Libro {i}", f"diff {i}") for i in range(5)]
    texto = telegram.mensaje_reporte_noche(cambios)
    assert texto == "Anoche cambié 5 libros: Libro 0, Libro 1, Libro 2 y 2 más."


def test_reporte_noche_no_nombra_los_libros_privados():
    texto = telegram.mensaje_reporte_noche([("Malik", "d"), (None, "monto: 500")])
    assert texto == "Anoche cambié 2 libros: Malik. Lo demás lo vemos en el Mac."
    assert telegram.mensaje_reporte_noche([(None, "x")]) == "Anoche cambié 1 libro. Lo vemos en el Mac."


# — 6. lo que cabe en el teléfono (26-oct-2026) —


def test_tema_privado_que_entra_va_al_mac_sin_tocar_nada(monkeypatch):
    llamados = []
    monkeypatch.setattr(importlib.import_module("servidor"), "recibir_mensaje", lambda m: llamados.append(m))
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()
    for texto in ("¿cuánta plata me deben?", "me toca la pastilla", "lo del paciente de ayer", "cobré $300"):
        telegram._manejar_actualizacion(transporte, _actualizacion(123, texto))
    assert [t for _, t in transporte.enviados] == ["Eso lo vemos en el Mac."] * 4
    assert llamados == []


def test_el_telefono_no_piensa(monkeypatch):
    vistos = []

    def recibir(mensaje):
        vistos.append(mensaje)
        return importlib.import_module("servidor").RespuestaMensaje(tipo="idea", texto="A la Bandeja.", voz="A la Bandeja.")

    # El servidor vigente (otras pruebas lo recargan): el que importa telegram.
    vigente = importlib.import_module("servidor")
    monkeypatch.setattr(vigente, "recibir_mensaje", recibir)
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    transporte = _TransporteFalso()
    telegram._manejar_actualizacion(transporte, _actualizacion(123, "idea: app de recetas"))
    assert vistos[0].think is False
    assert transporte.enviados == [(123, "A la Bandeja.")]


def test_respuesta_larga_o_privada_no_sale():
    assert telegram.para_el_telefono("x" * 300) == "Eso lo vemos en el Mac."
    assert telegram.para_el_telefono("Te deben 2 millones") == "Eso lo vemos en el Mac."
    assert telegram.para_el_telefono("Listo. Cerrado.") == "Listo. Cerrado."


def test_avisar_privado_solo_dice_que_hay_algo(monkeypatch):
    enviados = []

    class Falso:
        def __init__(self, tok):
            pass

        def enviar_mensaje(self, chat_id, texto):
            enviados.append(texto)

    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "123")
    monkeypatch.setattr(telegram, "token", lambda: "un-token")
    monkeypatch.setattr(telegram, "ClienteBotAPI", Falso)
    monkeypatch.setattr(telegram, "en_silencio", lambda ahora=None: False)
    monkeypatch.setattr(telegram.threading, "Thread", lambda target, args, daemon: type("H", (), {"start": lambda self: target(*args)})())
    telegram.avisar(telegram.AvisoSaliente(texto="Entra el pago de Alfonso"))
    assert enviados == ["Hay algo nuevo. Lo vemos en el Mac."]


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

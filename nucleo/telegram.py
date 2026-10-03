"""Telegram (Biblia Parte IV): el teléfono — avisos y charla corta.

Cliente mínimo sobre la Bot API con httpx, sin librerías de Telegram.
Long polling (getUpdates, timeout 30) en un hilo daemon que arranca el
startup de servidor.py. Solo Juan Camilo le habla a Remi: cualquier otro
chat_id se ignora en silencio, y sin TELEGRAM_CHAT_ID el primer /start solo
queda en el log (no contesta a nadie hasta que se configure).

Los imports de `servidor` y `entregas` van adentro de las funciones, nunca
arriba: servidor.py importa este módulo para arrancar el hilo, y un import
arriba crearía un ciclo.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

RUTA_ENV = Path(__file__).resolve().parent / ".env"
BOGOTA = ZoneInfo("America/Bogota")

TIMEOUT_POLLING_SEGUNDOS = 30
TIMEOUT_ENVIO_SEGUNDOS = 8
REINTENTO_AVISO_SEGUNDOS = 2
HORA_SILENCIO_DESDE = 23
HORA_SILENCIO_HASTA = 7

_MESES_NOMBRE = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _leer_env(ruta: Path | None = None) -> dict[str, str]:
    """KEY=VALOR por línea, igual que pensar._leer_env — la ruta se resuelve
    al llamar, no al definir, para que las pruebas no lean el .env real."""
    ruta = RUTA_ENV if ruta is None else ruta
    valores: dict[str, str] = {}
    if not ruta.exists():
        return valores
    for linea in ruta.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip("\"'")
    return valores


def _ajuste(clave: str) -> str | None:
    """La variable de entorno gana sobre nucleo/.env; ninguna se imprime."""
    return os.environ.get(clave) or _leer_env().get(clave) or None


def token() -> str | None:
    return _ajuste("TELEGRAM_TOKEN")


def chat_id_configurado() -> str | None:
    return _ajuste("TELEGRAM_CHAT_ID")


class Transporte(Protocol):
    """Lo que hace falta de la Bot API. Las pruebas usan un transporte falso
    para correr sin red."""

    def obtener_actualizaciones(self, offset: int | None) -> list[dict]: ...

    def enviar_mensaje(self, chat_id: int | str, texto: str) -> None: ...


class ClienteBotAPI:
    """Transporte real: httpx sobre la Bot API de Telegram.

    Dos clientes httpx separados, cada uno con su propio timeout: `_http`
    para el long polling de getUpdates (TIMEOUT_POLLING_SEGUNDOS, de sobra
    porque Telegram puede tardarse hasta ese tiempo en responder sin
    novedades) y `_http_envios` para `enviar_mensaje` (TIMEOUT_ENVIO_SEGUNDOS,
    mucho más corto porque a este no lo puede bloquear nadie)."""

    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._http = httpx.Client(timeout=TIMEOUT_POLLING_SEGUNDOS + 10)
        self._http_envios = httpx.Client(timeout=TIMEOUT_ENVIO_SEGUNDOS)

    def obtener_actualizaciones(self, offset: int | None) -> list[dict]:
        parametros: dict[str, int] = {"timeout": TIMEOUT_POLLING_SEGUNDOS}
        if offset is not None:
            parametros["offset"] = offset
        respuesta = self._http.get(f"{self._base}/getUpdates", params=parametros)
        respuesta.raise_for_status()
        return respuesta.json().get("result", [])

    def enviar_mensaje(self, chat_id: int | str, texto: str) -> None:
        self._http_envios.post(f"{self._base}/sendMessage", json={"chat_id": chat_id, "text": texto})


def _fecha_corta(fecha: datetime) -> str:
    return f"{fecha.day} de {_MESES_NOMBRE[fecha.month]}"


def _monto_corto(monto: float) -> str:
    entero = int(monto)
    texto = f"{entero:,}".replace(",", ".")
    if monto == entero:
        return texto
    decimales = f"{monto:.2f}".split(".")[1]
    return f"{texto},{decimales}"


def _procesar_texto(texto: str) -> str:
    """Lo que contesta el bot a un mensaje de charla corta. Una entrega con
    la forma exacta se crea por la misma vía que POST /entregas; si no,
    pasa por la misma función que /mensaje (clasificador, memoria y
    carácter incluidos) con origen="texto", modo="rapido"."""
    import entregas
    import servidor

    parseada = entregas.parsear_entrega(texto)
    if parseada is not None:
        entrega = entregas.crear_desde_texto(entregas.CrearEntregaDesdeTexto(texto=texto))
        # parsear_entrega no reconoce el texto sin un monto: acá siempre viene puesto.
        monto = _monto_corto(entrega.monto) if entrega.monto is not None else "?"
        return f"Entrega para {entrega.cliente}: {_fecha_corta(entrega.fecha)}, ${monto}"

    mensaje = servidor.MensajeEntrante(texto=texto, origen="texto", modo="rapido", think=True, canal="telegram")
    respuesta = servidor.recibir_mensaje(mensaje)
    return servidor.para_hablar(respuesta.texto)


def _manejar_start(chat_id: int | str) -> None:
    if chat_id_configurado() is not None:
        return
    print(
        f"[telegram] /start de chat_id={chat_id}: pon TELEGRAM_CHAT_ID={chat_id} en nucleo/.env",
        file=sys.stderr,
        flush=True,
    )


def _manejar_actualizacion(transporte: Transporte, actualizacion: dict) -> None:
    mensaje = actualizacion.get("message")
    if not mensaje:
        return
    chat = mensaje.get("chat", {})
    chat_id = chat.get("id")
    texto = mensaje.get("text")
    if chat_id is None or not texto:
        return

    if texto.strip() == "/start":
        _manejar_start(chat_id)
        return

    configurado = chat_id_configurado()
    if configurado is None:
        # Sin CHAT_ID no se sabe quién es Juan Camilo: no se contesta a nadie.
        return
    if str(chat_id) != str(configurado):
        return  # cualquier otro chat_id, en silencio

    respuesta = _procesar_texto(texto)
    transporte.enviar_mensaje(chat_id, respuesta)


def escuchar(transporte: Transporte, seguir: Callable[[], bool] | None = None) -> None:
    """El loop de long polling. `seguir` existe para que las pruebas puedan
    cortarlo tras un número fijo de vueltas."""
    offset: int | None = None
    while seguir is None or seguir():
        try:
            actualizaciones = transporte.obtener_actualizaciones(offset)
        except Exception as error:  # nunca tumbar el hilo por un error de red
            print(f"[telegram] falló getUpdates ({type(error).__name__}: {error})", file=sys.stderr, flush=True)
            time.sleep(1)
            continue
        for actualizacion in actualizaciones:
            offset = actualizacion["update_id"] + 1
            try:
                _manejar_actualizacion(transporte, actualizacion)
            except Exception as error:  # una actualización rota no tumba el hilo
                print(f"[telegram] falló al procesar una actualización ({type(error).__name__}: {error})", file=sys.stderr, flush=True)


# El evento de parada del hilo que está corriendo ahora, si hay uno.
# `reiniciar_hilo()` lo usa para apagar el polling viejo al arrancar uno
# nuevo, sin tocar el proceso del núcleo.
_evento_detener: threading.Event | None = None


def _iniciar_polling(tok: str) -> None:
    global _evento_detener
    evento = threading.Event()
    _evento_detener = evento
    transporte = ClienteBotAPI(tok)
    hilo = threading.Thread(target=escuchar, args=(transporte, lambda: not evento.is_set()), daemon=True)
    hilo.start()


def arrancar_hilo() -> None:
    """Se llama desde el startup de servidor.py. Sin TELEGRAM_TOKEN, el bot
    no arranca y lo dice una vez; el núcleo sigue igual.

    REMI_TELEGRAM=0 apaga el hilo aunque haya token: mismo patrón que
    REMI_TTS_PRECALENTAR y REMI_SEMBRAR_CONOCIMIENTO, para que correr la
    batería de pruebas con un nucleo/.env real no dispare long polling de
    verdad contra Telegram."""
    if os.environ.get("REMI_TELEGRAM", "1") == "0":
        return

    tok = token()
    if tok is None:
        print("[telegram] sin TELEGRAM_TOKEN en nucleo/.env: el bot no arranca", file=sys.stderr, flush=True)
        return

    _iniciar_polling(tok)


def reiniciar_hilo() -> None:
    """Para el polling viejo (si había uno) y arranca uno nuevo con el
    token/chat_id de ahora — lo llama nucleo/conexiones.py al guardar
    TELEGRAM_TOKEN o TELEGRAM_CHAT_ID desde el panel. El hilo viejo puede
    tardar hasta TIMEOUT_POLLING_SEGUNDOS en notar el evento y salir —
    está bien, el nuevo ya está sirviendo mientras tanto, y los dos con
    el mismo token nunca duran más que eso superpuestos."""
    if os.environ.get("REMI_TELEGRAM", "1") == "0":
        return
    if _evento_detener is not None:
        _evento_detener.set()

    tok = token()
    if tok is None:
        print("[telegram] sin TELEGRAM_TOKEN tras guardar: el bot queda apagado", file=sys.stderr, flush=True)
        return
    _iniciar_polling(tok)


def en_silencio(ahora: datetime | None = None) -> bool:
    """23:00–7:00 en Bogotá: nada sale salvo que el aviso sea urgente."""
    ahora = (ahora or datetime.now(BOGOTA)).astimezone(BOGOTA)
    hora = ahora.hour
    return hora >= HORA_SILENCIO_DESDE or hora < HORA_SILENCIO_HASTA


def mensaje_reporte_noche(cambios: list[tuple[str, str]], max_mostrados: int = 3) -> str:
    """El mensaje que `noche.py` manda por `/telegram/avisar` después de
    consolidar. Sin cambios, es literalmente «Anoche no toqué nada» — nunca
    «cambié 0 libros». Con cambios: «Anoche cambié N libros» y hasta
    `max_mostrados` diffs cortos (uno por libro, ya recortados por quien
    llama); si sobran, cierra con «y M más»."""
    if not cambios:
        return "Anoche no toqué nada"
    total = len(cambios)
    mostrados = cambios[:max_mostrados]
    piezas = [f"Anoche cambié {total} libro{'s' if total != 1 else ''}"]
    for titulo, diff in mostrados:
        piezas.append(f"{titulo}:\n{diff}")
    restantes = total - len(mostrados)
    if restantes > 0:
        piezas.append(f"y {restantes} más")
    return "\n\n".join(piezas)


router = APIRouter(prefix="/telegram", tags=["telegram"])


class AvisoSaliente(BaseModel):
    texto: str
    urgente: bool = False


# Un solo transporte para los avisos salientes, reutilizado entre llamadas a
# avisar() — nunca uno nuevo por aviso. Se recrea si cambia el token (p. ej.
# tras reiniciar_hilo) o si cambia el constructor ClienteBotAPI (las pruebas
# lo monkeypatchean caso por caso).
_avisos_cache_clave: tuple[object, str] | None = None
_avisos_cache_transporte: Transporte | None = None


def _transporte_para_avisar(tok: str) -> Transporte:
    global _avisos_cache_clave, _avisos_cache_transporte
    clave = (ClienteBotAPI, tok)
    if clave != _avisos_cache_clave:
        _avisos_cache_clave = clave
        _avisos_cache_transporte = ClienteBotAPI(tok)
    assert _avisos_cache_transporte is not None
    return _avisos_cache_transporte


def _enviar_con_reintento(transporte: Transporte, chat_id: int | str, texto: str) -> None:
    """Corre en un hilo daemon, lejos de quien llamó a avisar(): nunca debe
    tumbar nada, pase lo que pase con el envío real. Un solo reintento, a
    los REINTENTO_AVISO_SEGUNDOS, si el primer intento falla; cada llamada
    HTTP (exitosa o no) deja su propio `ms=` en el log."""
    motivo = ""
    ms = 0.0
    for intento in range(2):
        if intento == 1:
            time.sleep(REINTENTO_AVISO_SEGUNDOS)
        inicio = time.perf_counter()
        try:
            transporte.enviar_mensaje(chat_id, texto)
        except Exception as error:  # nunca tumbar el hilo de fondo
            ms = (time.perf_counter() - inicio) * 1000
            motivo = f"{type(error).__name__}: {error}"
            print(
                f"[telegram] intento {intento + 1} de avisar falló ({motivo}, ms={ms:.0f})",
                file=sys.stderr,
                flush=True,
            )
            continue
        ms = (time.perf_counter() - inicio) * 1000
        print(f"[telegram] avisé (ms={ms:.0f})", file=sys.stderr, flush=True)
        return
    print(f"[telegram] falló avisar ({motivo}, ms={ms:.0f})", file=sys.stderr, flush=True)


@router.post("/avisar", status_code=204)
def avisar(cuerpo: AvisoSaliente) -> None:
    """La única puerta de salida hacia el teléfono: la llaman el motor de
    iniciativa y el vigía (f-fase3), nunca este módulo. Respeta el
    silencio 23:00–7:00 salvo `urgente: true`.

    Responde 204 de inmediato: el envío real (con su reintento) corre en un
    hilo daemon, para que ni el vigía ni la iniciativa se queden esperando
    a Telegram."""
    if en_silencio() and not cuerpo.urgente:
        return
    configurado = chat_id_configurado()
    if configurado is None:
        print("[telegram] sin TELEGRAM_CHAT_ID: no puedo avisar", file=sys.stderr, flush=True)
        return
    tok = token()
    if tok is None:
        print("[telegram] sin TELEGRAM_TOKEN: no puedo avisar", file=sys.stderr, flush=True)
        return
    transporte = _transporte_para_avisar(tok)
    hilo = threading.Thread(
        target=_enviar_con_reintento,
        args=(transporte, configurado, cuerpo.texto),
        daemon=True,
    )
    hilo.start()

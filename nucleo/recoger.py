"""Recoger links por Telegram para la bóveda.

    /info     abre la recolección: desde ahí cada mensaje con links se acumula
    /listo    cierra y manda todo a la bóveda (también /enviar)
    /cancelar descarta lo recogido
    /estado   cuántos links van

Cero modelo, cero tokens: solo texto. Al cerrar, `lote.py` de la bóveda lee
cada link (YouTube, Instagram, TikTok, blogs) en segundo plano y Remi avisa
por Telegram cuántos entraron y cuáles fallaron. El Mac tiene que estar
prendido; si está dormido, el aviso llega cuando despierte.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import db

_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
_ABRIR = {"/info", "/links"}
_CERRAR = {"/listo", "/enviar"}
MAX_LINKS = 500
MAX_MOSTRADOS = 5
AUTO_ESPERA_SEG = 45          # calma sin links nuevos antes de empezar a leer
_SOLO_LINK_MAX_LETRAS = 12    # «mira esto:» cabe; una frase entera ya es charla
_SITIOS_AUTO = ("youtube.com", "youtu.be", "youtube-nocookie.com", "instagram.com", "tiktok.com")
_CANDADO = threading.Lock()   # un lote a la vez: Whisper y las plataformas no aguantan más
_TEMPORIZADORES: dict[str, threading.Timer] = {}


def extraer_urls(texto: str) -> list[str]:
    vistos: dict[str, None] = {}
    for crudo in _URL.findall(texto or ""):
        url = crudo.rstrip(".,;:!?»”’")
        if urlparse(url).netloc:
            vistos.setdefault(url, None)
    return list(vistos)


def _boveda() -> Path | None:
    for c in (os.environ.get("REMI_BOVEDA"), "/Volumes/ORGANIC/boveda"):
        if c and Path(c).is_dir():
            return Path(c)
    return None


def _ruta_estado() -> Path:
    return db.ruta_db().parent / "recoleccion.json"


def _leer() -> dict[str, list[str]]:
    try:
        datos = json.loads(_ruta_estado().read_text(encoding="utf-8"))
        return {str(k): list(v) for k, v in datos.items()}
    except (OSError, ValueError):
        return {}


def _guardar(estado: dict[str, list[str]]) -> None:
    ruta = _ruta_estado()
    tmp = ruta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ruta)


def _python_de(boveda: Path) -> str:
    venv = boveda / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def resumen_corto(markdown: str) -> str:
    """El cuadro de cache/ultimo_lote.md reducido a lo que cabe en un celular."""
    lineas = markdown.splitlines()
    cuenta = next((l for l in lineas if "entraron" in l), "Terminé.")
    if "## Fallaron" not in lineas:
        return f"✔ {cuenta}"
    falla = [l[2:] for l in lineas[lineas.index("## Fallaron") + 1:] if l.startswith("- ")]
    visibles = "\n".join(f"• {l[:140]}" for l in falla[:MAX_MOSTRADOS])
    extra = f"\n…y {len(falla) - MAX_MOSTRADOS} más (están en la bóveda)" if len(falla) > MAX_MOSTRADOS else ""
    return f"✔ {cuenta}\n{visibles}{extra}"


def _lanzar_y_avisar(boveda: Path, archivo: Path, avisar: Callable[[str], None]) -> None:
    """Corre lote.py aparte y, al terminar, avisa. En un hilo para no frenar el polling."""
    def trabajo() -> None:
        try:
            _CANDADO.acquire()
            r = subprocess.run([_python_de(boveda), "lote.py", str(archivo)], cwd=boveda, capture_output=True, text=True, timeout=6 * 3600)
            ultimo = boveda / "cache" / "ultimo_lote.md"
            avisar(resumen_corto(ultimo.read_text(encoding="utf-8")) if ultimo.exists() and r.returncode in (0, 1) else "No pude leer el resultado del lote. Mira la bóveda en el Mac.")
        except Exception as exc:  # noqa: BLE001 — avisar siempre, aunque falle
            avisar(f"El lote se cayó ({type(exc).__name__}). Los links están guardados en la bóveda.")
        finally:
            if _CANDADO.locked():
                _CANDADO.release()

    threading.Thread(target=trabajo, daemon=True).start()


def _es_solo_links_de_contenido(texto: str) -> list[str]:
    """Los links del mensaje si es SOLO links de YouTube/Instagram/TikTok (con a lo sumo
    unas palabras). Cualquier otra cosa devuelve [] y sigue como charla normal."""
    urls = extraer_urls(texto)
    if not urls or len(re.sub(r"\W+", "", _URL.sub("", texto))) > _SOLO_LINK_MAX_LETRAS:
        return []
    for u in urls:
        host = (urlparse(u).hostname or "").lower()
        if not any(host == d or host.endswith("." + d) for d in _SITIOS_AUTO):
            return []
    return urls


def _programar(segundos: float, funcion: Callable[[], None]) -> threading.Timer:
    t = threading.Timer(segundos, funcion)
    t.daemon = True
    t.start()
    return t


def _escribir_lote(boveda: Path, nombre: str, links: list[str], ahora: datetime) -> Path:
    carpeta = boveda / "00_inbox" / "_telegram"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{nombre}-{ahora:%Y%m%d-%H%M%S}.txt"
    archivo.write_text("\n".join(links) + "\n", encoding="utf-8")
    return archivo


def cerrar_auto(chat_id: int | str, avisar: Callable[[str], None], lanzar: Callable[..., None] | None = None, ahora: datetime | None = None) -> None:
    """Lo acumulado por «compartir a Telegram» pasa a la bóveda. Si no hay bóveda,
    los links se quedan guardados y se reintenta en el próximo mensaje o reinicio."""
    estado = _leer()
    clave = f"auto:{chat_id}"
    links = estado.get(clave) or []
    if not links:
        return
    boveda = _boveda()
    if boveda is None:
        avisar("No encuentro la bóveda (¿el disco ORGANIC está conectado?). Tus links quedan guardados y los leo cuando vuelva.")
        return
    archivo = _escribir_lote(boveda, "auto", links, ahora or datetime.now())
    estado.pop(clave)
    _guardar(estado)
    avisar(f"Leyendo {len(links)} link(s) de la bóveda…")
    (lanzar or _lanzar_y_avisar)(boveda, archivo, avisar)


def reanudar(enviar: Callable[[str, str], None], espera: float = 5, programar: Callable[..., object] | None = None, lanzar: Callable[..., None] | None = None) -> int:
    """Al arrancar el núcleo: links compartidos que se quedaron esperando (se cayó o se
    reinició antes de leerlos). Devuelve cuántos chats tenían algo pendiente."""
    pendientes = [k for k, v in _leer().items() if k.startswith("auto:") and v]
    for k in pendientes:
        chat = k.split(":", 1)[1]
        (programar or _programar)(espera, lambda c=chat: cerrar_auto(c, lambda t, c=c: enviar(c, t), lanzar))
    return len(pendientes)


def manejar(chat_id: int | str, texto: str, avisar: Callable[[str], None], lanzar: Callable[[Path, Path, Callable[[str], None]], None] | None = None, ahora: datetime | None = None, programar: Callable[..., object] | None = None, espera: float = AUTO_ESPERA_SEG) -> str | None:
    """Devuelve lo que contesta Remi, o None si el mensaje no es de la recolección."""
    cmd = texto.strip().split()[0].lower().split("@")[0] if texto.strip() else ""
    estado = _leer()
    clave = str(chat_id)
    abierta = clave in estado

    if cmd in _ABRIR:
        if abierta:
            return f"Ya está abierto: {len(estado[clave])} link(s). Sigue pegando o manda /listo."
        estado[clave] = []
        _guardar(estado)
        pegado = extraer_urls(texto)
        if pegado:
            estado[clave] = pegado
            _guardar(estado)
            return f"Abierto. {len(pegado)} link(s). Sigue pegando o manda /listo."
        return "Abierto. Pega tus links (uno o varios por mensaje). Cuando termines, /listo. Para soltar todo, /cancelar."

    if cmd == "/estado":
        return f"Van {len(estado[clave])} link(s). /listo para enviar." if abierta else "No hay nada abierto. /info para empezar."

    if cmd == "/cancelar":
        if not abierta:
            return "No había nada abierto."
        n = len(estado.pop(clave))
        _guardar(estado)
        return f"Listo, descarté {n} link(s)."

    if cmd in _CERRAR:
        if not abierta:
            return "No hay nada abierto. Manda /info primero."
        links = estado[clave]
        if not links:
            return "Todavía no hay links. Pega algunos o /cancelar."
        boveda = _boveda()
        if boveda is None:
            return "No encuentro la bóveda (¿el disco ORGANIC está conectado?). Tus links siguen guardados; manda /listo cuando esté."
        archivo = _escribir_lote(boveda, "lote", links, ahora or datetime.now())
        estado.pop(clave)
        _guardar(estado)
        (lanzar or _lanzar_y_avisar)(boveda, archivo, avisar)
        return f"{len(links)} link(s) en la bóveda. Los estoy leyendo; te aviso cuando termine."

    if abierta:  # cualquier otro mensaje mientras se recoge: buscar links
        if cmd.startswith("/"):
            return "Eso no lo entiendo ahora. Pega links, /listo para enviar o /cancelar."
        nuevos = [u for u in extraer_urls(texto) if u not in estado[clave]]
        if not extraer_urls(texto):
            return "No vi links en eso. Sigo esperando."
        lugar = MAX_LINKS - len(estado[clave])
        if lugar <= 0:
            return f"Ya hay {MAX_LINKS} links. Manda /listo y empezamos otro lote."
        estado[clave] += nuevos[:lugar]
        _guardar(estado)
        return f"+{len(nuevos[:lugar])} · {len(estado[clave])} en total" if nuevos else f"Ya los tenía · {len(estado[clave])} en total"

    # Compartir desde el celular: un mensaje que es solo links de YouTube/Instagram/TikTok
    # entra solo, sin /info. Espera `espera` s de calma y los lee todos juntos.
    auto = _es_solo_links_de_contenido(texto)
    if auto:
        k = f"auto:{clave}"
        cola = estado.get(k, [])
        nuevos = [u for u in auto if u not in cola]
        estado[k] = (cola + nuevos)[:MAX_LINKS]
        _guardar(estado)
        previo = _TEMPORIZADORES.pop(k, None)
        if previo is not None and hasattr(previo, "cancel"):
            previo.cancel()
        _TEMPORIZADORES[k] = (programar or _programar)(espera, lambda: cerrar_auto(chat_id, avisar, lanzar, ahora))
        return f"Anotado ✓ ({len(estado[k])} en espera; los leo en {int(espera)} s si no mandas más)"

    return None

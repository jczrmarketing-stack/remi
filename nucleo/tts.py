"""Voz de Remi, local y sin clave: Kokoro-82M en CPU.

Un solo modelo en memoria; las voces son embeddings, cambiar de voz no
recarga los pesos. El idioma lo marca el prefijo del id de la voz, nunca
un segundo modelo: `a…` es inglés, `e…` es español. Mezclar texto español
con una voz `a…` suena a spanglish, así que no se mezcla.

Nada de esto sale del Mac: los pesos se bajan una vez y después todo corre
acá adentro."""
from __future__ import annotations

import io
import re
import sys
import threading
from dataclasses import dataclass
from typing import Any

# Frecuencia de salida de Kokoro. La ventanita recibe wav 24 kHz mono.
FRECUENCIA = 24000
# Por defecto el modelo habla a 1×. La ventanita le pide 1,5× cuando Juan
# Camilo lo elige: estirar el audio en el reproductor se comía palabras, y
# el modelo acelera sin perderlas.
VELOCIDAD_GENERACION = 1.0


@dataclass(frozen=True)
class Voz:
    id: str
    lang: str
    label: str


# Las cuatro que eligió Milo, ni una más. El orden es el de la ventanita.
VOCES: tuple[Voz, ...] = (
    Voz("em_alex", "es", "Alex (ES)"),
    Voz("ef_dora", "es", "Dora (ES)"),
    Voz("em_santa", "es", "Santa (ES)"),
    Voz("af_bella", "en", "Bella (EN)"),
)
POR_ID: dict[str, Voz] = {voz.id: voz for voz in VOCES}

VOZ_ES = "em_alex"
VOZ_EN = "af_bella"


def lang_code(voz_id: str) -> str:
    """El prefijo manda: `a…` inglés, `e…` español."""
    return "a" if voz_id.startswith("a") else "e"


# — Elegir voz en automático —
# Sin modelo de detección de idioma: Remi habla español salvo que el texto
# sea claramente inglés. Ante la duda, español (es el locale de la UI).
_SENAS_ES = re.compile(
    r"[áéíóúñ¿¡]|\b(el|la|los|las|de|que|para|con|una|este|esta|tu|te|ya|hoy|"
    r"solo|minutos|abre|busca|anota|escribe)\b",
    re.IGNORECASE,
)
_SENAS_EN = re.compile(
    r"\b(the|and|your|you|this|that|with|for|open|write|check|just|now|"
    r"minutes|listening)\b",
    re.IGNORECASE,
)


def elegir_voz(texto: str) -> str:
    return VOZ_EN if len(_SENAS_EN.findall(texto)) > len(_SENAS_ES.findall(texto)) else VOZ_ES


def resolver_voz(pedida: str | None, texto: str) -> str | None:
    """None solo si pidió una voz que no existe: eso es un 400, no un fallo
    silencioso. `None`/"auto" eligen por el texto."""
    if pedida is None or pedida == "auto":
        return elegir_voz(texto)
    return pedida if pedida in POR_ID else None


# — El motor —
# Un pipeline por idioma, creado la primera vez que hace falta y
# reusado después: crear uno por frase volvería a leer los pesos.
_pipelines: dict[str, Any] = {}
_candado = threading.Lock()
# El motor es un modelo de torch: una síntesis a la vez. Con un solo
# usuario no se nota, y evita pisarse si llegan dos frases juntas.
_candado_sintesis = threading.Lock()


def _pipeline(codigo: str) -> Any:
    with _candado:
        if codigo not in _pipelines:
            from kokoro import KPipeline

            print(f"[tts] cargando el modelo para '{codigo}' (la primera vez tarda)", file=sys.stderr)
            _pipelines[codigo] = KPipeline(lang_code=codigo)
        return _pipelines[codigo]


def precalentar(voz_id: str = VOZ_ES) -> None:
    """Deja el modelo listo antes de la primera frase real. Se llama en un
    hilo al arrancar: si falla, no importa, se reintenta al hablar."""
    try:
        _pipeline(lang_code(voz_id))
    except Exception as error:  # el motor es de terceros: cualquier cosa puede salir
        print(f"[tts] no pude precalentar ({type(error).__name__}): sigo igual", file=sys.stderr)


def sintetizar(texto: str, voz_id: str, velocidad: float = VELOCIDAD_GENERACION) -> bytes | None:
    """El wav de `texto` dicho por `voz_id`, o None si el motor falla. Un
    fallo acá es silencio: la ventanita cae a la voz del sistema y Remi
    nunca dice el error en voz alta."""
    try:
        import numpy as np
        import soundfile as sf

        pipeline = _pipeline(lang_code(voz_id))
        with _candado_sintesis:
            trozos = [
                resultado.audio
                for resultado in pipeline(texto, voice=voz_id, speed=velocidad)
                if resultado.audio is not None
            ]
        if not trozos:
            print("[tts] el motor no devolvió audio", file=sys.stderr)
            return None

        # Kokoro devuelve tensores de torch; soundfile quiere numpy.
        muestras = [
            trozo.detach().cpu().numpy() if hasattr(trozo, "detach") else np.asarray(trozo)
            for trozo in trozos
        ]
        onda = muestras[0] if len(muestras) == 1 else np.concatenate(muestras)

        buffer = io.BytesIO()
        sf.write(buffer, onda, FRECUENCIA, format="WAV", subtype="PCM_16")
        return buffer.getvalue()
    except Exception as error:
        print(f"[tts] falló la síntesis ({type(error).__name__}: {error})", file=sys.stderr)
        return None

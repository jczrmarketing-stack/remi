#!/usr/bin/env python
"""Prueba de humo del TTS de Remi: genera un wav por cada una de las cuatro
voces y mide cuánto tardó. Usa el MISMO módulo que el endpoint del núcleo
(`nucleo/tts.py`), así lo que se escucha acá es exactamente lo que va a
decir Remi.

    cd nucleo && uv run python ../vendor/kokoro/tts_kokoro.py

Los wav salen en vendor/kokoro/salida/ (fuera de git).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ / "nucleo"))

import tts  # noqa: E402

FRASES = {"es": "Hola, soy Remi. Te escucho.", "en": "Hi, I'm Remi. I'm listening."}
SALIDA = Path(__file__).resolve().parent / "salida"


def main() -> int:
    SALIDA.mkdir(exist_ok=True)
    fallaron = []

    for voz in tts.VOCES:
        texto = FRASES[voz.lang]
        arranque = time.perf_counter()
        audio = tts.sintetizar(texto, voz.id)
        tardanza = time.perf_counter() - arranque

        if audio is None:
            print(f"✗ {voz.id:<10} {voz.label:<12} no generó audio")
            fallaron.append(voz.id)
            continue

        destino = SALIDA / f"{voz.id}.wav"
        destino.write_bytes(audio)
        segundos_audio = (len(audio) - 44) / (tts.FRECUENCIA * 2)
        print(
            f"✓ {voz.id:<10} {voz.label:<12} {len(audio) / 1024:6.0f} KB  "
            f"{segundos_audio:4.1f}s de audio  en {tardanza:4.1f}s  → {destino.name}"
        )

    # La elección automática: español salvo que el texto sea claramente inglés.
    print()
    for texto, esperada in ((FRASES["es"], tts.VOZ_ES), (FRASES["en"], tts.VOZ_EN)):
        elegida = tts.elegir_voz(texto)
        marca = "✓" if elegida == esperada else "✗"
        print(f"{marca} auto: {texto!r} → {elegida}")
        if elegida != esperada:
            fallaron.append(f"auto:{texto}")

    if fallaron:
        print(f"\nFallaron: {', '.join(fallaron)}")
        return 1
    print(f"\nLas cuatro voces suenan. Escuchalas en {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

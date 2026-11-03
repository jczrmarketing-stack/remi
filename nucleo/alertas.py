"""Las fallas de Remi van al bot de alertas de INV3RZA (@inv3rzabot), nunca al chat de Remi (3-nov).
JC: «de Remi solo necesito la newsletter; lo que falle, por otro canal». Usa la misma llave que la bóveda
(ALERTAS_TELEGRAM_TOKEN en ~/proyectos/boveda/_sistema/.env, o en nucleo/.env) y el chat de JC."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent


def _env(ruta: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    try:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip("\"'")
    except OSError:
        pass
    return valores


def credenciales() -> tuple[str, str]:
    import donde_boveda
    propio = _env(AQUI / ".env")
    boveda = _env(donde_boveda.INTERNA / "_sistema" / ".env")
    token = os.environ.get("ALERTAS_TELEGRAM_TOKEN") or propio.get("ALERTAS_TELEGRAM_TOKEN") or boveda.get("ALERTAS_TELEGRAM_TOKEN", "")
    chat = os.environ.get("ALERTAS_CHAT_ID") or propio.get("ALERTAS_CHAT_ID") or boveda.get("ALERTAS_CHAT_ID") or propio.get("TELEGRAM_CHAT_ID", "")
    return token, chat


def enviar(texto: str, post=None) -> bool:
    """Nunca levanta: una alerta que no sale se anota en stderr y la noche sigue."""
    token, chat = credenciales()
    if not token or not chat:
        print(f"[alertas] sin llave del bot de alertas: {texto[:120]}", file=sys.stderr, flush=True)
        return False
    try:
        (post or httpx.post)(f"https://api.telegram.org/bot{token}/sendMessage",
                             json={"chat_id": chat, "text": f"⚠️ INV3RZA · Remi\n{texto}"[:4000]}, timeout=15)
        return True
    except Exception as error:  # noqa: BLE001
        print(f"[alertas] no pude mandar la alerta ({type(error).__name__}): {texto[:120]}", file=sys.stderr, flush=True)
        return False


if __name__ == "__main__":
    sys.exit(0 if enviar(" ".join(sys.argv[1:]) or "Prueba de alertas de Remi.") else 1)

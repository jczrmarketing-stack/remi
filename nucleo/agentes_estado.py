"""Estado en vivo de los agentes de INV3RZA (3-nov).

Cada agente escribe aquí qué está haciendo; la Suite (/suite) lo lee para
pintar la oficina de cada piso. Un archivo por agente, escrito de forma
atómica: si dos procesos escriben a la vez, gana el último y nunca queda un
JSON a medias. Si un agente dice «trabajando» pero lleva más de 6 h sin
reportar, se considera caído (proceso muerto sin avisar).

Estados: trabajando | esperando | durmiendo | error.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(os.environ.get("REMI_ESTADO_AGENTES") or Path(__file__).resolve().parent.parent / "estado" / "agentes")
CATALOGO = Path(__file__).resolve().parent.parent / "config" / "agentes.json"
ESTADOS = ("trabajando", "esperando", "durmiendo", "error")
VENCE_TRABAJANDO = timedelta(hours=6)


def reportar(agente: str, estado: str, ahora: str = "", ultimo: str | None = None) -> None:
    """Lo llama el agente. `ahora`: qué hace en una frase. `ultimo`: su último trabajo terminado
    (si no se pasa, se conserva el que había)."""
    if estado not in ESTADOS:
        raise ValueError(f"estado desconocido: {estado}")
    RAIZ.mkdir(parents=True, exist_ok=True)
    previo = leer(agente) or {}
    datos = {"estado": estado, "ahora": ahora, "ultimo": ultimo if ultimo is not None else previo.get("ultimo", ""),
             "en": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    tmp = RAIZ / f".{agente}.tmp"
    tmp.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, RAIZ / f"{agente}.json")


def leer(agente: str) -> dict | None:
    try:
        return json.loads((RAIZ / f"{agente}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def catalogo() -> dict[str, dict]:
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    return {k: v for k, v in datos.items() if not k.startswith("$")}


def vivo(agente: str, ficha: dict, ahora: datetime | None = None) -> dict:
    """La ficha del catálogo + su estado real. Sin archivo: «esperando» si existe, «por crear» si no."""
    salida = {"id": agente, **ficha}
    if not ficha.get("existe"):
        return {**salida, "estado": "por_crear", "ahora": "", "ultimo": ""}
    estado = leer(agente)
    if not estado:
        return {**salida, "estado": "esperando", "ahora": "", "ultimo": ""}
    ahora = ahora or datetime.now(timezone.utc)
    try:
        en = datetime.fromisoformat(estado.get("en", ""))
    except ValueError:
        en = None
    if estado.get("estado") == "trabajando" and en and ahora - en > VENCE_TRABAJANDO:
        estado = {**estado, "estado": "error", "ahora": "Dejó de reportar mientras trabajaba"}
    return {**salida, "estado": estado.get("estado", "esperando"), "ahora": estado.get("ahora", ""),
            "ultimo": estado.get("ultimo", ""), "en": estado.get("en")}

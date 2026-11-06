"""Lo que el piso Ingeniería de la Suite muestra de la fábrica (6-nov).

Sin IA: lee los expedientes, el candado y `eventos.jsonl`. Da tres cosas a
`suite.armar`: tu paso (calmado, ley 4), la fila de estaciones para el edificio
y la lista «Pedidos de la fábrica» (máximo 5). Nunca rompe la Suite: si algo
falla, devuelve vacío.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fabrica import expediente

ESTACIONES = ("spec", "tests", "construir", "verificar", "revisar", "pr")
ESTADO_TEXTO = {
    "idea": "en cola, sin spec",
    "spec": "spec, espera tu sí",
    "aprobado": "aprobado, por construir",
    "construyendo": "construyendo",
    "revisando": "revisando",
    "pr": "PR en borrador",
    "cerrado": "cerrado",
}
PLIST = Path.home() / "Library" / "LaunchAgents" / "com.remi.fabrica.plist"
_ORDEN_FOCO = (("construyendo", "revisando"), ("pr",), ("spec",), ("aprobado",), ("idea",))


def _raiz(raiz: Path | None) -> Path:
    return expediente._raiz(raiz)


def corriendo(raiz: Path | None = None) -> bool:
    """Hay un pedido en la línea si el candado existe y su proceso vive."""
    from fabrica import linea  # aquí: linea importa agentes, que es más pesado

    ruta = _raiz(raiz) / ".candado"
    try:
        pid = int(ruta.read_text().strip() or 0)
    except (OSError, ValueError):
        return False
    return bool(pid) and linea._vivo(pid)


def eventos(id_: str, raiz: Path | None = None) -> list[dict[str, Any]]:
    ruta = expediente.carpeta(id_, raiz) / "eventos.jsonl"
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    filas = []
    for linea in lineas:
        try:
            filas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return filas


def pr_url(evs: list[dict[str, Any]]) -> str:
    for e in reversed(evs):
        if e.get("rol") == "linea" and e.get("tipo") == "fin" and str(e.get("texto", "")).startswith("http"):
            return str(e["texto"])
    return ""


def estacion_actual(evs: list[dict[str, Any]]) -> str | None:
    """La última estación con eventos. El Revisor no anota estación propia:
    sus eventos llegan después de `verificar`."""
    actual = None
    for e in evs:
        if e.get("tipo") == "estacion" and e.get("texto") in ESTACIONES:
            actual = e["texto"]
        elif e.get("rol") == "revisor":
            actual = "revisar"
    return actual


def estaciones(estado: str, evs: list[dict[str, Any]], vivo: bool) -> list[dict[str, str]]:
    """Cada estación hecha, activa o por venir. Sin candado no hay activa."""
    if estado in ("pr", "cerrado"):
        return [{"id": k, "estado": "hecha"} for k in ESTACIONES]
    actual = estacion_actual(evs)
    if estado in ("spec", "aprobado") and not vivo:
        actual, vivo = "tests", False   # la spec está hecha; lo demás espera
    i = ESTACIONES.index(actual) if actual in ESTACIONES else -1
    filas = []
    for n, k in enumerate(ESTACIONES):
        if n < i or (n == i and not vivo):
            filas.append({"id": k, "estado": "hecha" if n < i else "por_venir"})
        elif n == i:
            filas.append({"id": k, "estado": "activa"})
        else:
            filas.append({"id": k, "estado": "por_venir"})
    return filas


def idea(id_: str, raiz: Path | None = None) -> str:
    try:
        texto = expediente.leer(id_, raiz)["secciones"].get("Contexto", "")
    except (KeyError, OSError):
        return id_
    primera = (texto.strip().splitlines() or [id_])[0]
    corte = re.search(r":| \(", primera[:70]) if len(primera) > 70 else None
    corta = primera[:corte.start()] if corte else primera
    return corta if len(corta) <= 70 else corta[:69].rstrip() + "…"


def en_foco(pedidos: list[dict[str, Any]], vivo: bool, raiz: Path | None = None) -> dict[str, Any] | None:
    """El pedido que importa ahora. Con la línea corriendo, el de eventos más recientes."""
    if vivo:
        abiertos = [p for p in pedidos if p.get("estado") != "cerrado"]

        def tocado(p: dict[str, Any]) -> float:
            try:
                return (expediente.carpeta(p["pedido"], raiz) / "eventos.jsonl").stat().st_mtime
            except OSError:
                return 0.0

        if abiertos:
            return max(abiertos, key=tocado)
    for estados in _ORDEN_FOCO:
        for p in pedidos:   # el más nuevo primero
            if p.get("estado") in estados:
                return p
    return None


def _paso(foco: dict[str, Any] | None, titulo: str, url: str, vivo: bool, en_cola: int) -> dict[str, str] | None:
    if vivo:
        return {"titulo": "Nada que hacer: la línea trabaja.",
                "contexto": "Te aviso cuando haya un PR en borrador. Nada se fusiona sin ti."}
    if foco and foco.get("estado") == "pr":
        paso = {"titulo": "Un PR espera tu revisión.",
                "contexto": f"«{titulo}» pasó el verificador y la revisión. Tú decides si se une."}
        if url:
            paso.update(accion="Abrir el PR", ruta=url)
        return paso
    if foco and foco.get("estado") == "spec":
        return {"titulo": "Una spec espera tu sí.",
                "contexto": f"«{titulo}». Léela abajo, en la estación Spec. Se aprueba con `python -m fabrica aprobar {foco['pedido']} --de-noche`."}
    if en_cola:
        plural = "pedido" if en_cola == 1 else "pedidos"
        return {"titulo": "Nada que hacer: la fábrica trabaja de noche.",
                "contexto": f"Hay {en_cola} {plural} en la cola de las 2:30. Te aviso por Telegram."}
    return None


def piso(raiz: Path | None = None) -> dict[str, Any]:
    """Todo lo de la fábrica para el piso Ingeniería. Vacío si no hay pedidos."""
    try:
        pedidos = expediente.listar(raiz)
    except (OSError, KeyError, ValueError):
        return {}
    vivo = corriendo(raiz)
    foco = en_foco(pedidos, vivo, raiz)
    salida: dict[str, Any] = {"corriendo": vivo}
    if PLIST.exists():
        salida["horario"] = ["La fábrica, un pedido por noche", "02:30"]
    if not pedidos:
        return salida
    abiertos = [p for p in pedidos if p.get("estado") != "cerrado"]
    filas = [[idea(p["pedido"], raiz), ESTADO_TEXTO.get(str(p.get("estado")), str(p.get("estado")))]
             for p in (abiertos + [p for p in pedidos if p.get("estado") == "cerrado"])[:5]]
    salida["entra"] = {"titulo": "Pedidos de la fábrica", "fuente": "de la cola", "filas": filas}
    en_cola = sum(1 for p in abiertos if p.get("estado") in ("idea", "aprobado") and p.get("noche"))
    if foco:
        evs = eventos(foco["pedido"], raiz)
        titulo = idea(foco["pedido"], raiz)
        url = pr_url(evs)
        foco_vivo = vivo and foco.get("estado") != "cerrado"
        salida["linea"] = {"id": foco["pedido"], "idea": titulo, "estado": foco.get("estado"),
                           "corriendo": foco_vivo, "pr": url,
                           "estaciones": estaciones(str(foco.get("estado")), evs, foco_vivo)}
        paso = _paso(foco, titulo, url, foco_vivo, en_cola)
    else:
        paso = _paso(None, "", "", False, en_cola)
    if paso:
        salida["paso"] = paso
    return salida

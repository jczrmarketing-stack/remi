"""Rutas de la fábrica para el piso Ingeniería del panel (4402).

GET /fabrica/pedidos                      → los pedidos, el más nuevo primero
GET /fabrica/pedidos/{id}                 → expediente + tokens gastados + tope
GET /fabrica/pedidos/{id}/eventos?desde=N → eventos desde N (el panel lee cada 2 s)
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

import consumo
from fabrica import agentes, expediente

router = APIRouter(prefix="/fabrica", tags=["fabrica"])


def _leer(id_: str) -> dict[str, Any]:
    try:
        return expediente.leer(id_)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No encuentro el pedido {id_}.") from None


@router.get("/pedidos")
def pedidos() -> list[dict[str, Any]]:
    return expediente.listar()


@router.get("/pedidos/{id_}")
def pedido(id_: str) -> dict[str, Any]:
    datos = _leer(id_)
    return {**datos, "tokens": consumo.tokens_del_pedido(id_), "tope": agentes.config()["tope_tokens_pedido"]}


@router.get("/pedidos/{id_}/eventos")
def eventos(id_: str, desde: int = 0) -> dict[str, Any]:
    _leer(id_)
    ruta = expediente.carpeta(id_) / "eventos.jsonl"
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        lineas = []
    desde = max(desde, 0)
    filas = []
    for linea in lineas[desde:]:
        try:
            filas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return {"eventos": filas, "siguiente": len(lineas)}

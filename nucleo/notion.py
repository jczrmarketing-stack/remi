"""Cliente delgado de la API de Notion, y la puerta HTTP del sync (Fase 4).

El token vive en `nucleo/.env` (fuera del repo, gitignored), nunca en git —
mismo patrón que `pensar._leer_env` para Venice. Sin `NOTION_TOKEN`, todo lo
de acá se salta con un aviso en stderr: el núcleo sigue andando sin Notion.

Para tener con qué probar `notion_sync.py` sin pegarle a la API real, este
módulo no trae ningún doble de prueba — las pruebas arman el suyo con la
misma forma que `Notion` (mismos métodos), como pide el encargo.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter

RUTA_ENV = Path(__file__).resolve().parent / ".env"
BASE_URL = "https://api.notion.com/v1"
VERSION = "2022-06-28"
TIMEOUT_SEGUNDOS = 15.0


def _leer_env(ruta: Path | None = None) -> dict[str, str]:
    """KEY=VALOR por línea; # comenta; comillas alrededor del valor se quitan.
    Copia deliberada del mismo parser de `pensar._leer_env`: un .env de dos
    líneas no amerita compartir módulo con la CLI de Claude."""
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
    """La variable de entorno gana sobre el .env, para poder probar sin tocarlo."""
    return os.environ.get(clave) or _leer_env().get(clave) or None


def token() -> str | None:
    return _ajuste("NOTION_TOKEN")


def pagina_id() -> str | None:
    """El id de la página «Remi», compartida a mano con la integración."""
    return _ajuste("NOTION_PAGINA_ID")


def vuelta_habilitada() -> bool:
    """Notion solo de ida por defecto (docs/ROBUSTEZ.md): Remi empuja, nunca
    lee ni anota conflictos, salvo `NOTION_VUELTA=1` en `nucleo/.env`."""
    return _ajuste("NOTION_VUELTA") == "1"


class Notion:
    """Lo mínimo que `notion_sync.py` necesita: bases, páginas, consultas."""

    def __init__(self, token: str, *, cliente: httpx.Client | None = None) -> None:
        self._cliente = cliente or httpx.Client(
            base_url=BASE_URL,
            timeout=TIMEOUT_SEGUNDOS,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": VERSION,
                "Content-Type": "application/json",
            },
        )

    def buscar_base(self, padre_id: str, nombre: str) -> str | None:
        """La base de datos hija de `padre_id` que se llama `nombre`, si ya existe.

        `GET /blocks/{id}/children` LISTA los hijos; `POST` en esa misma ruta
        AGREGA bloques nuevos — con POST, Notion devolvía 400 Bad Request
        porque el cuerpo no tenía la forma de un bloque a crear."""
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            datos = self._pedir("GET", f"/blocks/{padre_id}/children", None, params=params)
            for bloque in datos.get("results", []):
                if bloque.get("type") == "child_database" and bloque["child_database"].get("title") == nombre:
                    return bloque["id"]
            if not datos.get("has_more"):
                return None
            cursor = datos.get("next_cursor")

    def crear_base(self, padre_id: str, nombre: str, propiedades: dict[str, Any]) -> str:
        cuerpo = {
            "parent": {"type": "page_id", "page_id": padre_id},
            "title": [{"type": "text", "text": {"content": nombre}}],
            "is_inline": True,
            "properties": propiedades,
        }
        return self._pedir("POST", "/databases", cuerpo)["id"]

    def consultar_base(self, database_id: str) -> list[dict[str, Any]]:
        paginas: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            cuerpo: dict[str, Any] = {"page_size": 100}
            if cursor:
                cuerpo["start_cursor"] = cursor
            datos = self._pedir("POST", f"/databases/{database_id}/query", cuerpo)
            paginas.extend(datos.get("results", []))
            if not datos.get("has_more"):
                return paginas
            cursor = datos.get("next_cursor")

    def crear_pagina(self, database_id: str, propiedades: dict[str, Any]) -> str:
        cuerpo = {"parent": {"database_id": database_id}, "properties": propiedades}
        return self._pedir("POST", "/pages", cuerpo)["id"]

    def actualizar_pagina(self, pagina_id: str, propiedades: dict[str, Any]) -> None:
        self._pedir("PATCH", f"/pages/{pagina_id}", {"properties": propiedades})

    def obtener_pagina(self, pagina_id: str) -> dict[str, Any]:
        return self._pedir("GET", f"/pages/{pagina_id}", None)

    def _pedir(
        self, metodo: str, ruta: str, cuerpo: dict[str, Any] | None, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        respuesta = self._cliente.request(metodo, ruta, json=cuerpo, params=params)
        respuesta.raise_for_status()
        return respuesta.json()


# — Construir y leer propiedades: lo mismo de los dos lados de la API —


def prop_titulo(valor: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": valor[:2000]}}]}


def prop_texto(valor: str) -> dict[str, Any]:
    return {"rich_text": [{"text": {"content": valor[:2000]}}]}


def prop_fecha(valor: date | None) -> dict[str, Any]:
    return {"date": {"start": valor.isoformat()} if valor else None}


def prop_numero(valor: float | None) -> dict[str, Any]:
    return {"number": valor}


def prop_seleccion(valor: str | None) -> dict[str, Any]:
    return {"select": {"name": valor} if valor else None}


def _texto_de(fragmento: dict[str, Any]) -> str:
    """Notion manda `plain_text`; lo que nosotros armamos con `prop_texto`
    solo trae `text.content` — cualquiera de los dos sirve para leer."""
    return fragmento.get("plain_text") or fragmento.get("text", {}).get("content", "")


def leer_titulo(propiedad: dict[str, Any] | None) -> str:
    if not propiedad:
        return ""
    return "".join(_texto_de(t) for t in propiedad.get("title", []))


def leer_texto(propiedad: dict[str, Any] | None) -> str:
    if not propiedad:
        return ""
    return "".join(_texto_de(t) for t in propiedad.get("rich_text", []))


def leer_fecha(propiedad: dict[str, Any] | None) -> str | None:
    if not propiedad or not propiedad.get("date"):
        return None
    return propiedad["date"].get("start")


def leer_numero(propiedad: dict[str, Any] | None) -> float | None:
    if not propiedad:
        return None
    return propiedad.get("number")


def leer_seleccion(propiedad: dict[str, Any] | None) -> str | None:
    if not propiedad or not propiedad.get("select"):
        return None
    return propiedad["select"].get("name")


# — La puerta HTTP: un disparador manual, mismo patrón que entregas.router —

router = APIRouter(prefix="/notion", tags=["notion"])


@router.get("/estado")
def estado() -> dict[str, bool]:
    return {"configurado": token() is not None and pagina_id() is not None}


@router.post("/sincronizar")
def sincronizar_ahora() -> dict[str, Any]:
    """Dispara la ida y vuelta ya mismo, sin esperar al LaunchAgent de los
    15 min. Import adentro: `notion_sync` importa este módulo, y arriba
    rompería el ciclo."""
    import notion_sync

    resumen = notion_sync.sincronizar()
    return resumen.__dict__


if __name__ == "__main__":
    print("configurado" if token() and pagina_id() else "sin configurar", file=sys.stderr)

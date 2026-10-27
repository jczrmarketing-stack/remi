"""Trae lo abierto de «Remi · CRM de vida» (Notion) a conocimiento/vida/crm.md.

Grok Bot y los rituales escriben ahí; este módulo lo vuelve un archivo corto
que `remi_mcp.estado_vivo` suma al estado. Solo lectura de Notion. Sin token
se salta sin ruido (nunca tumba la noche). Los frentes de salud y cuerpo no
se copian: este archivo viaja a cada sesión de Claude.

    cd nucleo && uv run python estado_crm.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(os.environ.get("REMI_RAIZ") or Path(__file__).resolve().parent.parent)
DESTINO = RAIZ / "conocimiento" / "vida" / "crm.md"
FRENTES_FUERA = frozenset({"Salud", "Cuerpo"})
MAXIMO_FILAS = 25
MAXIMO_NOTA = 220


def _texto(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    for clave in ("title", "rich_text"):
        if clave in prop:
            return "".join(f.get("plain_text", "") for f in prop[clave]).strip()
    for clave in ("select", "status"):
        if clave in prop:
            return ((prop[clave] or {}).get("name") or "").strip()
    return ""


def _fila(pagina: dict[str, Any]) -> dict[str, str]:
    p = pagina.get("properties", {})
    return {
        "que": _texto(p.get("Qué")),
        "frente": _texto(p.get("Frente")) or "Sin frente",
        "tipo": _texto(p.get("Tipo")),
        "estado": _texto(p.get("Estado")),
        "paso": _texto(p.get("Paso mínimo")),
        "notas": _texto(p.get("Notas")),
    }


def filtro() -> dict[str, Any]:
    return {
        "and": [
            {"property": "Tipo", "select": {"does_not_equal": "Hallazgo"}},
            {"property": "Estado", "status": {"does_not_equal": "Hecha"}},
            {"property": "Estado", "status": {"does_not_equal": "Soltada"}},
        ]
    }


def render(paginas: list[dict[str, Any]], ahora: datetime) -> str:
    filas = [f for f in map(_fila, paginas) if f["que"] and f["frente"] not in FRENTES_FUERA]
    grupos: dict[str, list[dict[str, str]]] = {}
    for f in filas[:MAXIMO_FILAS]:
        grupos.setdefault(f["frente"], []).append(f)
    salida = [f"---\nactualizado: {ahora.date().isoformat()}\nfuente: Notion CRM de vida\n---", "# Abierto en el CRM"]
    if not grupos:
        salida.append("Nada abierto.")
    for frente, items in grupos.items():
        salida.append(f"## {frente}")
        for f in items:
            linea = f"- {f['que']}"
            if f["paso"]:
                linea += f" → paso: {f['paso']}"
            nota = " ".join(f["notas"].split())
            if nota:
                linea += f" · {nota[:MAXIMO_NOTA]}{'…' if len(nota) > MAXIMO_NOTA else ''}"
            salida.append(linea)
    return "\n".join(salida) + "\n"


def refrescar(ahora: datetime | None = None) -> str:
    """Devuelve 'ok', 'sin token' o 'error: …'. Nunca lanza."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        import notion
        import notion_avisos

        tok = notion.token()
        if not tok:
            return "sin token"
        paginas = notion.Notion(tok).consultar_fuente(notion_avisos.fuente_id(), filtro())
        texto = render(paginas, ahora)
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        tmp = DESTINO.with_suffix(".md.tmp")
        tmp.write_text(texto, encoding="utf-8")
        tmp.replace(DESTINO)
        return "ok"
    except Exception as e:  # noqa: BLE001 — la noche no se cae por esto
        return f"error: {type(e).__name__}"


if __name__ == "__main__":
    resultado = refrescar()
    print(f"[estado_crm] {resultado}")
    sys.exit(0 if resultado in ("ok", "sin token") else 1)

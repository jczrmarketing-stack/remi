"""Reordenador local opcional (F1.5b).

Toma los mejores candidatos de la búsqueda híbrida y los vuelve a ordenar con
un modelo cruzado (consulta + nota juntas). Es lo que más sube la precisión en
las mediciones de Anthropic (−67 % de fallos con contexto + reordenador), pero
cuesta RAM y un modelo descargado, así que:

- está apagado por defecto (`config/mente.json` → reordenador.activar);
- si no está instalado `sentence-transformers` o el modelo falla, devuelve None
  y la búsqueda sigue con el orden híbrido: nunca rompe una consulta;
- `evaluar.py` mide con y sin él; solo se enciende si sube recall@5 sin subir tokens.
"""
from __future__ import annotations

import json
from pathlib import Path

_ARCHIVO = Path(__file__).resolve().parent.parent / "config" / "mente.json"
_MODELO = None
_MODELO_NOMBRE = None


def configuracion() -> dict:
    por_defecto = {"activar": False, "modelo": "BAAI/bge-reranker-v2-m3", "candidatos": 20}
    try:
        por_defecto.update(json.loads(_ARCHIVO.read_text(encoding="utf-8")).get("reordenador", {}))
    except (OSError, ValueError, AttributeError):
        pass
    return por_defecto


def activo() -> bool:
    return bool(configuracion()["activar"])


def _cargar(nombre: str):
    global _MODELO, _MODELO_NOMBRE
    if _MODELO is None or _MODELO_NOMBRE != nombre:
        from sentence_transformers import CrossEncoder  # import tardío: es pesado

        _MODELO = CrossEncoder(nombre)
        _MODELO_NOMBRE = nombre
    return _MODELO


def puntuar(consulta: str, textos: list[str], modelo: str | None = None) -> list[float] | None:
    """Un puntaje por texto, o None si no se pudo (sin modelo, sin librería)."""
    if not textos:
        return []
    try:
        cruzado = _cargar(modelo or configuracion()["modelo"])
        return [float(p) for p in cruzado.predict([(consulta, t) for t in textos])]
    except Exception:  # noqa: BLE001 — cualquier fallo del modelo = sin reordenar
        return None


def reordenar(consulta: str, candidatos: list[tuple[int, str]], modelo: str | None = None) -> list[int] | None:
    """Ids de `candidatos` (id, texto) del más al menos relevante; None si no se pudo."""
    puntos = puntuar(consulta, [texto for _, texto in candidatos], modelo)
    if puntos is None:
        return None
    orden = sorted(range(len(candidatos)), key=lambda i: puntos[i], reverse=True)
    return [candidatos[i][0] for i in orden]

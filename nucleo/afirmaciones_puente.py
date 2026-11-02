"""Puente a las afirmaciones de la bóveda (B2) para `preguntar` y `contradice`.

El código vive en la bóveda (`afirmaciones.py`, solo librería estándar) y esta cabeza lo carga por
ruta hasta que B3 junte todo en un paquete. Reglas: solo LEE (`mode=ro`), y si la bóveda no está
montada, o la base aún no existe, devuelve vacío: `preguntar` nunca se rompe por esto.
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def _raiz_boveda() -> Path | None:
    import donde_boveda
    return donde_boveda.ubicar(os.environ.get("BOVEDA_RAIZ"), marca="afirmaciones.py")


def _modulo():
    raiz = _raiz_boveda()
    if raiz is None:
        return None
    try:
        espec = importlib.util.spec_from_file_location("afirmaciones_boveda", raiz / "afirmaciones.py")
        modulo = importlib.util.module_from_spec(espec)
        espec.loader.exec_module(modulo)  # type: ignore[union-attr]
        return modulo
    except Exception:  # noqa: BLE001 — un archivo roto en la bóveda no tumba a Remi
        return None


def _ro(ruta: Path) -> sqlite3.Connection | None:
    if not ruta.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        return con
    except sqlite3.Error:
        return None


def estado_de(nota_id: str, mente: Path | None = None) -> str:
    """«afirmaciones: 2 vigentes, 1 por verificar (venció 2026-08-31)» o '' si no hay nada que decir."""
    import vida
    modulo, con = _modulo(), _ro((mente or vida.MENTE) / "afirmaciones.db")
    if modulo is None or con is None:
        return ""
    with closing(con):
        try:
            return modulo.resumen_de_nota(con, nota_id)
        except sqlite3.Error:
            return ""


def contradice(texto: str, mente: Path | None = None) -> str:
    import vida
    modulo, con = _modulo(), _ro((mente or vida.MENTE) / "afirmaciones.db")
    if modulo is None:
        return "La bóveda no está montada ahora: no puedo comparar."
    if con is None:
        return "Todavía no hay afirmaciones guardadas (la noche las arma)."
    with closing(con):
        try:
            hallazgos = modulo.contradice(con, texto)
        except sqlite3.Error:
            return "No pude leer las afirmaciones ahora."
    if not hallazgos:
        return "Nada vigente en la mente choca con eso."
    return "Choca con lo que la mente tiene:\n" + "\n".join(
        f"- «{h['texto']}» [{h['nota']}] · {h['desde']} · {h['estado']}" for h in hallazgos)

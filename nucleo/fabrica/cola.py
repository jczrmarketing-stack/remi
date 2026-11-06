"""La cola de la fábrica en SQLite (mejora 4, 6-nov): un espejo del expediente.

La verdad de cada pedido sigue en `fabrica/pedidos/<id>/expediente.md`; aquí queda una
fila por pedido con su estado, en la misma base que `consumo.py` (`db.ruta_db()`,
`REMI_DB_PATH`), para consultarla sin abrir archivos: el panel, `fabrica cola`, la noche.
Reflejar nunca tumba al expediente: si la base no abre, el pedido sigue igual.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ESQUEMA = """
CREATE TABLE IF NOT EXISTS fabrica_cola (
    pedido      TEXT PRIMARY KEY,
    idea        TEXT NOT NULL DEFAULT '',
    base        TEXT NOT NULL DEFAULT 'main',
    estado      TEXT NOT NULL,
    noche       INTEGER NOT NULL DEFAULT 0,
    creado      TEXT NOT NULL DEFAULT '',
    actualizado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fabrica_cola_estado ON fabrica_cola(estado);
"""


def _ruta(ruta: Path | None) -> Path:
    if ruta is not None:
        return Path(ruta)
    import db

    return db.ruta_db()


def _abrir(ruta: Path | None) -> sqlite3.Connection:
    conexion = sqlite3.connect(_ruta(ruta), timeout=5)
    conexion.executescript(ESQUEMA)
    return conexion


def reflejar(meta: dict[str, Any], idea: str, ruta: Path | None = None) -> None:
    try:
        with _abrir(ruta) as conexion:
            conexion.execute(
                "INSERT INTO fabrica_cola (pedido, idea, base, estado, noche, creado, actualizado) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(pedido) DO UPDATE SET idea=excluded.idea, base=excluded.base, estado=excluded.estado, "
                "noche=excluded.noche, actualizado=excluded.actualizado",
                (str(meta.get("pedido", "")), idea[:300], str(meta.get("base") or "main"), str(meta.get("estado", "")),
                 int(meta.get("noche") or 0), str(meta.get("creado", "")),
                 datetime.now(timezone.utc).isoformat(timespec="seconds")))
    except (sqlite3.Error, OSError, ValueError, TypeError):
        pass  # el espejo es mejor esfuerzo: nunca frena un pedido


def listar(ruta: Path | None = None) -> list[dict[str, Any]]:
    try:
        with _abrir(ruta) as conexion:
            conexion.row_factory = sqlite3.Row
            filas = conexion.execute("SELECT * FROM fabrica_cola ORDER BY creado").fetchall()
    except (sqlite3.Error, OSError):
        return []
    return [dict(f) for f in filas]

"""Registro de consumo de `claude -p` (Bloque 0 de la fábrica).

Cada llamada a la CLI de Claude deja una fila en SQLite: qué agente, cuándo,
cuánto tardó, cuántos tokens entraron y salieron, y si terminó bien. Es el
único módulo que sabe hacerlo; los agentes solo llaman a `registrar`.

Reglas:
- El registro NUNCA tumba a quien lo llama: `registrar` atrapa todo.
- La tabla es de este módulo (`CREATE TABLE IF NOT EXISTS`); `db.py` no la
  conoce y el contrato no cambia.
- La base es la de siempre (`db.ruta_db()`, `REMI_DB_PATH`). En pruebas, una
  temporal: nunca el remi.db real.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ESQUEMA = """
CREATE TABLE IF NOT EXISTS consumo_claude (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agente TEXT NOT NULL,
    fecha TEXT NOT NULL,
    duracion_ms INTEGER NOT NULL DEFAULT 0,
    tokens_entrada INTEGER NOT NULL DEFAULT 0,
    tokens_salida INTEGER NOT NULL DEFAULT 0,
    ok INTEGER NOT NULL DEFAULT 0,
    modelo TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_consumo_claude_fecha ON consumo_claude(fecha);
"""

# Si la base está ocupada, el agente no espera por un registro.
ESPERA_SEG = 3


def _ruta(ruta: Path | None) -> Path:
    if ruta is not None:
        return Path(ruta)
    import db

    return db.ruta_db()


def _entero(valor: Any) -> int:
    # bool es int en Python: un `True` perdido no es una cuenta de tokens.
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0 else 0


def _resultado(salida: Any) -> dict[str, Any] | None:
    """El objeto `result` de la CLI, venga como dict ya leído, como el JSON de
    `--output-format json` o como un stream-json (una línea por evento)."""
    if isinstance(salida, dict):
        return salida or None
    if not isinstance(salida, str) or not salida.strip():
        return None
    try:
        datos = json.loads(salida)
    except json.JSONDecodeError:
        datos = None
    if isinstance(datos, dict):
        return datos
    candidatos = datos if isinstance(datos, list) else []
    if datos is None:
        candidatos = []
        for linea in salida.splitlines():
            try:
                candidatos.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    for evento in reversed(candidatos):
        if isinstance(evento, dict) and evento.get("type") == "result":
            return evento
    return None


def _tokens(datos: dict[str, Any]) -> tuple[int, int]:
    """(entrada, salida). Lo leído y escrito en la caché también es entrada:
    la CLI informa `input_tokens` solo con lo no cacheado."""
    uso = datos.get("usage")
    if not isinstance(uso, dict):
        return 0, 0
    entrada = sum(_entero(uso.get(k)) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return entrada, _entero(uso.get("output_tokens"))


def registrar(
    agente: str,
    modelo: str | None,
    segundos: float,
    salida: Any = None,
    returncode: int = 0,
    error: str | None = None,
    ruta: Path | None = None,
    ahora: datetime | None = None,
) -> None:
    """Guarda una fila. `salida` es el stdout de la CLI (o su `result` ya
    leído). `error` explica un fallo que no dejó salida (timeout, sin CLI).
    Nunca levanta una excepción."""
    try:
        datos = _resultado(salida)
        entrada, salida_tokens = _tokens(datos) if datos else (0, 0)
        texto = datos.get("result") if datos else None
        ok = bool(
            datos
            and returncode == 0
            and error is None
            and not datos.get("is_error")
            and isinstance(texto, str)
            and texto.strip()
        )
        if error is None and not ok:
            error = f"la CLI terminó en {returncode}" if returncode != 0 else ("is_error" if datos and datos.get("is_error") else "respuesta vacía o rota")
        fila = (
            str(agente),
            (ahora or datetime.now(timezone.utc)).isoformat(),
            int(max(segundos, 0) * 1000),
            entrada,
            salida_tokens,
            1 if ok else 0,
            modelo,
            None if ok else str(error)[:200],
        )
        conexion = sqlite3.connect(_ruta(ruta), timeout=ESPERA_SEG)
        try:
            conexion.executescript(ESQUEMA)
            conexion.execute(
                "INSERT INTO consumo_claude (agente, fecha, duracion_ms, tokens_entrada, tokens_salida, ok, modelo, error)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                fila,
            )
            conexion.commit()
        finally:
            conexion.close()
    except Exception as exc:  # noqa: BLE001 — el registro jamás tumba a un agente
        try:
            print(f"[consumo] no pude registrar: {type(exc).__name__}: {exc}", file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass

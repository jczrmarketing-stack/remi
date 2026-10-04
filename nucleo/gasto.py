"""Tope de gasto en los motores pagados (B1, docs/PLAN-FINAL.md). Venice y
OpenRouter cobran por token; Groq, Ollama y Claude (por la membresía Max)
no, y no se registran acá. Antes de cada llamada pagada, pensar.py consulta
`excede_tope()`: si ya se pasó, no llama y cae al respaldo gratis (Groq ->
Ollama). Código puro: nunca decide el precio de un modelo que no conoce,
nunca lee datetime.now() (todo recibe `ahora`/`hoy` para que las pruebas
controlen el reloj)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import db

BOGOTA = ZoneInfo("America/Bogota")
RUTA_GASTO_POR_DEFECTO = Path(__file__).resolve().parent / "config" / "gasto.json"
RUTA_MOTORES_POR_DEFECTO = Path(__file__).resolve().parent / "config" / "motores.json"
# Los únicos dos que cobran aparte. Lo que llama decide qué hacer con
# cualquier otro nombre (nunca se inventa un precio).
MOTORES_PAGADOS = ("venice", "openrouter")


def _ruta_gasto() -> Path:
    return Path(os.environ.get("REMI_GASTO") or RUTA_GASTO_POR_DEFECTO)


def _ruta_motores() -> Path:
    return Path(os.environ.get("REMI_MOTORES") or RUTA_MOTORES_POR_DEFECTO)


@dataclass(frozen=True)
class ConfigGasto:
    tope_dia_usd: float
    tope_mes_usd: float
    activo: bool


CONFIG_POR_DEFECTO = ConfigGasto(tope_dia_usd=5.0, tope_mes_usd=50.0, activo=True)


def leer_config() -> ConfigGasto:
    try:
        datos = json.loads(_ruta_gasto().read_text())
    except (OSError, json.JSONDecodeError):
        return CONFIG_POR_DEFECTO
    if not isinstance(datos, dict):
        return CONFIG_POR_DEFECTO
    return ConfigGasto(
        tope_dia_usd=float(datos.get("tope_dia_usd", CONFIG_POR_DEFECTO.tope_dia_usd)),
        tope_mes_usd=float(datos.get("tope_mes_usd", CONFIG_POR_DEFECTO.tope_mes_usd)),
        activo=bool(datos.get("activo", CONFIG_POR_DEFECTO.activo)),
    )


def escribir_config(config: ConfigGasto) -> None:
    ruta = _ruta_gasto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(
            {
                "tope_dia_usd": config.tope_dia_usd,
                "tope_mes_usd": config.tope_mes_usd,
                "activo": config.activo,
            },
            indent=2,
        )
        + "\n"
    )


def _precios() -> dict[str, Any]:
    try:
        datos = json.loads(_ruta_motores().read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    precios = datos.get("precios") if isinstance(datos, dict) else None
    return precios if isinstance(precios, dict) else {}


def calcular_usd(motor: str, modelo: str, tokens_entrada: int, tokens_salida: int) -> float:
    """0.0 si no hay precio para ese motor/modelo en config/motores.json —
    nunca inventa un costo."""
    precio = _precios().get(motor, {}).get(modelo) if isinstance(_precios().get(motor), dict) else None
    if not isinstance(precio, dict):
        return 0.0
    usd_entrada = float(precio.get("usd_1k_entrada", 0.0))
    usd_salida = float(precio.get("usd_1k_salida", 0.0))
    return round((tokens_entrada / 1000) * usd_entrada + (tokens_salida / 1000) * usd_salida, 6)


def registrar(
    motor: str,
    modelo: str,
    tokens_entrada: int,
    tokens_salida: int,
    usd: float | None = None,
    ahora: datetime | None = None,
) -> None:
    usd = calcular_usd(motor, modelo, tokens_entrada, tokens_salida) if usd is None else usd
    ahora = ahora or datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        conexion.execute(
            "INSERT INTO gasto_motor (fecha, motor, modelo, tokens_in, tokens_out, usd) VALUES (?, ?, ?, ?, ?, ?)",
            (ahora.astimezone(timezone.utc).isoformat(), motor, modelo, tokens_entrada, tokens_salida, usd),
        )
        conexion.commit()
    finally:
        conexion.close()


def _inicio_del_dia_utc(hoy: date) -> str:
    local = datetime(hoy.year, hoy.month, hoy.day, tzinfo=BOGOTA)
    return local.astimezone(timezone.utc).isoformat()


def _inicio_del_mes_utc(hoy: date) -> str:
    local = datetime(hoy.year, hoy.month, 1, tzinfo=BOGOTA)
    return local.astimezone(timezone.utc).isoformat()


def _suma_desde(desde_iso: str) -> float:
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT COALESCE(SUM(usd), 0) AS total FROM gasto_motor WHERE fecha >= ?", (desde_iso,)
        ).fetchone()
        return float(fila["total"])
    finally:
        conexion.close()


def gasto_dia_usd(hoy: date | None = None) -> float:
    hoy = hoy or datetime.now(timezone.utc).astimezone(BOGOTA).date()
    return _suma_desde(_inicio_del_dia_utc(hoy))


def gasto_mes_usd(hoy: date | None = None) -> float:
    hoy = hoy or datetime.now(timezone.utc).astimezone(BOGOTA).date()
    return _suma_desde(_inicio_del_mes_utc(hoy))


def excede_tope(hoy: date | None = None) -> bool:
    config = leer_config()
    if not config.activo:
        return False
    return gasto_dia_usd(hoy) >= config.tope_dia_usd or gasto_mes_usd(hoy) >= config.tope_mes_usd


def fraccion_usada(hoy: date | None = None) -> float:
    """La mayor fracción (día o mes) contra su tope — para el aviso del 80%
    de doctor.sh. 0.0 si el tope está apagado o algún tope es 0."""
    config = leer_config()
    if not config.activo:
        return 0.0
    frac_dia = gasto_dia_usd(hoy) / config.tope_dia_usd if config.tope_dia_usd > 0 else 0.0
    frac_mes = gasto_mes_usd(hoy) / config.tope_mes_usd if config.tope_mes_usd > 0 else 0.0
    return max(frac_dia, frac_mes)

"""B5 (docs/PLAN-FINAL.md): avisos que jalan la atención — los únicos tres
con sonido: `terminal_termino` (cierra la sesión de un encargo), `foco_25`
(25 min de bloque) y `desvio` (actividad en otro libro por más de 30 min
con un bloque abierto y fecha prometida). Lo demás, callado (eso ya lo
hace iniciativa.py). Forma L.

El reloj entra siempre como parámetro: nada acá llama a datetime.now()."""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")
RUTA_CONFIG_POR_DEFECTO = Path(__file__).resolve().parent.parent / "config" / "avisos.json"

TIPOS = ("terminal_termino", "foco_25", "desvio")
MINUTOS_FOCO = 25
MINUTOS_DESVIO = 30

ESQUEMA = """
CREATE TABLE IF NOT EXISTS avisos (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    texto TEXT NOT NULL,
    canal TEXT NOT NULL,
    creado TEXT NOT NULL,
    respuesta TEXT,
    -- Revisión de B5: qué bloque o sesión ya avisó (el id de `sesiones` o
    -- `trabajo_claude`) — para que foco_25/desvio no se repitan mientras
    -- el mismo bloque sigue abierto. NULL en terminal_termino.
    ref TEXT
);
"""


def _preparar(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA)


@dataclass(frozen=True)
class ConfigAvisos:
    suenan: tuple[str, ...]
    max_dia: int
    entre_min: int
    noche: tuple[int, int]
    telegram: bool


CONFIG_POR_DEFECTO = ConfigAvisos(suenan=TIPOS, max_dia=5, entre_min=45, noche=(23, 7), telegram=True)


def _ruta_config() -> Path:
    return Path(os.environ.get("REMI_AVISOS") or RUTA_CONFIG_POR_DEFECTO)


def leer_config() -> ConfigAvisos:
    try:
        datos = json.loads(_ruta_config().read_text())
    except (OSError, json.JSONDecodeError):
        return CONFIG_POR_DEFECTO
    if not isinstance(datos, dict):
        return CONFIG_POR_DEFECTO
    noche = datos.get("noche", list(CONFIG_POR_DEFECTO.noche))
    return ConfigAvisos(
        suenan=tuple(datos.get("suenan", CONFIG_POR_DEFECTO.suenan)),
        max_dia=int(datos.get("max_dia", CONFIG_POR_DEFECTO.max_dia)),
        entre_min=int(datos.get("entre_min", CONFIG_POR_DEFECTO.entre_min)),
        noche=(int(noche[0]), int(noche[1])) if isinstance(noche, list) and len(noche) == 2 else CONFIG_POR_DEFECTO.noche,
        telegram=bool(datos.get("telegram", CONFIG_POR_DEFECTO.telegram)),
    )


@dataclass(frozen=True)
class Aviso:
    id: UUID
    tipo: str
    texto: str
    canal: str
    creado: datetime
    respuesta: str | None
    ref: str | None = None


def _fila_a_aviso(fila: sqlite3.Row) -> Aviso:
    creado = datetime.fromisoformat(fila["creado"])
    return Aviso(
        id=UUID(fila["id"]), tipo=fila["tipo"], texto=fila["texto"], canal=fila["canal"], creado=creado,
        respuesta=fila["respuesta"], ref=fila["ref"] if "ref" in fila.keys() else None,
    )


def _hoy(momento: datetime) -> str:
    return momento.astimezone(BOGOTA).date().isoformat()


def _en_noche(momento: datetime, noche: tuple[int, int]) -> bool:
    hora = momento.astimezone(BOGOTA).hour
    inicio, fin = noche
    if inicio > fin:  # p. ej. 23 a 7: cruza medianoche
        return hora >= inicio or hora < fin
    return inicio <= hora < fin


def _silenciado_hoy(conexion: sqlite3.Connection, tipo: str, ahora: datetime) -> bool:
    """«Ahora no» calla ESE tipo el resto del día de hoy (Bogotá) — y
    solo ese tipo, nunca los demás."""
    hoy = _hoy(ahora)
    filas = conexion.execute("SELECT creado FROM avisos WHERE tipo = ? AND respuesta = 'ahora_no'", (tipo,)).fetchall()
    return any(_hoy(datetime.fromisoformat(f["creado"])) == hoy for f in filas)


def _presupuesto_ok(conexion: sqlite3.Connection, config: ConfigAvisos, ahora: datetime) -> bool:
    if _en_noche(ahora, config.noche):
        return False
    filas = conexion.execute("SELECT creado FROM avisos ORDER BY creado DESC").fetchall()
    if not filas:
        return True
    hoy = _hoy(ahora)
    de_hoy = sum(1 for f in filas if _hoy(datetime.fromisoformat(f["creado"])) == hoy)
    if de_hoy >= config.max_dia:
        return False
    ultimo = datetime.fromisoformat(filas[0]["creado"])
    return ahora - ultimo >= timedelta(minutes=config.entre_min)


def _ya_avisado_ese_bloque(conexion: sqlite3.Connection, tipo: str, ref: str) -> bool:
    """Revisión de B5: foco_25 y desvio avisan UNA vez por bloque/sesión
    (su `ref`), no cada `entre_min` mientras siga abierto — y de paso,
    una sesión de trabajo_claude huérfana (el gancho nunca cerró `fin`)
    tampoco vuelve a avisar día tras día."""
    fila = conexion.execute("SELECT 1 FROM avisos WHERE tipo = ? AND ref = ? LIMIT 1", (tipo, ref)).fetchone()
    return fila is not None


def registrar(
    conexion: sqlite3.Connection, tipo: str, texto: str, canal: str, ahora: datetime, ref: str | None = None
) -> Aviso | None:
    """Crea el aviso SOLO si el presupuesto lo permite, ese tipo no está
    silenciado hoy, y (con `ref`) ese mismo bloque no avisó ya. None si no
    sale — nunca se fuerza ni se avisa dos veces por lo mismo."""
    _preparar(conexion)
    config = leer_config()
    if tipo not in config.suenan:
        return None
    if _silenciado_hoy(conexion, tipo, ahora):
        return None
    if ref is not None and _ya_avisado_ese_bloque(conexion, tipo, ref):
        return None
    if not _presupuesto_ok(conexion, config, ahora):
        return None
    aviso = Aviso(id=uuid4(), tipo=tipo, texto=texto, canal=canal, creado=ahora, respuesta=None, ref=ref)
    conexion.execute(
        "INSERT INTO avisos (id, tipo, texto, canal, creado, respuesta, ref) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(aviso.id), aviso.tipo, aviso.texto, aviso.canal, aviso.creado.isoformat(), aviso.respuesta, aviso.ref),
    )
    conexion.commit()
    return aviso


def responder(conexion: sqlite3.Connection, aviso_id: UUID, respuesta: str) -> Aviso | None:
    """«volver» o «ahora_no». Ahora no no deja ningún contador (ley 3):
    solo calla ESE tipo el resto de hoy, vía `_silenciado_hoy`."""
    _preparar(conexion)
    fila = conexion.execute("SELECT * FROM avisos WHERE id = ?", (str(aviso_id),)).fetchone()
    if fila is None:
        return None
    conexion.execute("UPDATE avisos SET respuesta = ? WHERE id = ?", (respuesta, str(aviso_id)))
    conexion.commit()
    return _fila_a_aviso(conexion.execute("SELECT * FROM avisos WHERE id = ?", (str(aviso_id),)).fetchone())


def listar_de_hoy(conexion: sqlite3.Connection, ahora: datetime) -> list[Aviso]:
    """Para el panel — nunca se muestra como contador (ley 4), solo se usa
    para ver qué pasó hoy."""
    _preparar(conexion)
    hoy = _hoy(ahora)
    filas = conexion.execute("SELECT * FROM avisos ORDER BY creado").fetchall()
    return [_fila_a_aviso(f) for f in filas if _hoy(datetime.fromisoformat(f["creado"])) == hoy]


def pendiente(conexion: sqlite3.Connection) -> Aviso | None:
    """El último aviso sin respuesta — lo que la ventanita muestra."""
    _preparar(conexion)
    fila = conexion.execute(
        "SELECT * FROM avisos WHERE respuesta IS NULL ORDER BY creado DESC LIMIT 1"
    ).fetchone()
    return _fila_a_aviso(fila) if fila is not None else None


# — Las dos reglas que se miran (encuesta periódica, como iniciativa.py) —
# `terminal_termino` no está acá: nace del evento mismo (trabajo.py, al
# cerrar una sesión nacida de un encargo), no de mirar el reloj.


def _regla_foco_25(conexion: sqlite3.Connection, ahora: datetime) -> tuple[str, str, str] | None:
    fila = conexion.execute(
        "SELECT id, inicio, app_contexto FROM sesiones WHERE fin IS NULL ORDER BY inicio DESC LIMIT 1"
    ).fetchone()
    if fila is None:
        return None
    inicio = datetime.fromisoformat(fila["inicio"])
    if (ahora - inicio).total_seconds() / 60 < MINUTOS_FOCO:
        return None
    tema = fila["app_contexto"]
    return "foco_25", f"25 min de bloque{f' en {tema}' if tema else ''}. ¿Seguimos?", f"sesion:{fila['id']}"


def _regla_desvio(conexion: sqlite3.Connection, ahora: datetime) -> tuple[str, str, str] | None:
    fila = conexion.execute(
        "SELECT s.app_contexto AS tema, t.fecha_limite AS fecha_limite FROM sesiones s "
        "JOIN tareas t ON t.id = s.tarea_id WHERE s.fin IS NULL ORDER BY s.inicio DESC LIMIT 1"
    ).fetchone()
    if fila is None or fila["fecha_limite"] is None or not fila["tema"]:
        return None
    tema_bloque = fila["tema"]
    limite = ahora - timedelta(minutes=MINUTOS_DESVIO)
    otra = conexion.execute(
        "SELECT session_id, tema, inicio FROM trabajo_claude WHERE fin IS NULL AND tema IS NOT NULL AND tema != ? "
        "ORDER BY inicio ASC LIMIT 1",
        (tema_bloque,),
    ).fetchone()
    if otra is None:
        return None
    if datetime.fromisoformat(otra["inicio"]) > limite:
        return None
    return "desvio", f"Lleva un rato en {otra['tema']} con {tema_bloque} prometido. ¿Volvemos?", f"claude:{otra['session_id']}"


_REGLAS = (_regla_foco_25, _regla_desvio)


def evaluar(conexion: sqlite3.Connection, ahora: datetime, canal: str = "ventanita") -> Aviso | None:
    """El primer candidato de las reglas de reloj que de verdad sale —
    presupuesto, silencio, noche y «ya avisó este bloque» ya filtrados
    por `registrar`."""
    for regla in _REGLAS:
        candidato = regla(conexion, ahora)
        if candidato is None:
            continue
        tipo, texto, ref = candidato
        aviso = registrar(conexion, tipo, texto, canal, ahora, ref=ref)
        if aviso is not None:
            return aviso
    return None

"""El motor de iniciativa (Biblia Parte III «el que sabe cuándo», ley 6).

Sin IA: cada regla mira el estado real y devuelve una voz o None. El
presupuesto de silencio decide si esa voz nace como Nudge de verdad: como
mucho 5 por día, 45 min entre dos, ninguno mientras hay una sesión de
Claude Code abierta (`trabajo_claude`) — salvo «rumbo», que sí interrumpe.

El reloj entra siempre como parámetro (`ahora`): nada acá adentro llama a
`datetime.now()`, para que las pruebas lo controlen del todo.

`entregas.proyecto_id` (contrato) todavía no está atado a ningún Proyecto
real — no existe esa tabla en el núcleo. La regla «rumbo» lo usa tal cual,
como si fuera el `tema` del libro (el mismo texto que guarda
`sesiones.app_contexto`), hasta que exista un puente mejor. Documentado en
docs/BITACORA.md como decisión a revisar.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import bandeja
from modelos import Nudge

BOGOTA = ZoneInfo("America/Bogota")

MAXIMO_NUDGES_POR_DIA = 5
MINUTOS_ENTRE_NUDGES = 45
MINUTOS_BLOQUE_LARGO = 90
HORA_DE_ENCOGER = 22  # 22:00, hora de Bogotá
HORAS_RUMBO = 24
HORAS_SILENCIO_AHORA_NO = 2
MAX_PALABRAS_VOZ = 25

Tipo = Literal["cuerpo", "ritual", "encoger", "rumbo"]
Respuesta = Literal["listo", "ahora_no"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS iniciativa_nudges (
    nudge_id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    creado_en TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_iniciativa_nudges_creado_en ON iniciativa_nudges(creado_en);

CREATE TABLE IF NOT EXISTS iniciativa_silencios (
    tipo TEXT PRIMARY KEY,
    hasta TEXT NOT NULL
);
"""


def _preparar(conexion: sqlite3.Connection) -> None:
    """IF NOT EXISTS lo hace barato llamarlo siempre: no hace falta la
    cache por-archivo que usa db.py (eso es de otra tarea)."""
    conexion.executescript(ESQUEMA)


def _hoy(momento: datetime) -> str:
    """La fecha en Bogotá: el mismo corte de «hoy» que usa trabajo._lunes."""
    return momento.astimezone(BOGOTA).date().isoformat()


def _formato_duracion(minutos: int) -> str:
    """Mismo formato que servidor.formatear_duracion — duplicado a
    propósito para no importar servidor.py desde acá (servidor.py importa
    este módulo para sus rutas; importar al revés sería un ciclo)."""
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto:02d}" if resto else f"{horas} h"


def _recortar(voz: str) -> str:
    palabras = voz.split()
    if len(palabras) <= MAX_PALABRAS_VOZ:
        return voz
    return " ".join(palabras[: MAX_PALABRAS_VOZ - 1]) + "…"


# — El presupuesto de silencio —


def _presupuesto_ok(conexion: sqlite3.Connection, ahora: datetime) -> bool:
    filas = conexion.execute(
        "SELECT creado_en FROM iniciativa_nudges ORDER BY creado_en DESC"
    ).fetchall()
    if not filas:
        return True
    hoy = _hoy(ahora)
    de_hoy = sum(1 for f in filas if _hoy(datetime.fromisoformat(f["creado_en"])) == hoy)
    if de_hoy >= MAXIMO_NUDGES_POR_DIA:
        return False
    ultimo = datetime.fromisoformat(filas[0]["creado_en"])
    return ahora - ultimo >= timedelta(minutes=MINUTOS_ENTRE_NUDGES)


def _silenciado(conexion: sqlite3.Connection, tipo: str, ahora: datetime) -> bool:
    fila = conexion.execute(
        "SELECT hasta FROM iniciativa_silencios WHERE tipo = ?", (tipo,)
    ).fetchone()
    return fila is not None and ahora < datetime.fromisoformat(fila["hasta"])


def _hay_sesion_claude_abierta(conexion: sqlite3.Connection) -> bool:
    fila = conexion.execute("SELECT 1 FROM trabajo_claude WHERE fin IS NULL LIMIT 1").fetchone()
    return fila is not None


def silenciar(conexion: sqlite3.Connection, tipo: str, ahora: datetime) -> None:
    """«Ahora no»: esa regla no vuelve a sonar por HORAS_SILENCIO_AHORA_NO."""
    _preparar(conexion)
    hasta = ahora + timedelta(hours=HORAS_SILENCIO_AHORA_NO)
    conexion.execute(
        "INSERT INTO iniciativa_silencios (tipo, hasta) VALUES (?, ?) "
        "ON CONFLICT(tipo) DO UPDATE SET hasta = excluded.hasta",
        (tipo, hasta.isoformat()),
    )
    conexion.commit()


# — Las reglas: cada una devuelve una voz, o None si no aplica —


def _regla_rumbo(conexion: sqlite3.Connection, ahora: datetime) -> str | None:
    fila_sesion = conexion.execute(
        "SELECT app_contexto FROM sesiones WHERE fin IS NULL ORDER BY inicio DESC LIMIT 1"
    ).fetchone()
    tema_actual = fila_sesion["app_contexto"] if fila_sesion else None
    if not tema_actual:
        return None
    limite = ahora + timedelta(hours=HORAS_RUMBO)
    filas = conexion.execute(
        "SELECT cliente, proyecto_id FROM entregas WHERE estado = 'camino' AND fecha >= ? AND fecha <= ?",
        (ahora.isoformat(), limite.isoformat()),
    ).fetchall()
    for fila in filas:
        tema_entrega = str(fila["proyecto_id"] or "")
        if tema_entrega and tema_entrega != tema_actual:
            return f"Mañana entregas {fila['cliente']}. ¿Seguimos en {tema_actual} o cambiamos?"
    return None


def _regla_cuerpo(conexion: sqlite3.Connection, ahora: datetime) -> str | None:
    fila = conexion.execute(
        "SELECT inicio, app_contexto FROM sesiones WHERE fin IS NULL ORDER BY inicio DESC LIMIT 1"
    ).fetchone()
    if fila is None:
        return None
    inicio = datetime.fromisoformat(fila["inicio"])
    minutos = (ahora - inicio).total_seconds() / 60
    if minutos <= MINUTOS_BLOQUE_LARGO:
        return None
    tema = fila["app_contexto"] or "esto"
    return f"Llevas {_formato_duracion(round(minutos))} en {tema}. ¿Sigue?"


def _regla_ritual(conexion: sqlite3.Connection, ahora: datetime) -> str | None:
    frias = [idea for idea, fria in bandeja.listar_abiertas(conexion, ahora) if fria]
    if not frias:
        return None
    hoy = _hoy(ahora)
    ya_hubo = conexion.execute(
        "SELECT creado_en FROM iniciativa_nudges WHERE tipo = 'ritual'"
    ).fetchall()
    if any(_hoy(datetime.fromisoformat(f["creado_en"])) == hoy for f in ya_hubo):
        return None
    return f"Hay {len(frias)} ideas frías. ¿Las miramos 2 minutos?"


def _regla_encoger(conexion: sqlite3.Connection, ahora: datetime) -> str | None:
    if ahora.astimezone(BOGOTA).hour < HORA_DE_ENCOGER:
        return None
    fila = conexion.execute("SELECT 1 FROM sesiones WHERE fin IS NULL LIMIT 1").fetchone()
    if fila is None:
        return None
    return "Es tarde. ¿Cerramos con un paso mínimo?"


_REGLAS: tuple[tuple[Tipo, Callable[[sqlite3.Connection, datetime], str | None]], ...] = (
    ("rumbo", _regla_rumbo),
    ("cuerpo", _regla_cuerpo),
    ("ritual", _regla_ritual),
    ("encoger", _regla_encoger),
)


@dataclass(frozen=True)
class Candidato:
    tipo: Tipo
    voz: str


def evaluar(conexion: sqlite3.Connection, ahora: datetime) -> Candidato | None:
    """La primera regla que suena, respetando presupuesto, silencios y la
    sesión de Claude Code abierta. None si nada aplica."""
    _preparar(conexion)
    if not _presupuesto_ok(conexion, ahora):
        return None
    sesion_abierta = _hay_sesion_claude_abierta(conexion)
    for tipo, regla in _REGLAS:
        if _silenciado(conexion, tipo, ahora):
            continue
        if sesion_abierta and tipo != "rumbo":
            continue
        voz = regla(conexion, ahora)
        if voz is not None:
            return Candidato(tipo=tipo, voz=_recortar(voz))
    return None


def registrar(conexion: sqlite3.Connection, nudge_id: UUID, tipo: Tipo, ahora: datetime) -> None:
    """El rastro que usa el presupuesto del día. No duplica el contrato:
    `nudges` sigue siendo la única fuente para tipo/voz/respuesta."""
    _preparar(conexion)
    conexion.execute(
        "INSERT INTO iniciativa_nudges (nudge_id, tipo, creado_en) VALUES (?, ?, ?)",
        (str(nudge_id), tipo, ahora.isoformat()),
    )
    conexion.commit()


# — Lo que usan las rutas de servidor.py (tarea 3) —


def _fila_a_nudge(fila: sqlite3.Row) -> Nudge:
    return Nudge(
        id=UUID(fila["id"]),
        tipo=fila["tipo"],
        voz=fila["voz"],
        salida_amable=bool(fila["salida_amable"]),
        respuesta=fila["respuesta"],
    )


def pendiente_o_nuevo(conexion: sqlite3.Connection, ahora: datetime) -> Nudge | None:
    """El pendiente sin respuesta más viejo, o uno nuevo si el motor lo
    hace nacer, o None. Nunca dos pendientes a la vez: si ya hay uno sin
    responder, el motor ni se corre."""
    _preparar(conexion)
    fila = conexion.execute(
        """
        SELECT n.* FROM nudges n
        JOIN iniciativa_nudges i ON i.nudge_id = n.id
        WHERE n.respuesta IS NULL
        ORDER BY i.creado_en ASC
        LIMIT 1
        """
    ).fetchone()
    if fila is not None:
        return _fila_a_nudge(fila)

    candidato = evaluar(conexion, ahora)
    if candidato is None:
        return None

    nudge = Nudge(id=uuid4(), tipo=candidato.tipo, voz=candidato.voz, salida_amable=True, respuesta=None)
    conexion.execute(
        "INSERT INTO nudges (id, tipo, voz, salida_amable, respuesta) VALUES (?, ?, ?, ?, ?)",
        (str(nudge.id), nudge.tipo, nudge.voz, int(nudge.salida_amable), None),
    )
    conexion.commit()
    registrar(conexion, nudge.id, candidato.tipo, ahora)
    return nudge


def responder(conexion: sqlite3.Connection, nudge_id: UUID, respuesta: Respuesta, ahora: datetime) -> Nudge | None:
    """Idempotente: responder dos veces no cambia nada la segunda vez.
    None si ese nudge no existe."""
    _preparar(conexion)
    fila = conexion.execute("SELECT * FROM nudges WHERE id = ?", (str(nudge_id),)).fetchone()
    if fila is None:
        return None
    if fila["respuesta"] is not None:
        return _fila_a_nudge(fila)

    conexion.execute("UPDATE nudges SET respuesta = ? WHERE id = ?", (respuesta, str(nudge_id)))
    conexion.commit()
    if respuesta == "ahora_no":
        silenciar(conexion, str(fila["tipo"]), ahora)
    nueva = conexion.execute("SELECT * FROM nudges WHERE id = ?", (str(nudge_id),)).fetchone()
    assert nueva is not None
    return _fila_a_nudge(nueva)

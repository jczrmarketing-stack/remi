"""SQLite: fuente de verdad de Remi. remi.db nunca va al repo (ver .gitignore)."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from modelos import Idea, Memoria, Sesion, Tarea

RUTA_DB_POR_DEFECTO = Path(__file__).resolve().parent / "remi.db"


def ruta_db() -> Path:
    """La base, resuelta al conectar y no al importar. Antes quedaba fija
    en el import, y una prueba heredaba la base temporal de otra: los turnos
    de una conversación se filtraban en la siguiente (29/09, Fase 3a)."""
    return Path(os.environ.get("REMI_DB_PATH") or RUTA_DB_POR_DEFECTO)


# Compatibilidad: quien lo lea obtiene la ruta de este momento.
RUTA_DB = ruta_db()

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tareas (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    proyecto_id TEXT,
    estado TEXT NOT NULL,
    paso_minimo TEXT NOT NULL,
    estimado_min INTEGER,
    real_min INTEGER,
    compartible INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sesiones (
    id TEXT PRIMARY KEY,
    tarea_id TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT,
    real_min INTEGER NOT NULL,
    app_contexto TEXT,
    FOREIGN KEY (tarea_id) REFERENCES tareas(id)
);

CREATE INDEX IF NOT EXISTS idx_sesiones_tarea_id ON sesiones(tarea_id);

CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY,
    texto TEXT NOT NULL,
    origen TEXT NOT NULL,
    creada_en TEXT NOT NULL,
    enfria_hasta TEXT NOT NULL,
    estado TEXT NOT NULL,
    problema_vision INTEGER
);

CREATE TABLE IF NOT EXISTS nudges (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    voz TEXT NOT NULL,
    salida_amable INTEGER NOT NULL,
    respuesta TEXT
);

-- El estante: lo que Remi sabe. `cuerpo` es lo largo y solo se lee cuando
-- hace falta; el índice (titulo/resumen) es lo que vive siempre en la mente.
CREATE TABLE IF NOT EXISTS memoria (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    resumen TEXT NOT NULL,
    tema TEXT NOT NULL,
    fecha TEXT NOT NULL,
    cuerpo TEXT NOT NULL,
    fuente TEXT NOT NULL,
    -- Palabras clave (3–6, separadas por coma) y nivel de detalle 0–3
    -- (ARQUITECTURA-CEREBRO §2). Nulos hasta que algo los complete.
    claves TEXT,
    nivel INTEGER
);

CREATE INDEX IF NOT EXISTS idx_memoria_fecha ON memoria(fecha);
CREATE INDEX IF NOT EXISTS idx_memoria_tema ON memoria(tema);

-- La conversación: lo que dijo cada uno, en orden. Remi recuerda la última
-- hora; pasada, la conversación es nueva. (Lo que vale guardar de verdad
-- va al estante; esto es solo el hilo.)
CREATE TABLE IF NOT EXISTS turnos (
    id TEXT PRIMARY KEY,
    rol TEXT NOT NULL,
    texto TEXT NOT NULL,
    fecha TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_turnos_fecha ON turnos(fecha);

-- Una conversación: arranca con un turno y termina tras 60 min sin turnos.
-- Lleva un resumen vivo de lo que ya salió de los últimos 10 turnos
-- literales (ARQUITECTURA-CEREBRO §5): se resume, nunca se corta.
CREATE TABLE IF NOT EXISTS conversaciones (
    id TEXT PRIMARY KEY,
    inicio TEXT NOT NULL,
    ultimo TEXT NOT NULL,
    resumen TEXT NOT NULL DEFAULT '',
    resumidos INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entregas (
    id TEXT PRIMARY KEY,
    cliente TEXT NOT NULL,
    proyecto_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    monto REAL,
    estado TEXT NOT NULL,
    compartible INTEGER NOT NULL
);

-- Lo que las herramientas avisan solas (3d): un commit, un arranque o un
-- cierre de sesión. tema es null cuando la carpeta no tiene libro.
CREATE TABLE IF NOT EXISTS trabajo_eventos (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    ruta TEXT NOT NULL,
    tema TEXT,
    datos TEXT NOT NULL,
    fecha TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trabajo_eventos_fecha ON trabajo_eventos(fecha);

-- Commits que todavía no entraron al Estado del libro. `incluido` pasa a 1
-- cuando esa tanda ya se escribió. El tope de 10 min vive en trabajo_estado_en.
CREATE TABLE IF NOT EXISTS trabajo_commits (
    id TEXT PRIMARY KEY,
    tema TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    rama TEXT NOT NULL,
    archivos TEXT NOT NULL,
    fecha TEXT NOT NULL,
    incluido INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_trabajo_commits_tema ON trabajo_commits(tema, incluido);

CREATE TABLE IF NOT EXISTS trabajo_estado_en (
    tema TEXT PRIMARY KEY,
    fecha TEXT NOT NULL
);

-- Sesiones de Claude Code, para el tiempo de la semana. Sin fila de
-- inicio no se inventa una duración aunque llegue el cierre.
CREATE TABLE IF NOT EXISTS trabajo_claude (
    session_id TEXT PRIMARY KEY,
    tema TEXT,
    ruta TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT
);

CREATE INDEX IF NOT EXISTS idx_trabajo_claude_tema ON trabajo_claude(tema);
"""


_rutas_con_esquema_listo: set[str] = set()


def inicializar_esquema(ruta: Path | None = None) -> None:
    """El CREATE TABLE/INDEX corre una sola vez por archivo, no en cada
    conectar() — PRAGMA foreign_keys en cambio es por-conexión en SQLite y
    hay que activarlo siempre, eso sí lo hace conectar()."""
    ruta = ruta_db() if ruta is None else ruta
    clave = str(ruta)
    if clave in _rutas_con_esquema_listo:
        return
    conexion = sqlite3.connect(ruta)
    try:
        conexion.executescript(ESQUEMA)
        _migrar(conexion)
        conexion.commit()
    finally:
        conexion.close()
    _rutas_con_esquema_listo.add(clave)


# Columnas que llegaron después de crear la tabla. CREATE TABLE IF NOT
# EXISTS no las agrega a una base que ya existía: se agregan acá, una vez.
_COLUMNAS_NUEVAS = (
    ("memoria", "claves", "TEXT"),
    ("memoria", "nivel", "INTEGER"),
    ("turnos", "conversacion_id", "TEXT"),
)


def _migrar(conexion: sqlite3.Connection) -> None:
    for tabla, columna, tipo in _COLUMNAS_NUEVAS:
        existentes = {fila[1] for fila in conexion.execute(f"PRAGMA table_info({tabla})")}
        if columna not in existentes:
            conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = ruta_db() if ruta is None else ruta
    inicializar_esquema(ruta)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_tarea(conexion: sqlite3.Connection, tarea: Tarea) -> None:
    conexion.execute(
        """
        INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(tarea.id),
            tarea.titulo,
            str(tarea.proyecto_id) if tarea.proyecto_id else None,
            tarea.estado,
            tarea.paso_minimo,
            tarea.estimado_min,
            tarea.real_min,
            int(tarea.compartible),
        ),
    )
    conexion.commit()


def _fila_a_tarea(fila: sqlite3.Row) -> Tarea:
    return Tarea(
        id=UUID(fila["id"]),
        titulo=fila["titulo"],
        proyecto_id=UUID(fila["proyecto_id"]) if fila["proyecto_id"] else None,
        estado=fila["estado"],
        paso_minimo=fila["paso_minimo"],
        estimado_min=fila["estimado_min"],
        real_min=fila["real_min"],
        compartible=bool(fila["compartible"]),
    )


def actualizar_paso_minimo(
    conexion: sqlite3.Connection, tarea_id: UUID, paso_minimo: str
) -> Tarea | None:
    """None si no existe esa tarea."""
    conexion.execute(
        "UPDATE tareas SET paso_minimo = ? WHERE id = ?", (paso_minimo, str(tarea_id))
    )
    conexion.commit()
    fila = conexion.execute("SELECT * FROM tareas WHERE id = ?", (str(tarea_id),)).fetchone()
    return _fila_a_tarea(fila) if fila else None


def actualizar_estado_tarea(
    conexion: sqlite3.Connection, tarea_id: UUID, estado: str
) -> Tarea | None:
    """None si no existe esa tarea. El estado ya viene validado contra el
    contrato por Pydantic antes de llegar acá (Literal en el endpoint)."""
    conexion.execute("UPDATE tareas SET estado = ? WHERE id = ?", (estado, str(tarea_id)))
    conexion.commit()
    fila = conexion.execute("SELECT * FROM tareas WHERE id = ?", (str(tarea_id),)).fetchone()
    return _fila_a_tarea(fila) if fila else None


def leer_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> Tarea | None:
    fila = conexion.execute("SELECT * FROM tareas WHERE id = ?", (str(tarea_id),)).fetchone()
    return _fila_a_tarea(fila) if fila else None


def listar_tareas_hoy(conexion: sqlite3.Connection) -> list[Tarea]:
    filas = conexion.execute(
        "SELECT * FROM tareas WHERE estado = 'hoy' ORDER BY rowid"
    ).fetchall()
    return [_fila_a_tarea(fila) for fila in filas]


# — La Bandeja: lo suelto entra acá y enfría 48 h (ley 6) —


def crear_idea(conexion: sqlite3.Connection, idea: Idea) -> None:
    conexion.execute(
        """
        INSERT INTO ideas (id, texto, origen, creada_en, enfria_hasta, estado, problema_vision)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(idea.id),
            idea.texto,
            idea.origen,
            idea.creada_en.isoformat(),
            idea.enfria_hasta.isoformat(),
            idea.estado,
            idea.problema_vision,
        ),
    )
    conexion.commit()


def _fila_a_idea(fila: sqlite3.Row) -> Idea:
    return Idea(
        id=UUID(fila["id"]),
        texto=fila["texto"],
        origen=fila["origen"],
        creada_en=fila["creada_en"],
        enfria_hasta=fila["enfria_hasta"],
        estado=fila["estado"],
        problema_vision=fila["problema_vision"],
    )


def listar_ideas(conexion: sqlite3.Connection) -> list[Idea]:
    """Lo que está enfriando, lo más nuevo primero."""
    filas = conexion.execute("SELECT * FROM ideas ORDER BY creada_en DESC").fetchall()
    return [_fila_a_idea(fila) for fila in filas]


def crear_sesion(conexion: sqlite3.Connection, sesion: Sesion) -> None:
    conexion.execute(
        """
        INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(sesion.id),
            str(sesion.tarea_id),
            sesion.inicio.isoformat(),
            sesion.fin.isoformat() if sesion.fin else None,
            sesion.real_min,
            sesion.app_contexto,
        ),
    )
    conexion.commit()


def _fila_a_sesion(fila: sqlite3.Row) -> Sesion:
    return Sesion(
        id=UUID(fila["id"]),
        tarea_id=UUID(fila["tarea_id"]),
        inicio=fila["inicio"],
        fin=fila["fin"],
        real_min=fila["real_min"],
        app_contexto=fila["app_contexto"],
    )


def listar_sesiones_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> list[Sesion]:
    filas = conexion.execute(
        "SELECT * FROM sesiones WHERE tarea_id = ? ORDER BY inicio", (str(tarea_id),)
    ).fetchall()
    return [_fila_a_sesion(fila) for fila in filas]


def listar_sesiones_cerradas_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> list[Sesion]:
    filas = conexion.execute(
        "SELECT * FROM sesiones WHERE tarea_id = ? AND fin IS NOT NULL ORDER BY inicio",
        (str(tarea_id),),
    ).fetchall()
    return [_fila_a_sesion(fila) for fila in filas]


def ultima_sesion_cerrada_min(conexion: sqlite3.Connection, tarea_id: UUID) -> int | None:
    """El dato que pide la ley 1: cuánto tardó la última vez. None si la
    tarea nunca tuvo una sesión cerrada — no hay de dónde sacarlo."""
    fila = conexion.execute(
        "SELECT real_min FROM sesiones WHERE tarea_id = ? AND fin IS NOT NULL "
        "ORDER BY fin DESC LIMIT 1",
        (str(tarea_id),),
    ).fetchone()
    return fila["real_min"] if fila else None


def sesion_abierta_de_tarea(conexion: sqlite3.Connection, tarea_id: UUID) -> UUID | None:
    fila = conexion.execute(
        "SELECT id FROM sesiones WHERE tarea_id = ? AND fin IS NULL ORDER BY inicio DESC LIMIT 1",
        (str(tarea_id),),
    ).fetchone()
    return UUID(fila["id"]) if fila else None


def cerrar_sesion_en_cero(conexion: sqlite3.Connection, sesion_id: UUID) -> Sesion | None:
    """Cierra una sesión vieja sin inventarle duración. Para las que
    quedaron colgadas de otro día: nadie estuvo doce horas en eso, y un
    número inventado envenena el historial en el que se apoya la ley 1."""
    fila = conexion.execute(
        "SELECT * FROM sesiones WHERE id = ?", (str(sesion_id),)
    ).fetchone()
    if fila is None or fila["fin"] is not None:
        return None
    conexion.execute(
        "UPDATE sesiones SET fin = ?, real_min = 0 WHERE id = ?",
        (fila["inicio"], str(sesion_id)),
    )
    conexion.commit()
    return _fila_a_sesion(
        conexion.execute("SELECT * FROM sesiones WHERE id = ?", (str(sesion_id),)).fetchone()
    )


def ultima_sesion_cerrada(conexion: sqlite3.Connection) -> Sesion | None:
    """El último bloque que se midió de verdad, sea de la tarea que sea.
    Es lo que el reposo muestra como «la última vez»: un dato medido, no un
    reloj. None si todavía no se cerró ninguno — no se inventa."""
    fila = conexion.execute(
        "SELECT * FROM sesiones WHERE fin IS NOT NULL ORDER BY fin DESC LIMIT 1"
    ).fetchone()
    return _fila_a_sesion(fila) if fila else None


def sesion_abierta_mas_reciente(conexion: sqlite3.Connection) -> UUID | None:
    """La última que quedó abierta, sea de la tarea que sea. Es la que
    cierra un «listo» suelto: no hace falta decir cuál."""
    fila = conexion.execute(
        "SELECT id FROM sesiones WHERE fin IS NULL ORDER BY inicio DESC LIMIT 1"
    ).fetchone()
    return UUID(fila["id"]) if fila else None


def sesiones_abiertas(conexion: sqlite3.Connection) -> list[Sesion]:
    """Todas las que nadie cerró. Las usa nucleo/sanear.py."""
    filas = conexion.execute(
        "SELECT * FROM sesiones WHERE fin IS NULL ORDER BY inicio"
    ).fetchall()
    return [_fila_a_sesion(fila) for fila in filas]


def cerrar_sesion(conexion: sqlite3.Connection, sesion_id: UUID) -> Sesion | None:
    """Escribe `fin` y calcula `real_min` desde `inicio` (ley 1). None si la
    sesión no existe o ya estaba cerrada — cerrar dos veces no la altera."""
    fila = conexion.execute(
        "SELECT * FROM sesiones WHERE id = ?", (str(sesion_id),)
    ).fetchone()
    if fila is None or fila["fin"] is not None:
        return None

    inicio = datetime.fromisoformat(fila["inicio"])
    fin = datetime.now(timezone.utc)
    real_min = max(0, round((fin - inicio).total_seconds() / 60))

    conexion.execute(
        "UPDATE sesiones SET fin = ?, real_min = ? WHERE id = ?",
        (fin.isoformat(), real_min, str(sesion_id)),
    )
    conexion.commit()
    return _fila_a_sesion(
        conexion.execute("SELECT * FROM sesiones WHERE id = ?", (str(sesion_id),)).fetchone()
    )


# — El estante: la memoria de Remi —


@dataclass(frozen=True)
class EntradaIndice:
    """Una línea del índice. No es un contrato: es una vista recortada de
    Memoria, justo lo que entra en la mente. Sin `cuerpo`, a propósito —
    el cuerpo se lee del estante cuando hace falta, no antes."""

    id: UUID
    titulo: str
    resumen: str
    tema: str
    fecha: datetime
    claves: str | None = None
    nivel: int | None = None


def guardar_memoria(conexion: sqlite3.Connection, memoria: Memoria) -> None:
    conexion.execute(
        """
        INSERT INTO memoria (id, titulo, resumen, tema, fecha, cuerpo, fuente, claves, nivel)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(memoria.id),
            memoria.titulo,
            memoria.resumen,
            memoria.tema,
            memoria.fecha.isoformat(),
            memoria.cuerpo,
            memoria.fuente,
            memoria.claves,
            memoria.nivel,
        ),
    )
    conexion.commit()


def indice_memoria(conexion: sqlite3.Connection) -> list[EntradaIndice]:
    """Lo que Remi tiene presente, lo más reciente primero. La consulta
    nombra las columnas una por una y `cuerpo` no está: si alguien lo
    agrega, el índice deja de caber en la mente."""
    filas = conexion.execute(
        "SELECT id, titulo, resumen, tema, fecha, claves, nivel FROM memoria ORDER BY fecha DESC"
    ).fetchall()
    return [
        EntradaIndice(
            id=UUID(fila["id"]),
            titulo=fila["titulo"],
            resumen=fila["resumen"],
            tema=fila["tema"],
            fecha=datetime.fromisoformat(fila["fecha"]),
            claves=fila["claves"],
            nivel=fila["nivel"],
        )
        for fila in filas
    ]


def _fila_a_memoria(fila: sqlite3.Row) -> Memoria:
    return Memoria(
        id=UUID(fila["id"]),
        titulo=fila["titulo"],
        resumen=fila["resumen"],
        tema=fila["tema"],
        fecha=fila["fecha"],
        cuerpo=fila["cuerpo"],
        fuente=fila["fuente"],
        claves=fila["claves"],
        nivel=fila["nivel"],
    )


def memorias_por_tema(conexion: sqlite3.Connection, tema: str) -> list[Memoria]:
    """Las entradas de un tema, la más vieja primero."""
    filas = conexion.execute(
        "SELECT * FROM memoria WHERE tema = ? ORDER BY fecha", (tema,)
    ).fetchall()
    return [_fila_a_memoria(fila) for fila in filas]


def leer_memoria(conexion: sqlite3.Connection, memoria_id: UUID) -> Memoria | None:
    """Bajar una del estante, entera. None si no está."""
    fila = conexion.execute(
        "SELECT * FROM memoria WHERE id = ?", (str(memoria_id),)
    ).fetchone()
    return _fila_a_memoria(fila) if fila else None


def editar_memoria(
    conexion: sqlite3.Connection,
    memoria_id: UUID,
    *,
    titulo: str | None = None,
    resumen: str | None = None,
    tema: str | None = None,
    cuerpo: str | None = None,
    claves: str | None = None,
    nivel: int | None = None,
) -> Memoria | None:
    """Cambia solo lo que venga. None si no existe esa memoria. `fecha` y
    `fuente` no se editan: son de dónde y cuándo vino, no opinión.

    Arma la memoria entera de nuevo antes de escribir, en vez de parchear
    columnas sueltas: así el contrato sigue siendo el único lugar donde
    dice cuánto mide un título, y un cambio inválido no llega a la base."""
    actual = leer_memoria(conexion, memoria_id)
    if actual is None:
        return None

    nueva = Memoria(
        id=actual.id,
        titulo=actual.titulo if titulo is None else titulo,
        resumen=actual.resumen if resumen is None else resumen,
        tema=actual.tema if tema is None else tema,
        fecha=actual.fecha,
        cuerpo=actual.cuerpo if cuerpo is None else cuerpo,
        fuente=actual.fuente,
        claves=actual.claves if claves is None else claves,
        nivel=actual.nivel if nivel is None else nivel,
    )
    conexion.execute(
        "UPDATE memoria SET titulo = ?, resumen = ?, tema = ?, cuerpo = ?, claves = ?, nivel = ? WHERE id = ?",
        (nueva.titulo, nueva.resumen, nueva.tema, nueva.cuerpo, nueva.claves, nueva.nivel, str(nueva.id)),
    )
    conexion.commit()
    return nueva


def borrar_memoria(conexion: sqlite3.Connection, memoria_id: UUID) -> bool:
    """True si había algo que borrar."""
    cursor = conexion.execute("DELETE FROM memoria WHERE id = ?", (str(memoria_id),))
    conexion.commit()
    return cursor.rowcount > 0


# — La conversación —


@dataclass(frozen=True)
class Turno:
    rol: str  # "juan" o "remi"
    texto: str
    fecha: datetime


# Pasado esto sin turnos, la conversación terminó y la siguiente es nueva.
MINUTOS_SIN_TURNOS_PARA_CERRAR = 60


@dataclass(frozen=True)
class Conversacion:
    id: str
    resumen: str
    # Cuántos turnos (desde el primero) ya están dentro del resumen.
    resumidos: int


def conversacion_vigente(conexion: sqlite3.Connection, ahora: datetime) -> Conversacion | None:
    """La que tuvo un turno en los últimos 60 min. None si no hay."""
    from datetime import timedelta

    corte = ahora - timedelta(minutes=MINUTOS_SIN_TURNOS_PARA_CERRAR)
    fila = conexion.execute(
        "SELECT id, resumen, resumidos FROM conversaciones WHERE ultimo >= ? ORDER BY ultimo DESC LIMIT 1",
        (corte.isoformat(),),
    ).fetchone()
    return Conversacion(fila["id"], fila["resumen"], fila["resumidos"]) if fila else None


def guardar_turno(conexion: sqlite3.Connection, rol: str, texto: str, fecha: datetime) -> str:
    """Guarda el turno en la conversación vigente, o abre una nueva si pasó
    una hora sin turnos. Devuelve el id de la conversación."""
    from uuid import uuid4

    vigente = conversacion_vigente(conexion, fecha)
    if vigente is None:
        conversacion_id = str(uuid4())
        conexion.execute(
            "INSERT INTO conversaciones (id, inicio, ultimo) VALUES (?, ?, ?)",
            (conversacion_id, fecha.isoformat(), fecha.isoformat()),
        )
    else:
        conversacion_id = vigente.id
        conexion.execute(
            "UPDATE conversaciones SET ultimo = ? WHERE id = ?", (fecha.isoformat(), conversacion_id)
        )
    conexion.execute(
        "INSERT INTO turnos (id, rol, texto, fecha, conversacion_id) VALUES (?, ?, ?, ?, ?)",
        (str(uuid4()), rol, texto, fecha.isoformat(), conversacion_id),
    )
    conexion.commit()
    return conversacion_id


def turnos_de(conexion: sqlite3.Connection, conversacion_id: str) -> list[Turno]:
    """Todos los turnos de una conversación, del primero al último."""
    filas = conexion.execute(
        "SELECT rol, texto, fecha FROM turnos WHERE conversacion_id = ? ORDER BY fecha",
        (conversacion_id,),
    ).fetchall()
    return [Turno(rol=f["rol"], texto=f["texto"], fecha=datetime.fromisoformat(f["fecha"])) for f in filas]


def guardar_resumen(conexion: sqlite3.Connection, conversacion_id: str, resumen: str, resumidos: int) -> None:
    conexion.execute(
        "UPDATE conversaciones SET resumen = ?, resumidos = ? WHERE id = ?",
        (resumen, resumidos, conversacion_id),
    )
    conexion.commit()

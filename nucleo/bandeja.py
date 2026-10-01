"""La Bandeja (Ley 6): lo suelto enfría 48 h antes de una revisión en frío.

GET /bandeja (servidor.py) lista lo abierto; POST /idea/{id}/revision decide
su destino. Una idea nunca se borra: «soltar» la cierra con estado
`soltada`, y la fila queda — es memoria externa (ley 2), no una papelera.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from modelos import Idea, Tarea

HORAS_DE_ENFRIAMIENTO = 48

# El mismo paso inicial universal que servidor.PASO_MINIMO_INICIAL: no se
# importa de ahí para no atar bandeja.py a servidor.py (éste va a importar
# bandeja.py para sus rutas).
PASO_MINIMO_INICIAL = "Cinco minutos en esto y paramos."

Decision = Literal["soltar", "mantener", "tarea"]


class IdeaNoEncontrada(Exception):
    """No hay ninguna idea con ese id."""


class IdeaNoFria(Exception):
    """Ley 6: no se revisa antes de que pasen las 48 h."""


@dataclass(frozen=True)
class RevisionHecha:
    idea: Idea
    tarea: Tarea | None


def _fila_a_idea(fila: sqlite3.Row) -> Idea:
    return Idea(
        id=UUID(fila["id"]),
        texto=fila["texto"],
        origen=fila["origen"],
        creada_en=fila["creada_en"],
        enfria_hasta=fila["enfria_hasta"],
        estado=fila["estado"],
        problema_vision=fila["problema_vision"],
        tema=fila["tema"],
    )


def leer_idea(conexion: sqlite3.Connection, idea_id: UUID) -> Idea | None:
    fila = conexion.execute("SELECT * FROM ideas WHERE id = ?", (str(idea_id),)).fetchone()
    return _fila_a_idea(fila) if fila else None


def esta_fria(idea: Idea, ahora: datetime) -> bool:
    return ahora >= idea.enfria_hasta


def listar_abiertas(conexion: sqlite3.Connection, ahora: datetime) -> list[tuple[Idea, bool]]:
    """Lo que no se cerró todavía (ni soltada ni ya vuelta tarea), lo más
    nuevo primero. `fria` es solo informativa: la regla dura (409) vive en
    `revisar`, no acá."""
    filas = conexion.execute(
        "SELECT * FROM ideas WHERE estado IN ('enfriando', 'lista') ORDER BY creada_en DESC"
    ).fetchall()
    return [(idea, esta_fria(idea, ahora)) for idea in (_fila_a_idea(f) for f in filas)]


def revisar(
    conexion: sqlite3.Connection, idea_id: UUID, decision: Decision, ahora: datetime
) -> RevisionHecha:
    """Decide el destino de una idea fría. Lanza `IdeaNoEncontrada` o
    `IdeaNoFria` — servidor.py las traduce a 404 y 409."""
    idea = leer_idea(conexion, idea_id)
    if idea is None:
        raise IdeaNoEncontrada()
    if not esta_fria(idea, ahora):
        raise IdeaNoFria()

    if decision == "soltar":
        conexion.execute("UPDATE ideas SET estado = 'soltada' WHERE id = ?", (str(idea.id),))
        conexion.commit()
        nueva = leer_idea(conexion, idea.id)
        assert nueva is not None
        return RevisionHecha(idea=nueva, tarea=None)

    if decision == "mantener":
        vuelve_a_enfriar = ahora + timedelta(hours=HORAS_DE_ENFRIAMIENTO)
        conexion.execute(
            "UPDATE ideas SET estado = 'enfriando', enfria_hasta = ? WHERE id = ?",
            (vuelve_a_enfriar.isoformat(), str(idea.id)),
        )
        conexion.commit()
        nueva = leer_idea(conexion, idea.id)
        assert nueva is not None
        return RevisionHecha(idea=nueva, tarea=None)

    # decision == "tarea": la idea se vuelve proyecto (contrato Idea: estado
    # "proyecto") y nace una tarea normal con su mismo texto.
    tarea = Tarea(
        id=uuid4(),
        titulo=idea.texto,
        proyecto_id=None,
        estado="hoy",
        paso_minimo=PASO_MINIMO_INICIAL,
        estimado_min=None,
        real_min=None,
        hora=None,
        fecha_limite=None,
        compartible=False,
    )
    conexion.execute(
        """
        INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible, hora, fecha_limite)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (str(tarea.id), tarea.titulo, None, tarea.estado, tarea.paso_minimo, None, None, 0, None, None),
    )
    conexion.execute("UPDATE ideas SET estado = 'proyecto' WHERE id = ?", (str(idea.id),))
    conexion.commit()
    nueva = leer_idea(conexion, idea.id)
    assert nueva is not None
    return RevisionHecha(idea=nueva, tarea=tarea)

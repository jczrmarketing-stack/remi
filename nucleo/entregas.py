"""Entregas (3f · 2): CRUD del contrato Entrega, aparte de servidor.py — un
router que se incluye con una sola línea. `compartible: true` en el
contrato: una Entrega SÍ puede llegar a los espejos (Notion, Calendar), a
diferencia de Tarea/Sesión.

Sin IA: crear una entrega desde el chat («entrega para Alfonso el 18 de
octubre por 5.000») se resuelve con reglas locales (regex), como el resto
del líder — nunca con un modelo.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from modelos import Entrega

router = APIRouter(prefix="/entregas", tags=["entregas"])

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# «entrega para Alfonso el 18 de octubre por 5.000» · sin "el" · sin "para".
_PATRON = re.compile(
    r"entrega\s+(?:para|de)\s+(?P<cliente>.+?)\s+(?:el\s+)?"
    r"(?P<dia>\d{1,2})\s+de\s+(?P<mes>[a-záéíóúñ]+)(?:\s+de\s+(?P<anio>\d{4}))?"
    r"\s+por\s+\$?\s*(?P<monto>[\d.,]+)",
    re.IGNORECASE,
)


class EntregaParseada(BaseModel):
    cliente: str
    fecha: datetime
    monto: float


def parsear_entrega(texto: str) -> EntregaParseada | None:
    """Reglas, no IA. `None` si el texto no tiene la forma de un encargo con
    entrega — no inventa un cliente ni una fecha de una frase ambigua."""
    coincidencia = _PATRON.search(texto)
    if not coincidencia:
        return None
    mes = _MESES.get(coincidencia.group("mes").lower())
    if mes is None:
        return None
    anio = int(coincidencia.group("anio") or datetime.now(timezone.utc).year)
    try:
        fecha = datetime(anio, mes, int(coincidencia.group("dia")), tzinfo=timezone.utc)
    except ValueError:
        return None
    monto_texto = coincidencia.group("monto").replace(".", "").replace(",", ".")
    try:
        monto = float(monto_texto)
    except ValueError:
        return None
    return EntregaParseada(cliente=coincidencia.group("cliente").strip(), fecha=fecha, monto=monto)


def _proyecto_id_de_tema(tema: str | None) -> UUID:
    """Todavía no hay un Proyecto con id propio en el núcleo (`tarea.proyecto_id`
    sale siempre null hoy, ver servidor.py). Mientras eso no exista, un id
    determinístico por tema deja a Entrega usable sin inventar una tabla de
    proyectos acá — apuntado en la bitácora para la sesión de nucleo/."""
    return uuid5(NAMESPACE_URL, f"remi:proyecto:{tema or 'sin-proyecto'}")


def crear_entrega(conexion: sqlite3.Connection, entrega: Entrega) -> None:
    conexion.execute(
        """
        INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(entrega.id),
            entrega.cliente,
            str(entrega.proyecto_id),
            entrega.fecha.isoformat(),
            entrega.monto,
            entrega.estado,
            int(entrega.compartible),
        ),
    )
    conexion.commit()


def _fila_a_entrega(fila: sqlite3.Row) -> Entrega:
    return Entrega(
        id=UUID(fila["id"]),
        cliente=fila["cliente"],
        proyecto_id=UUID(fila["proyecto_id"]),
        fecha=datetime.fromisoformat(fila["fecha"]),
        monto=fila["monto"],
        estado=fila["estado"],
        compartible=bool(fila["compartible"]),
    )


def listar_entregas(conexion: sqlite3.Connection) -> list[Entrega]:
    filas = conexion.execute("SELECT * FROM entregas ORDER BY fecha").fetchall()
    return [_fila_a_entrega(f) for f in filas]


def leer_entrega(conexion: sqlite3.Connection, entrega_id: UUID) -> Entrega | None:
    fila = conexion.execute("SELECT * FROM entregas WHERE id = ?", (str(entrega_id),)).fetchone()
    return _fila_a_entrega(fila) if fila else None


def entrega_del_proyecto(conexion: sqlite3.Connection, proyecto_id: UUID) -> Entrega | None:
    """La entrega viva (no pagada) de un proyecto — la que hace que un
    bloque de esa tarea sea «piel dinero» (3f · 3)."""
    fila = conexion.execute(
        "SELECT * FROM entregas WHERE proyecto_id = ? AND estado != 'pagada' AND monto IS NOT NULL ORDER BY fecha LIMIT 1",
        (str(proyecto_id),),
    ).fetchone()
    return _fila_a_entrega(fila) if fila else None


def actualizar_estado_entrega(conexion: sqlite3.Connection, entrega_id: UUID, estado: str) -> Entrega | None:
    conexion.execute("UPDATE entregas SET estado = ? WHERE id = ?", (estado, str(entrega_id)))
    conexion.commit()
    return leer_entrega(conexion, entrega_id)


# — Rutas —

class CrearEntregaDesdeTexto(BaseModel):
    texto: str
    tema: str | None = None


@router.get("", response_model=list[Entrega])
def listar() -> list[Entrega]:
    conexion = db.conectar()
    try:
        return listar_entregas(conexion)
    finally:
        conexion.close()


@router.get("/{entrega_id}", response_model=Entrega)
def obtener(entrega_id: UUID) -> Entrega:
    conexion = db.conectar()
    try:
        entrega = leer_entrega(conexion, entrega_id)
        if entrega is None:
            raise HTTPException(status_code=404, detail="no hay entrega con ese id")
        return entrega
    finally:
        conexion.close()


@router.get("/de-proyecto/{proyecto_id}", response_model=Entrega | None)
def de_proyecto(proyecto_id: UUID) -> Entrega | None:
    """El bloque abierto de una tarea de este proyecto: ¿pertenece a una
    entrega que paga?"""
    conexion = db.conectar()
    try:
        return entrega_del_proyecto(conexion, proyecto_id)
    finally:
        conexion.close()


@router.post("", response_model=Entrega, status_code=201)
def crear_desde_texto(cuerpo: CrearEntregaDesdeTexto) -> Entrega:
    """«entrega para Alfonso el 18 de octubre por 5.000» — reglas, no IA
    (ver parsear_entrega). Sin la forma esperada, 422: Remi no adivina."""
    parseada = parsear_entrega(cuerpo.texto)
    if parseada is None:
        raise HTTPException(status_code=422, detail="no reconocí cliente, fecha y monto en ese texto")
    entrega = Entrega(
        id=uuid4(),
        cliente=parseada.cliente,
        proyecto_id=_proyecto_id_de_tema(cuerpo.tema),
        fecha=parseada.fecha,
        monto=parseada.monto,
        estado="camino",
        compartible=True,
    )
    conexion = db.conectar()
    try:
        crear_entrega(conexion, entrega)
        return entrega
    finally:
        conexion.close()


@router.post("/{entrega_id}/estado", response_model=Entrega)
def cambiar_estado(entrega_id: UUID, estado: str) -> Entrega:
    if estado not in ("camino", "entregada", "pagada"):
        raise HTTPException(status_code=422, detail="estado inválido")
    conexion = db.conectar()
    try:
        entrega = actualizar_estado_entrega(conexion, entrega_id, estado)
        if entrega is None:
            raise HTTPException(status_code=404, detail="no hay entrega con ese id")
        return entrega
    finally:
        conexion.close()

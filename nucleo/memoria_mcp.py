"""El estante de Remi, como servidor MCP (stdio).

La mente (el índice: títulos y con qué se quedó) viaja siempre en el system
prompt y no cuesta nada mirarla. El cuerpo entero de cada cosa vive acá, y
se baja solo cuando hace falta — sabiendo de antemano cuál bajar, que para
eso está el índice. Nada de embeddings ni búsqueda: si no está en el
índice, Remi no lo sabe.

Corre contra el mismo remi.db que el resto del núcleo (REMI_DB_PATH manda,
igual que en db.py). Nada sale del Mac.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from mcp.server.mcpserver import MCPServer
from pydantic import ValidationError

import db
from modelos import Memoria

# El nombre del servidor arma el de las herramientas que ve la CLI:
# mcp__memoria__leer y mcp__memoria__guardar.
servidor = MCPServer(
    "memoria",
    instructions=(
        "El estante de Remi: lo que Juan Camilo le contó. El índice ya está en tu "
        "contexto; usá `leer` con el id de la entrada que haga falta y `guardar` "
        "cuando aparezca algo que valga la pena recordar."
    ),
)


@servidor.tool(
    description=(
        "Baja del estante una cosa que ya sabés, entera. El id sale del índice que "
        "tenés arriba; alcanza con los primeros ocho caracteres."
    )
)
def leer(id: str) -> str:
    _marcar_lectura()
    conexion = db.conectar()
    try:
        memoria = _buscar(conexion, id)
        if memoria is None:
            # Ley 3: no hay reto ni «deberías». Se dice qué pasó y qué hacer.
            return (
                f"No tengo nada con el id {id}. Mirá el índice de arriba y probá "
                "con uno de esos."
            )
        fecha = memoria.fecha.date().isoformat()
        return (
            f"{memoria.titulo}\n"
            f"{fecha} · {memoria.tema} · {memoria.fuente}\n\n"
            f"{memoria.cuerpo}"
        )
    finally:
        conexion.close()


@servidor.tool(
    description=(
        "Guarda algo nuevo en el estante. El título y el resumen son lo que vas a "
        "tener presente después, así que tienen que valerse solos: el título en "
        "hasta 80 caracteres y el resumen en hasta 240. El cuerpo es lo largo, lo "
        "que solo se lee al bajarlo."
    )
)
def guardar(titulo: str, resumen: str, cuerpo: str, tema: str) -> str:
    try:
        memoria = Memoria(
            id=uuid4(),
            titulo=titulo.strip(),
            resumen=resumen.strip(),
            tema=tema.strip(),
            fecha=datetime.now(timezone.utc),
            cuerpo=cuerpo,
            fuente="conversacion",
        )
    except ValidationError:
        return (
            "Así no me entra: el título va hasta 80 caracteres y el resumen hasta "
            "240, y ninguno puede ir vacío. Probá más corto."
        )

    conexion = db.conectar()
    try:
        db.guardar_memoria(conexion, memoria)
    finally:
        conexion.close()
    return f"Guardado. [{str(memoria.id)[:8]}] {memoria.titulo}"


# Quien nos abrió (pensar.py) quiere saber si Remi llegó a bajar algo del
# estante, y el JSON final de la CLI no lo dice. Dejamos una marca en el
# archivo que nos indiquen. Si nadie indicó nada, no se marca nada.
MARCA = "REMI_MARCA_LECTURA"


def _marcar_lectura() -> None:
    ruta = os.environ.get(MARCA)
    if not ruta:
        return
    try:
        Path(ruta).touch()
    except OSError:
        pass


def _buscar(conexion: sqlite3.Connection, id_pedido: str) -> Memoria | None:
    """Acepta el id entero o el corto de ocho que muestra el índice."""
    pedido = id_pedido.strip().lower()
    try:
        return db.leer_memoria(conexion, UUID(pedido))
    except ValueError:
        pass
    for entrada in db.indice_memoria(conexion):
        if str(entrada.id).startswith(pedido):
            return db.leer_memoria(conexion, entrada.id)
    return None


if __name__ == "__main__":
    servidor.run("stdio")

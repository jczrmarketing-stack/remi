"""El estante de Remi, como servidor MCP (stdio).

La mente (el índice: títulos y con qué se quedó) viaja siempre en el system
prompt y no cuesta nada mirarla. El cuerpo entero de cada cosa vive acá, y
se baja solo cuando hace falta — sabiendo de antemano cuál bajar, que para
eso está el índice. T10: el índice tiene un presupuesto de tokens, así que
no siempre trae todo — `buscar_memoria` encuentra lo que quedó afuera.

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
import experiencia
from modelos import Memoria

# El nombre del servidor arma el de las herramientas que ve la CLI:
# mcp__memoria__leer y mcp__memoria__guardar.
servidor = MCPServer(
    "memoria",
    instructions=(
        "El estante de Remi: lo que Juan Camilo le contó. Si el índice no está en "
        "tu contexto, pedilo con `indice`; usá `leer` con el id de la entrada que "
        "haga falta y `guardar` cuando aparezca algo que valga la pena recordar. "
        "Al cerrar un trabajo, por cada problema resuelto o acierto que valga la pena "
        "repetir: `anotar_leccion`. Antes de proponer un arreglo nuevo: `buscar_lecciones`. "
        "Si el índice no trae algo viejo que debería estar (quedó fuera del presupuesto): "
        "`buscar_memoria`."
    ),
)


@servidor.tool(
    description=(
        "Qué hay en el estante: una línea por cosa, con su id, tema, título y "
        "resumen. Usala si no tenés el índice en tu contexto (fuera de Remi, en "
        "cualquier sesión de Claude). Con `tema` filtra, por ejemplo «upvisuals»."
    )
)
def indice(tema: str = "") -> str:
    # Remi trae el índice en su prompt; Claude Code desde otra carpeta no, y
    # sin esto no tenía de dónde sacar el id que pide `leer` (3d · 6,
    # revisión del 30/09).
    conexion = db.conectar()
    try:
        entradas = db.indice_memoria(conexion)
    finally:
        conexion.close()
    filtro = tema.strip().lower()
    elegidas = [e for e in entradas if not filtro or e.tema.lower() == filtro]
    if not elegidas:
        return f"No hay nada con el tema «{tema}»." if filtro else "El estante está vacío."
    return "\n".join(f"{str(e.id)[:8]} · {e.tema} · {e.titulo} — {e.resumen}" for e in elegidas)


@servidor.tool(
    description=(
        "Baja del estante una cosa que ya sabés, entera. El id sale del índice que "
        "tenés arriba; alcanza con los primeros ocho caracteres."
    )
)
def leer(id: str) -> str:
    conexion = db.conectar()
    try:
        memoria = _buscar(conexion, id)
        _marcar_lectura(memoria.tema if memoria else f"?{id}")
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
            claves=None,
            nivel=None,
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


@servidor.tool(
    description=(
        "T8: al cerrar un trabajo, por cada problema resuelto o acierto que valga la pena "
        "repetir — anotá una lección, con evidencia, no un resumen de la charla. "
        "`clase` es «error» o «acierto»; `secciones` lleva las que pide cada clase: error — "
        "Síntoma, Lo que creímos (vacía si no hubo pista falsa), Causa real, Cura, Cómo "
        "verlo antes; acierto — Qué funcionó, Evidencia, Cuándo usarlo. `donde` es el repo y "
        "el archivo. Si ya hay una lección del mismo tema con el mismo síntoma, esto no crea "
        "otra: le suma una vuelta más."
    )
)
def anotar_leccion(
    titulo: str, tema: str, resumen: str, clase: str, donde: str, secciones: dict[str, str]
) -> str:
    if clase not in experiencia.CLASES:
        return f"clase tiene que ser error o acierto, no «{clase}»."
    leccion = experiencia.Leccion(
        titulo=titulo, tema=tema, resumen=resumen, clase=clase,  # type: ignore[arg-type]
        donde=donde, secciones=secciones, fuente="claude-code",
    )
    try:
        destino, es_nueva = experiencia.escribir(leccion)
    except ValueError as error:
        return f"Así no me entra: {error}"
    if es_nueva:
        return f"Anotada. {destino.name}"
    return f"Ya había una lección igual de {tema} — le sumé una vuelta más ({destino.name})."


@servidor.tool(
    description=(
        "T8: antes de proponer un arreglo nuevo, buscá si esto ya pasó. Texto exacto (un "
        "código de error, un nombre, un monto) y parecido, sobre toda la bóveda — libros, "
        "oficios, episodios y lecciones. `tema` filtra, por ejemplo «malik»."
    )
)
def buscar_lecciones(q: str, tema: str = "") -> str:
    conexion = db.conectar()
    try:
        encontradas = experiencia.buscar(conexion, q, tema.strip() or None)
    finally:
        conexion.close()
    if not encontradas:
        return "No encontré nada parecido en la bóveda."
    return "\n".join(f"{r.tipo} · {r.titulo} — {r.ruta}" for r in encontradas)


@servidor.tool(
    description=(
        "T10: el índice de arriba tiene un presupuesto de tokens — lo viejo que no entró "
        "no se borró ni se movió, sigue en el estante. Buscá por una palabra exacta "
        "(título, resumen, tema) para encontrarlo. `tema` filtra."
    )
)
def buscar_memoria(q: str, tema: str = "") -> str:
    conexion = db.conectar()
    try:
        encontradas = db.buscar_memoria(conexion, q, tema.strip() or None)
    finally:
        conexion.close()
    if not encontradas:
        return "No encontré nada en el estante con eso."
    return "\n".join(f"{str(e.id)[:8]} · {e.tema} · {e.titulo} — {e.resumen}" for e in encontradas)


# Quien nos abrió (pensar.py) quiere saber si Remi llegó a bajar algo del
# estante, y el JSON final de la CLI no lo dice. Dejamos una marca en el
# archivo que nos indiquen. Si nadie indicó nada, no se marca nada.
MARCA = "REMI_MARCA_LECTURA"


def _marcar_lectura(tema: str) -> None:
    """Agrega una línea con el tema del libro leído: así el log dice QUÉ
    leyó, no solo si leyó. Un id que no existía queda como «?id»."""
    ruta = os.environ.get(MARCA)
    if not ruta:
        return
    try:
        with Path(ruta).open("a") as archivo:
            archivo.write(tema + "\n")
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

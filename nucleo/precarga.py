"""Precarga del proyecto activo (ARQUITECTURA-CEREBRO §4).

Antes de cada respuesta, el nivel 2 (el Estado) del proyecto activo entra al
contexto sin que el modelo tenga que llamar a `leer`: por eso cuando
preguntas por lo que estás haciendo, ya está — no hay que ir a buscarlo.

Proyecto activo, en este orden:
1. **Bloque abierto**: la sesión de trabajo abierta más reciente ya guarda,
   en `app_contexto`, el tema del proyecto activo al abrirse esa tarea
   (servidor.py, `POST /mensaje`).
2. **App en primer plano** (NSWorkspace): todavía no existe esa señal en el
   núcleo — es Fase F · 13, sin construir. Cuando exista, entra acá, entre
   el bloque abierto y el último tocado.
3. **El último libro tocado** (`trabajo_eventos`): lo mismo que usa
   `trabajo._libro_reciente()` para «¿dónde quedé?».

`estado_libro` se importa adentro de la función, no arriba del archivo: así
se evita el ciclo pensar → precarga → estado_libro → pensar.
"""
from __future__ import annotations

import db
import libros

ENCABEZADO = (
    "\n\nEsto es lo que estás haciendo ahora mismo (precargado, nivel 2 — "
    "ARQUITECTURA-CEREBRO §4; no hizo falta pedirlo con `leer`):\n"
)


def _tema_de_bloque_abierto() -> str | None:
    conexion = db.conectar()
    try:
        sesion_id = db.sesion_abierta_mas_reciente(conexion)
        if sesion_id is None:
            return None
        fila = conexion.execute(
            "SELECT app_contexto FROM sesiones WHERE id = ?", (str(sesion_id),)
        ).fetchone()
        tema = fila["app_contexto"] if fila else None
        return str(tema) if tema else None
    finally:
        conexion.close()


def _ultimo_tocado() -> str | None:
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT tema FROM trabajo_eventos WHERE tema IS NOT NULL ORDER BY fecha DESC LIMIT 1"
        ).fetchone()
        return str(fila["tema"]) if fila else None
    finally:
        conexion.close()


def proyecto_activo() -> tuple[str, str] | None:
    """(tema, razón) del proyecto activo, o None si no hay ninguna señal."""
    tema = _tema_de_bloque_abierto()
    if tema:
        return tema, "bloque_abierto"
    tema = _ultimo_tocado()
    if tema:
        return tema, "ultimo_tocado"
    return None


def _libro_de(tema: str) -> libros.Libro | None:
    return next((libro for libro in libros.listar() if libro.tema == tema), None)


def resumen_nivel2(tema: str) -> str | None:
    """El Estado del libro (Quedaste/Decisiones/Próximo paso), o su resumen
    si todavía no tiene Estado. None si no hay libro con ese tema."""
    import estado_libro  # import diferido: evita el ciclo con pensar.py

    libro = _libro_de(tema)
    if libro is None:
        return None
    estado = estado_libro.leer_estado(libro.archivo)
    if estado.strip():
        return f"{libro.titulo}:\n{estado.strip()}"
    return f"{libro.titulo}: {libro.resumen}"


def bloque() -> tuple[str, str] | None:
    """(texto a sumar a las instrucciones, "<tema> razon=<razón>" para el
    log), o None si no hay nada que precargar."""
    activo = proyecto_activo()
    if activo is None:
        return None
    tema, razon = activo
    resumen = resumen_nivel2(tema)
    if resumen is None:
        return None
    return f"{ENCABEZADO}{resumen}\n", f"{tema} razon={razon}"

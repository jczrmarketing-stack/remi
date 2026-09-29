#!/usr/bin/env python
"""Cierra las sesiones que quedaron abiertas y nadie cerró.

Hasta ahora /mensaje abría un bloque con cada frase y no lo cerraba nunca,
así que la base tiene sesiones colgadas de días. Mientras estén abiertas, la
ley 1 no puede decir «la última vez esto te tomó 1 h 40»: no hay duración,
hay un cronómetro corriendo.

    cd nucleo && uv run python sanear.py

No borra tareas. Las de basura las marca Juan Camilo, no este script: una
tarea borrada no se puede recuperar y no somos quién.
"""
from __future__ import annotations

from datetime import datetime, timezone

import db


def sanear() -> int:
    """Devuelve cuántas sesiones cerró."""
    ahora = datetime.now(timezone.utc)
    conexion = db.conectar()
    try:
        abiertas = db.sesiones_abiertas(conexion)
        if not abiertas:
            print("No hay sesiones abiertas. Nada que hacer.")
            return 0

        print(f"{len(abiertas)} sesión(es) abierta(s):\n")
        for sesion in abiertas:
            tarea = db.leer_tarea(conexion, sesion.tarea_id)
            titulo = tarea.titulo if tarea else "(sin tarea)"
            del_mismo_dia = sesion.inicio.date() == ahora.date()

            if del_mismo_dia:
                # Es de hoy: el tiempo transcurrido es creíble.
                cerrada = db.cerrar_sesion(conexion, sesion.id)
                minutos = cerrada.real_min if cerrada else 0
                print(f"  cerrada en {minutos:>4} min · {sesion.inicio.date()} · {titulo}")
            else:
                # De otro día: nadie estuvo doce horas en esto. Un número
                # inventado es peor que un cero — la ley 1 se apoya en esto.
                db.cerrar_sesion_en_cero(conexion, sesion.id)
                print(f"  cerrada en    0 min · {sesion.inicio.date()} · {titulo} (de otro día)")

        return len(abiertas)
    finally:
        conexion.close()


if __name__ == "__main__":
    cuantas = sanear()
    if cuantas:
        print(f"\n{cuantas} sesión(es) cerrada(s). Ninguna tarea se tocó.")

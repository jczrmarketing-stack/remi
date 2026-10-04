"""B7: hilos por tema (de la revisión R6). Al saltar de proyecto en medio
de una charla, Remi anota qué quedó a medias en el tema que se deja, y lo
devuelve una sola vez al volver a ese tema. Sin IA: el salto se detecta
con `temas.tema_de_texto`, que ya existe."""
from __future__ import annotations

import sqlite3
from datetime import datetime

import db
import temas


def rastrear(conexion: sqlite3.Connection, texto: str, ahora: datetime) -> str | None:
    """Mira de qué tema habla `texto`. Si es distinto del último tema
    visto, deja anotado qué quedó a medias en ese tema anterior. Devuelve
    el hilo pendiente de ESTE tema, si había uno — y lo consume."""
    tema = temas.tema_de_texto(texto)
    if tema is None:
        return None
    anterior = db.ultimo_tema_visto(conexion)
    if anterior is not None and anterior[0] != tema:
        db.guardar_hilo(conexion, anterior[0], anterior[1], ahora)
    hilo = db.recoger_hilo(conexion, tema)
    db.poner_ultimo_tema_visto(conexion, tema, texto, ahora)
    return hilo


def voz_del_hilo(tema: str, texto_quedado: str) -> str:
    return f"En {tema}, quedaste en: {texto_quedado}"

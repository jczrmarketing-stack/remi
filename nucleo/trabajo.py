"""Las herramientas avisan solas. Remi no espera una palabra clave.

POST /evento trae un commit o una sesión, con la carpeta donde pasó.
Si esa carpeta tiene libro, el evento queda a su nombre. Si no, entra a
la Bandeja una sola vez, como «proyecto sin ficha», y no se repite
mientras siga enfriando.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import db
import libros
from modelos import Idea

HORAS_DE_ENFRIAMIENTO = 48


def _anotar_sin_ficha(ruta: str, ahora: datetime) -> bool:
    """True si esta vez sí se anotó. La misma carpeta no llena la Bandeja."""
    texto = f"proyecto sin ficha: {ruta}"
    conexion = db.conectar()
    try:
        ya = conexion.execute(
            "SELECT 1 FROM ideas WHERE texto = ? AND estado = 'enfriando' LIMIT 1",
            (texto,),
        ).fetchone()
        if ya:
            return False
        db.crear_idea(
            conexion,
            Idea(
                id=uuid4(),
                texto=texto,
                origen="texto",
                creada_en=ahora,
                enfria_hasta=ahora + timedelta(hours=HORAS_DE_ENFRIAMIENTO),
                estado="enfriando",
                problema_vision=None,
            ),
        )
    finally:
        conexion.close()
    return True


def recibir(tipo: str, ruta: str, datos: dict[str, object] | None = None, ahora: datetime | None = None) -> dict[str, object]:
    """Registra el evento y dice a qué proyecto cayó. Nunca levanta por una carpeta rara."""
    momento = ahora or datetime.now(timezone.utc)
    libro = libros.por_ruta(ruta)
    tema = libro.tema if libro else None
    anotado = False
    if libro is None and ruta.strip():
        anotado = _anotar_sin_ficha(ruta.strip(), momento)

    conexion = db.conectar()
    try:
        conexion.execute(
            """
            INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), tipo, ruta, tema, json.dumps(datos or {}, ensure_ascii=False), momento.isoformat()),
        )
        conexion.commit()
    finally:
        conexion.close()

    return {"proyecto": tema, "anotado": anotado}

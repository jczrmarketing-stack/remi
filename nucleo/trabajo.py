"""Las herramientas avisan solas. Remi no espera una palabra clave.

POST /evento trae un commit o una sesión, con la carpeta donde pasó.
Si esa carpeta tiene libro, el evento queda a su nombre. Si no, entra a
la Bandeja una sola vez, como «proyecto sin ficha», y no se repite
mientras siga enfriando.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import db
import estado_libro
import libros
from modelos import Idea

HORAS_DE_ENFRIAMIENTO = 48
MINUTOS_ENTRE_ESTADOS = 10


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

    carga = datos or {}
    conexion = db.conectar()
    try:
        conexion.execute(
            """
            INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), tipo, ruta, tema, json.dumps(carga, ensure_ascii=False), momento.isoformat()),
        )
        if tema and tipo == "commit":
            _guardar_commit(conexion, tema, carga, momento)
        conexion.commit()
    finally:
        conexion.close()

    if tema and tipo == "commit":
        _programar_estado(tema, momento)

    return {"proyecto": tema, "anotado": anotado}


def _guardar_commit(
    conexion: sqlite3.Connection, tema: str, datos: dict[str, object], ahora: datetime
) -> None:
    mensaje = str(datos.get("mensaje") or "").strip()
    rama = str(datos.get("rama") or "").strip()
    crudos = datos.get("archivos") or []
    archivos = [str(a) for a in crudos][:40] if isinstance(crudos, list) else []
    conexion.execute(
        """
        INSERT INTO trabajo_commits (id, tema, mensaje, rama, archivos, fecha, incluido)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (str(uuid4()), tema, mensaje, rama, json.dumps(archivos, ensure_ascii=False), ahora.isoformat()),
    )


def _programar_estado(tema: str, ahora: datetime) -> None:
    """Como máximo una redacción cada 10 min. La primera de la ventana sale ya."""
    if os.environ.get("REMI_ESTADO", "1") == "0":
        return
    if not _tomar_turno(tema, ahora):
        return
    if os.environ.get("REMI_TRABAJO_EN_LINEA") == "1":
        actualizar_estado(tema, ahora)
        return
    hilo = threading.Thread(target=_actualizar_seguro, args=(tema, ahora), daemon=True)
    hilo.start()


def _tomar_turno(tema: str, ahora: datetime) -> bool:
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT fecha FROM trabajo_estado_en WHERE tema = ?", (tema,)
        ).fetchone()
        if fila is not None:
            anterior = datetime.fromisoformat(str(fila["fecha"]))
            if anterior.tzinfo is None:
                anterior = anterior.replace(tzinfo=timezone.utc)
            if ahora - anterior < timedelta(minutes=MINUTOS_ENTRE_ESTADOS):
                return False
        conexion.execute(
            """
            INSERT INTO trabajo_estado_en (tema, fecha) VALUES (?, ?)
            ON CONFLICT(tema) DO UPDATE SET fecha = excluded.fecha
            """,
            (tema, ahora.isoformat()),
        )
        conexion.commit()
        return True
    finally:
        conexion.close()


def _actualizar_seguro(tema: str, hasta: datetime) -> None:
    try:
        actualizar_estado(tema, hasta)
    except Exception as error:  # noqa: BLE001 — un libro que no se pudo escribir no tumba el núcleo
        print(f"[estado] no pude actualizar {tema} ({type(error).__name__})", file=sys.stderr)


def actualizar_estado(tema: str, hasta: datetime) -> None:
    """Escribe ## Estado con los commits que todavía no entraron."""
    libro = next((item for item in libros.listar() if item.tema == tema), None)
    if libro is None:
        return
    commits = _commits_pendientes(tema, hasta)
    if not commits:
        return
    anterior = estado_libro.leer_estado(libro.archivo)
    texto = estado_libro.redactar(estado_libro.pedido(libro.titulo, anterior, commits))
    if not texto:
        texto = estado_libro.plano(commits)
    estado_libro.escribir_estado(libro.archivo, texto)
    _marcar_incluidos([str(c["id"]) for c in commits])


def _commits_pendientes(tema: str, hasta: datetime) -> list[dict[str, object]]:
    conexion = db.conectar()
    try:
        filas = conexion.execute(
            """
            SELECT id, mensaje, rama, archivos, fecha FROM trabajo_commits
            WHERE tema = ? AND incluido = 0 AND fecha <= ?
            ORDER BY fecha
            """,
            (tema, hasta.isoformat()),
        ).fetchall()
    finally:
        conexion.close()
    commits: list[dict[str, object]] = []
    for fila in filas:
        try:
            archivos = json.loads(fila["archivos"])
        except json.JSONDecodeError:
            archivos = []
        commits.append(
            {
                "id": fila["id"],
                "mensaje": fila["mensaje"],
                "rama": fila["rama"],
                "archivos": archivos if isinstance(archivos, list) else [],
            }
        )
    return commits


def _marcar_incluidos(ids: list[str]) -> None:
    if not ids:
        return
    conexion = db.conectar()
    try:
        conexion.executemany(
            "UPDATE trabajo_commits SET incluido = 1 WHERE id = ?",
            [(item,) for item in ids],
        )
        conexion.commit()
    finally:
        conexion.close()

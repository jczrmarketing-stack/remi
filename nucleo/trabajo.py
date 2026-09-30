"""Las herramientas avisan solas. Remi no espera una palabra clave.

POST /evento trae un commit o una sesión, con la carpeta donde pasó.
Si esa carpeta tiene libro, el evento queda a su nombre. Si no, entra a
la Bandeja una sola vez, como «proyecto sin ficha», y no se repite
mientras siga enfriando.
"""
from __future__ import annotations

import json
from pathlib import Path
import os
import re
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import clasificar
import db
import estado_libro
import libros
from modelos import Idea

_DONDE = re.compile(r"\bdonde qued(?:e|amos|aste)\b")
BOGOTA = ZoneInfo("America/Bogota")

HORAS_DE_ENFRIAMIENTO = 48
MINUTOS_ENTRE_ESTADOS = 10


def es_carpeta_de_proyecto(ruta: str) -> bool:
    """Un proyecto sin libro solo cuenta si la carpeta está dentro de un repo
    de git. Abrir Claude Code en la carpeta personal (30/09, 00:47) o en una
    temporal no es un proyecto: antes dejaba «proyecto sin ficha:
    /Users/juancamilo» en la Bandeja."""
    try:
        carpeta = Path(ruta).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    casa = Path.home().resolve()
    if carpeta == casa:
        return False
    for actual in (carpeta, *carpeta.parents):
        if actual == casa or actual == actual.parent:
            return False
        if (actual / ".git").exists():
            return True
    return False


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


def es_cuanto(texto: str) -> bool:
    return "cuanto le meti" in clasificar.normalizar(texto)


def cuanto_le_meti(texto: str, ahora: datetime | None = None) -> str | None:
    """El número de la semana, o None si no era esa pregunta."""
    if not es_cuanto(texto):
        return None
    libro = _libro_nombrado(texto)
    if libro is None:
        return "No sé de qué proyecto."
    nombre = libro.titulo.split("—")[0].split(" - ")[0].strip() or libro.tema
    minutos = minutos_esta_semana(libro.tema, ahora)
    if minutos <= 0:
        return f"A {nombre} esta semana no tengo tiempo medido."
    return f"A {nombre} esta semana: {_formato(minutos)}."


def minutos_esta_semana(tema: str, ahora: datetime | None = None) -> int:
    """Claude Code más los bloques de Remi, de lunes a ahora, hora de Bogotá."""
    momento = ahora or datetime.now(timezone.utc)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    desde = _lunes(momento)
    conexion = db.conectar()
    try:
        filas = list(
            conexion.execute(
                "SELECT inicio, fin FROM trabajo_claude WHERE tema = ?", (tema,)
            ).fetchall()
        )
        filas += list(
            conexion.execute(
                "SELECT inicio, fin FROM sesiones WHERE app_contexto = ?", (tema,)
            ).fetchall()
        )
    finally:
        conexion.close()
    return sum(_solape(fila["inicio"], fila["fin"], desde, momento) for fila in filas)


def tema_activo() -> str | None:
    libro = _libro_reciente()
    return libro.tema if libro else None


def _lunes(momento: datetime) -> datetime:
    local = momento.astimezone(BOGOTA)
    cero = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return (cero - timedelta(days=cero.weekday())).astimezone(timezone.utc)


def _solape(inicio_iso: str, fin_iso: str | None, desde: datetime, hasta: datetime) -> int:
    inicio = datetime.fromisoformat(str(inicio_iso))
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    if fin_iso:
        fin = datetime.fromisoformat(str(fin_iso))
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
    else:
        fin = hasta
    a = max(inicio, desde)
    b = min(fin, hasta)
    if b <= a:
        return 0
    return int((b - a).total_seconds() // 60)


def _formato(minutos: int) -> str:
    """Igual que servidor.formatear_duracion: «40 min» o «1 h 40»."""
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto:02d}" if resto else f"{horas} h"


def _abrir_claude(
    conexion: sqlite3.Connection,
    datos: dict[str, object],
    tema: str | None,
    ruta: str,
    ahora: datetime,
) -> None:
    sesion = str(datos.get("session_id") or "").strip()
    if not sesion:
        return
    conexion.execute(
        """
        INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin)
        VALUES (?, ?, ?, ?, NULL)
        ON CONFLICT(session_id) DO NOTHING
        """,
        (sesion, tema, ruta, ahora.isoformat()),
    )


def _cerrar_claude(conexion: sqlite3.Connection, datos: dict[str, object], ahora: datetime) -> None:
    """Sin la fila de inicio, no se inventa cuánto duró."""
    sesion = str(datos.get("session_id") or "").strip()
    if not sesion:
        return
    conexion.execute(
        "UPDATE trabajo_claude SET fin = ? WHERE session_id = ? AND fin IS NULL",
        (ahora.isoformat(), sesion),
    )


def es_donde_quede(texto: str) -> bool:
    return bool(_DONDE.search(clasificar.normalizar(texto)))


def donde_quede(texto: str) -> str | None:
    """Tres líneas, o una si no hay proyecto. None si no era esa pregunta."""
    if not es_donde_quede(texto):
        return None
    libro = _libro_nombrado(texto) or _libro_reciente()
    if libro is None:
        return "No tengo un proyecto abierto."
    return "\n\n".join(_tres_lineas(libro))


def lineas_donde_quede() -> list[str]:
    """Al abrir la ventanita. Vacío si no hay proyecto: no se dice nada."""
    libro = _libro_reciente()
    if libro is None:
        return []
    return _tres_lineas(libro)


def _libro_nombrado(texto: str) -> libros.Libro | None:
    limpio = clasificar.normalizar(texto)
    mejor: libros.Libro | None = None
    mejor_largo = -1
    for libro in libros.listar():
        formas = {libro.tema, libro.tema.replace("-", " ")}
        for forma in formas:
            if not forma:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(forma)}(?![a-z0-9])", limpio) and len(forma) > mejor_largo:
                mejor = libro
                mejor_largo = len(forma)
    return mejor


def _libro_reciente() -> libros.Libro | None:
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            """
            SELECT tema FROM trabajo_eventos
            WHERE tema IS NOT NULL
            ORDER BY fecha DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conexion.close()
    if fila is None:
        return None
    tema = str(fila["tema"])
    return next((libro for libro in libros.listar() if libro.tema == tema), None)


def _tres_lineas(libro: libros.Libro) -> list[str]:
    estado = estado_libro.leer_estado(libro.archivo)
    quedaste = decisiones = proximo = ""
    for linea in estado.splitlines():
        limpia = linea.strip()
        baja = clasificar.normalizar(limpia)
        if baja.startswith("quedaste"):
            quedaste = limpia
        elif baja.startswith("decisiones"):
            decisiones = limpia
        elif baja.startswith("proximo paso"):
            proximo = limpia
    if not quedaste:
        resumen = " ".join(libro.resumen.split())
        quedaste = f"Quedaste: {resumen}" if resumen else f"Quedaste en {libro.titulo}."
    if not decisiones:
        decisiones = "Decisiones: ninguna anotada."
    if not proximo:
        proximo = "Próximo paso: elegir un paso de cinco minutos."
    return [_veinte(quedaste), _veinte(decisiones), _veinte(proximo)]


def _veinte(linea: str) -> str:
    palabras = linea.split()
    if len(palabras) <= 20:
        return " ".join(palabras)
    return " ".join(palabras[:20]).rstrip(".,;:") + "."


def recibir(tipo: str, ruta: str, datos: dict[str, object] | None = None, ahora: datetime | None = None) -> dict[str, object]:
    """Registra el evento y dice a qué proyecto cayó. Nunca levanta por una carpeta rara."""
    momento = ahora or datetime.now(timezone.utc)
    libro = libros.por_ruta(ruta)
    tema = libro.tema if libro else None
    anotado = False
    if libro is None and ruta.strip() and es_carpeta_de_proyecto(ruta.strip()):
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
        if tipo == "sesion_inicio":
            _abrir_claude(conexion, carga, tema, ruta, momento)
        elif tipo == "sesion_fin":
            _cerrar_claude(conexion, carga, momento)
        conexion.commit()
    finally:
        conexion.close()

    if tema and tipo == "commit":
        _programar_estado(tema, momento)
    contexto = _contexto_de(ruta) if tipo == "sesion_inicio" else None
    # El episodio, solo de un proyecto: una sesión en la carpeta personal no
    # deja nota a nombre de «juancamilo».
    if tipo == "sesion_fin" and (libro is not None or es_carpeta_de_proyecto(ruta)):
        _programar_cierre(ruta, carga, momento)

    return {"proyecto": tema, "anotado": anotado, "contexto": contexto}


def _contexto_de(ruta: str) -> str | None:
    """Dónde quedó, decisiones y próximo paso. Sin modelo: lo lee del libro."""
    libro = libros.por_ruta(ruta)
    if libro is None:
        return None
    estado = estado_libro.leer_estado(libro.archivo)
    if estado.strip():
        lineas = [f"Proyecto: {libro.titulo}", *estado.splitlines()]
    else:
        lineas = [
            f"Proyecto: {libro.titulo}",
            f"Quedaste: {libro.resumen}",
            "Decisiones: ninguna anotada.",
            "Próximo paso: elegir un paso de cinco minutos.",
        ]
    limpias = [linea.strip() for linea in lineas if linea.strip()]
    return "\n".join(limpias[:15])


def _programar_cierre(ruta: str, datos: dict[str, object], ahora: datetime) -> None:
    """El episodio se escribe al cerrar, también dentro de la ventana de 10 min."""
    import cierre

    if os.environ.get("REMI_CIERRE", "1") == "0":
        return
    if os.environ.get("REMI_TRABAJO_EN_LINEA") == "1":
        cierre.guardar(ruta, datos, ahora)
        return
    hilo = threading.Thread(target=_cierre_seguro, args=(ruta, datos, ahora), daemon=True)
    hilo.start()


def _cierre_seguro(ruta: str, datos: dict[str, object], ahora: datetime) -> None:
    import cierre

    try:
        cierre.guardar(ruta, datos, ahora)
    except Exception as error:  # noqa: BLE001 — cerrar la sesión no puede tumbar el núcleo
        print(f"[cierre] no pude guardarlo ({type(error).__name__})", file=sys.stderr)


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

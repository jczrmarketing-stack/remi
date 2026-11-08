"""El catálogo de YouTube de la bóveda, visto desde Remi (B4).

`sugeridos` solo LEE la base del catálogo (`mode=ro`): si hay un video sin leer que habla de lo que
se pregunta, `preguntar` lo dice. `leer_video` le pide a la bóveda, en su propio entorno, que lo lea
ahora (solo con subtítulos: nunca Whisper). Sin bóveda montada, todo devuelve vacío o lo dice.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import afirmaciones_puente

ID_VIDEO = re.compile(r"[A-Za-z0-9_-]{11}")
_PALABRA = re.compile(r"[a-záéíóúñ0-9]{4,}")


def _ruta() -> Path | None:
    raiz = afirmaciones_puente._raiz_boveda()
    return None if raiz is None else raiz / "cache" / "youtube" / "catalogo.db"


def sugeridos(pregunta: str, n: int = 2, ruta: Path | None = None) -> list[dict]:
    """Pendientes y útiles cuyo título comparte palabras con la pregunta (al menos 2, o la única que haya)."""
    ruta = ruta or _ruta()
    termino = set(_PALABRA.findall(pregunta.lower()))
    if ruta is None or not ruta.exists() or not termino:
        return []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
    except sqlite3.Error:
        return []
    with closing(con):
        try:
            filas = con.execute("SELECT id, canal, titulo, puntaje FROM videos WHERE estado = 'pendiente' AND (relevancia IS NULL OR relevancia >= 2)").fetchall()
        except sqlite3.Error:
            return []
    puntuados = []
    for v in filas:
        hit = len(termino & set(_PALABRA.findall(v["titulo"].lower())))
        if hit >= min(2, len(termino)):
            puntuados.append((hit, v["puntaje"] or 0, dict(v)))
    puntuados.sort(key=lambda x: (-x[0], -x[1]))
    return [x[2] for x in puntuados[:n]]


def aviso(pregunta: str, ruta: Path | None = None) -> str:
    """Las líneas que `preguntar` agrega al final, o ''."""
    v = sugeridos(pregunta, ruta=ruta)
    if not v:
        return ""
    return "Videos sin leer sobre esto (pídelos con `leer_video`):\n" + "\n".join(f"- «{x['titulo'][:90]}» ({x['canal']}) · id {x['id']}" for x in v)


def leer_video(video_id: str, correr=subprocess.run, raiz: Path | None = None) -> str:
    video_id = (video_id or "").strip()
    if not ID_VIDEO.fullmatch(video_id):
        return "Ese id de video no es válido: son 11 caracteres, como el que sale en `preguntar`."
    raiz = raiz or afirmaciones_puente._raiz_boveda()
    if raiz is None:
        return "No encuentro la bóveda ahora: no puedo leer el video."
    python = raiz / ".venv" / "bin" / "python"
    if not python.exists():
        return "No encuentro la bóveda ahora: no puedo leer el video."
    try:
        r = correr([str(python), "youtube_catalogo.py", "--leer", video_id], cwd=raiz, capture_output=True, text=True, timeout=170)
    except subprocess.TimeoutExpired:
        return "Se pasó de tiempo leyendo el video; puede seguir pendiente. Prueba otra vez en un rato."
    except OSError as exc:
        return f"No pude arrancar la lectura: {exc}"
    salida = (r.stdout or "").strip().splitlines()
    ultima = salida[-1] if salida else (r.stderr or "sin respuesta").strip().splitlines()[-1][:160]
    return f"{ultima} (el índice lo recoge en la próxima consulta)" if ultima.startswith("leído") else ultima

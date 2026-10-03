"""Vectores locales de la bóveda (ARQUITECTURA-CEREBRO §3 / Biblia Parte IV·B).

Un vector encuentra QUÉ libro es, nunca trae el libro: la asociación suma
solo títulos a la mente («esto quizá tenga que ver»), el cuerpo nunca viaja
así. Embeddings con Ollama (`nomic-embed-text`, local, gratis — 274 MB,
elegido por tamaño contra `bge-m3` de 1,16 GB, ver docs/BITACORA.md),
guardados en `remi.db` con `sqlite-vec`. Se recalculan solo si el hash del
contenido cambió: no hay por qué volver a pedirle un vector a Ollama a cada
respuesta.

Cubre la bóveda entera: `proyectos/` y `areas/` (los libros), `oficios/`
(`tipo: oficio` en el frontmatter), `episodios/` y `experiencia/` (las
lecciones de T8).
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import httpx
import sqlite_vec

import libros

DIMENSIONES = 768
OLLAMA_BASE = "http://127.0.0.1:11434"
MODELO_EMBEDDINGS = "nomic-embed-text"
TIMEOUT_SEGUNDOS = 10.0

ESQUEMA_VECTORES = f"""
CREATE TABLE IF NOT EXISTS notas_vector (
    id INTEGER PRIMARY KEY,
    ruta TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    hash TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Nota:
    ruta: Path
    tipo: str  # libro | oficio | episodio
    titulo: str
    texto: str  # lo que se vectoriza: título + resumen + claves


def _cargar_extension(conexion: sqlite3.Connection) -> None:
    conexion.enable_load_extension(True)
    sqlite_vec.load(conexion)
    conexion.enable_load_extension(False)


def preparar(conexion: sqlite3.Connection) -> None:
    """Crea la tabla de metadatos y la tabla virtual vec0, si no existen."""
    _cargar_extension(conexion)
    conexion.executescript(ESQUEMA_VECTORES)
    conexion.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS notas_vector_embed USING vec0(embedding float[{DIMENSIONES}])"
    )
    conexion.commit()


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _texto_de(ruta: Path) -> tuple[str, str] | None:
    """(titulo, texto-a-vectorizar), o None si al libro le falta lo mínimo."""
    original = ruta.read_text()
    if not original.startswith("---"):
        return None
    partes = original.split("---", 2)
    if len(partes) < 3:
        return None
    campos = libros._frontmatter(partes[1])
    titulo = campos.get("titulo")
    if not isinstance(titulo, str) or not titulo:
        return None
    resumen = campos.get("resumen")
    resumen_txt = resumen if isinstance(resumen, str) else ""
    claves = campos.get("claves")
    if isinstance(claves, list):
        claves_txt = ", ".join(str(c) for c in claves)
    elif isinstance(claves, str):
        claves_txt = claves.strip("[]")
    else:
        claves_txt = ""
    piezas = [titulo, resumen_txt, claves_txt]
    return titulo, "\n".join(p for p in piezas if p.strip())


def notas() -> list[Nota]:
    """Libros de proyecto y área, oficios, episodios y lecciones (T8) — todo
    lo que se asocia."""
    raiz = libros.carpeta().parent
    resultado: list[Nota] = []
    for carpeta, tipo in (
        (raiz / "proyectos", "libro"),
        (raiz / "areas", "libro"),
        (raiz / "oficios", "oficio"),
        (raiz / "episodios", "episodio"),
        (raiz / "experiencia", "leccion"),
    ):
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.glob("*.md")):
            if libros.fuera_del_estante(ruta):
                continue
            leido = _texto_de(ruta)
            if leido is None:
                continue
            titulo, texto = leido
            resultado.append(Nota(ruta=ruta, tipo=tipo, titulo=titulo, texto=texto))
    return resultado


def embed(texto: str) -> list[float]:
    respuesta = httpx.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": MODELO_EMBEDDINGS, "prompt": texto},
        timeout=TIMEOUT_SEGUNDOS,
    )
    respuesta.raise_for_status()
    vector = respuesta.json()["embedding"]
    if len(vector) != DIMENSIONES:
        raise ValueError(f"el embedding vino de {len(vector)} dimensiones, se esperaban {DIMENSIONES}")
    return vector


def _empaquetar(vector: list[float]) -> bytes:
    return sqlite_vec.serialize_float32(vector)


def actualizar_todos(conexion: sqlite3.Connection) -> int:
    """Recalcula el vector de cada nota cuyo contenido cambió (por hash).
    Devuelve cuántas se (re)calcularon."""
    preparar(conexion)
    recalculadas = 0
    for nota in notas():
        clave = _hash(nota.texto)
        fila = conexion.execute(
            "SELECT id, hash FROM notas_vector WHERE ruta = ?", (str(nota.ruta),)
        ).fetchone()
        if fila is not None and fila["hash"] == clave:
            continue  # la nota no cambió: no hay por qué volver a pedirle a Ollama
        vector = _empaquetar(embed(nota.texto))
        if fila is None:
            cursor = conexion.execute(
                "INSERT INTO notas_vector (ruta, tipo, titulo, hash, actualizado) VALUES (?, ?, ?, ?, datetime('now'))",
                (str(nota.ruta), nota.tipo, nota.titulo, clave),
            )
            id_fila = cursor.lastrowid
            conexion.execute(
                "INSERT INTO notas_vector_embed (rowid, embedding) VALUES (?, ?)", (id_fila, vector)
            )
        else:
            id_fila = fila["id"]
            conexion.execute(
                "UPDATE notas_vector SET tipo = ?, titulo = ?, hash = ?, actualizado = datetime('now') WHERE id = ?",
                (nota.tipo, nota.titulo, clave, id_fila),
            )
            conexion.execute(
                "UPDATE notas_vector_embed SET embedding = ? WHERE rowid = ?", (vector, id_fila)
            )
        recalculadas += 1
    conexion.commit()
    return recalculadas


def asociar(conexion: sqlite3.Connection, mensaje: str, k: int = 5) -> list[str]:
    """Los k títulos más parecidos a `mensaje`. Solo títulos — nunca el cuerpo
    (Ley de la asociación, ARQUITECTURA §3): esto va a la mente como «esto
    quizá tenga que ver», no como una respuesta hecha."""
    preparar(conexion)
    total = conexion.execute("SELECT COUNT(*) AS n FROM notas_vector").fetchone()["n"]
    if total == 0:
        return []
    vector = _empaquetar(embed(mensaje))
    # Se piden de más: una nota archivada o fusionada conserva su vector (la
    # tabla nunca se poda) y se salta acá, igual que un título repetido.
    filas = conexion.execute(
        """
        SELECT n.titulo AS titulo, n.ruta AS ruta
        FROM notas_vector_embed e
        JOIN notas_vector n ON n.id = e.rowid
        WHERE e.embedding MATCH ? AND k = ?
        ORDER BY e.distance
        """,
        (vector, min(k * 3, total)),
    ).fetchall()
    titulos: list[str] = []
    for fila in filas:
        if fila["titulo"] in titulos or libros.fuera_del_estante(Path(fila["ruta"])):
            continue
        titulos.append(fila["titulo"])
        if len(titulos) == k:
            break
    return titulos

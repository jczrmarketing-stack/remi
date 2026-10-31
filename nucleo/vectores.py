"""Vectores locales de la bóveda (ARQUITECTURA-CEREBRO §3 / Biblia Parte IV·B).

Un vector encuentra QUÉ libro es, nunca trae el libro: la asociación suma
solo títulos a la mente («esto quizá tenga que ver»), el cuerpo nunca viaja
así. Embeddings con Ollama (modelo en config/mente.json — hoy `qwen3-embedding:0.6b`, local,
gratis; antes `nomic-embed-text`, ver docs/BITACORA.md),
guardados en `remi.db` con `sqlite-vec`. Se recalculan solo si el hash del
contenido cambió: no hay por qué volver a pedirle un vector a Ollama a cada
respuesta.

Cubre lo que se asocia en mente/: `proyectos/` y `areas/` (los libros, si
los hay), `oficios/`, `episodios/`, `aprendido/` (lecciones y decisiones) y
`mundo/`. La búsqueda general va por `indexar.py`; esto sigue siendo solo la
asociación de títulos.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import httpx
import sqlite_vec

import libros

OLLAMA_BASE = "http://127.0.0.1:11434"
TIMEOUT_SEGUNDOS = 10.0

# El modelo de embeddings vive en config/mente.json (F1.5): cambiarlo es editar
# un archivo, no código. Si cambia, el índice reconstruye sus vectores solo
# (indexar.conectar → alinear). Valores por defecto: el modelo multilingüe
# pequeño de Qwen3 (1024 dimensiones, español incluido, corre en Ollama).
_POR_DEFECTO = {
    "modelo": "qwen3-embedding:0.6b",
    "dimensiones": 1024,
    "prefijo_consulta": "Instruct: Dada una pregunta, recupera las notas que la responden\nQuery: ",
}
_ARCHIVO_CONFIG = Path(__file__).resolve().parent.parent / "config" / "mente.json"


def _configuracion() -> dict:
    datos = dict(_POR_DEFECTO)
    try:
        leido = json.loads(_ARCHIVO_CONFIG.read_text(encoding="utf-8")).get("embeddings", {})
        datos.update({k: v for k, v in leido.items() if k in datos})
    except (OSError, ValueError, AttributeError):
        pass
    if os.environ.get("REMI_EMBED_MODELO"):
        datos["modelo"] = os.environ["REMI_EMBED_MODELO"]
    if os.environ.get("REMI_EMBED_DIM"):
        datos["dimensiones"] = int(os.environ["REMI_EMBED_DIM"])
    if os.environ.get("REMI_EMBED_PREFIJO") is not None:
        datos["prefijo_consulta"] = os.environ["REMI_EMBED_PREFIJO"]
    return datos


_CONFIG = _configuracion()
MODELO_EMBEDDINGS: str = _CONFIG["modelo"]
DIMENSIONES: int = int(_CONFIG["dimensiones"])
PREFIJO_CONSULTA: str = _CONFIG["prefijo_consulta"]
# Lo que había antes de F1.5: una bóveda sin registro de modelo se asume así.
MODELO_ANTERIOR = ("nomic-embed-text", 768)

ESQUEMA_VECTORES = f"""
CREATE TABLE IF NOT EXISTS notas_vector (
    id INTEGER PRIMARY KEY,
    ruta TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    hash TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notas_vector_meta (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
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
    firma = firma_modelo()
    fila = conexion.execute("SELECT valor FROM notas_vector_meta WHERE clave = 'embeddings'").fetchone()
    hay = conexion.execute("SELECT 1 FROM notas_vector LIMIT 1").fetchone() is not None
    previa = fila[0] if fila else (firma_modelo(*MODELO_ANTERIOR) if hay else firma)
    if previa != firma:
        # Otro modelo, otras dimensiones: los vectores viejos no sirven. Se
        # borran y el hash vacío obliga a recalcular cada nota.
        conexion.execute("DROP TABLE IF EXISTS notas_vector_embed")
        conexion.execute("DELETE FROM notas_vector")
    conexion.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS notas_vector_embed USING vec0(embedding float[{DIMENSIONES}])"
    )
    conexion.execute("INSERT OR REPLACE INTO notas_vector_meta (clave, valor) VALUES ('embeddings', ?)", (firma,))
    conexion.commit()


def firma_modelo(modelo: str | None = None, dimensiones: int | None = None) -> str:
    """«modelo|dimensiones»: lo que se guarda para saber con qué se calcularon los vectores."""
    return f"{modelo or MODELO_EMBEDDINGS}|{dimensiones or DIMENSIONES}"


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
        (raiz / "aprendido" / "lecciones", "leccion"),
        (raiz / "aprendido" / "decisiones", "decision"),
        (raiz / "mundo" / "campo", "campo"),
        (raiz / "mundo" / "fuentes", "fuente"),
        (raiz / "mundo" / "investigaciones", "investigacion"),
        (raiz / "referencia", "referencia"),
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


def embed_consulta(pregunta: str) -> list[float]:
    """El vector de una pregunta. Algunos modelos (Qwen3) rinden más si la
    pregunta lleva una instrucción delante; las notas se vectorizan sin ella."""
    return embed(PREFIJO_CONSULTA + pregunta)


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


def asociar(conexion: sqlite3.Connection, mensaje: str, k: int = 5, con_fecha: bool = False) -> list[str]:
    """Los k títulos más parecidos a `mensaje`. Solo títulos — nunca el cuerpo
    (Ley de la asociación, ARQUITECTURA §3): esto va a la mente como «esto
    quizá tenga que ver», no como una respuesta hecha."""
    preparar(conexion)
    total = conexion.execute("SELECT COUNT(*) AS n FROM notas_vector").fetchone()["n"]
    if total == 0:
        return []
    vector = _empaquetar(embed_consulta(mensaje))
    # Se piden de más: una nota archivada o fusionada conserva su vector (la
    # tabla nunca se poda) y se salta acá, igual que un título repetido.
    filas = conexion.execute(
        """
        SELECT n.titulo AS titulo, n.ruta AS ruta, n.tipo AS tipo
        FROM notas_vector_embed e
        JOIN notas_vector n ON n.id = e.rowid
        WHERE e.embedding MATCH ? AND k = ?
        ORDER BY e.distance
        """,
        (vector, min(k * 3, total)),
    ).fetchall()
    titulos: list[str] = []
    for fila in filas:
        if any(t == fila["titulo"] or t.endswith(f": {fila['titulo']}") for t in titulos) or libros.fuera_del_estante(Path(fila["ruta"])):
            continue
        titulos.append(fila["titulo"])
        if con_fecha and fila["tipo"] in ("episodio", "leccion", "decision", "campo"):
            # Lo que pasó lleva su fecha (tarea 3 del 2-oct); un libro no.
            dia = libros.fecha_del_nombre(Path(fila["ruta"]))
            if dia is not None:
                titulos[-1] = f"{libros.fecha_corta(dia)}: {fila['titulo']}"
        if len(titulos) == k:
            break
    return titulos

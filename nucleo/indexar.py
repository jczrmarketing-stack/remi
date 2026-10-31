"""El índice único de la mente: `mente/indice.db`, FTS5 + sqlite-vec, por hash.

El markdown es la verdad; este archivo se puede borrar y se reconstruye. Cubre
`mente/` y, en solo lectura hasta que la ingesta se mude (F1.4), las notas de
la bóveda. Una búsqueda devuelve título, resumen, fecha, estatus y confianza;
el cuerpo solo sale con `leer(id)`.

Los vectores son opcionales: sin Ollama, el texto sigue respondiendo y lo que
faltó se calcula en la siguiente corrida.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import httpx
import sqlite_vec
import yaml

import vectores
import vida

SIN_DATO = "sin dato"
LARGO_RESUMEN = 240
LARGO_PARA_VECTOR = 1500
_RRF = 60
# Un vector siempre trae k vecinos, aunque nada se parezca. La distancia cambia
# con cada consulta, así que el corte es relativo al mejor: medido en la mente
# real, deja lo que toca y saca el relleno (15 %).
_HOLGURA_VECTOR = 1.15
# Diez salidas casi iguales de Rumbo no pueden tapar la lección o el dato de
# campo: una respuesta cruza tipos de conocimiento.
_TOPE_POR_TIPO = 3

_TIPOS_MENTE = (
    ("yo/", "yo"),
    ("negocio/", "negocio"),
    ("oficios/", "oficio"),
    ("mundo/campo/", "campo"),
    ("mundo/fuentes/campo/", "campo"),
    ("mundo/fuentes/", "fuente"),
    ("mundo/repos/", "repo"),
    ("mundo/investigaciones/", "investigacion"),
    ("aprendido/lecciones/", "leccion"),
    ("aprendido/decisiones/", "decision"),
    ("aprendido/diario/", "diario"),
    ("aprendido/", "aprendido"),
    ("bandeja/", "bandeja"),
)

ESQUEMA = f"""
CREATE TABLE IF NOT EXISTS notas (
    rowid INTEGER PRIMARY KEY,
    id TEXT UNIQUE NOT NULL,
    ruta TEXT NOT NULL,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    resumen TEXT NOT NULL,
    fecha TEXT NOT NULL,
    estatus TEXT NOT NULL,
    confianza TEXT NOT NULL,
    hash TEXT NOT NULL,
    hash_vector TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS notas_fts USING fts5(
    titulo, resumen, cuerpo, tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS notas_vec USING vec0(embedding float[{vectores.DIMENSIONES}]);
"""


@dataclass(frozen=True)
class Hallazgo:
    id: str
    tipo: str
    titulo: str
    resumen: str
    fecha: str
    estatus: str
    confianza: str


def ruta_indice() -> Path:
    return vida.MENTE / "indice.db"


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = ruta or ruta_indice()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.enable_load_extension(True)
    sqlite_vec.load(conexion)
    conexion.enable_load_extension(False)
    conexion.executescript(ESQUEMA)
    return conexion


def _tipo(relativa: str, tabla: tuple[tuple[str, str], ...], otro: str) -> str:
    return next((tipo for prefijo, tipo in tabla if relativa.startswith(prefijo)), otro)


def _archivos() -> dict[str, tuple[Path, str]]:
    """{id: (ruta, tipo)}. El id es la ruta relativa a la mente, que es la única
    raíz: las notas de la ingesta viven en `mundo/fuentes/` (F1.4c)."""
    encontrados: dict[str, tuple[Path, str]] = {}
    for ruta in vida.MENTE.rglob("*.md"):
        relativa = ruta.relative_to(vida.MENTE)
        if vida.FUERA_DE_BUSQUEDA.intersection(relativa.parts) or ruta.name == "README.md":
            continue
        encontrados[relativa.as_posix()] = (ruta, _tipo(relativa.as_posix(), _TIPOS_MENTE, "mente"))
    return encontrados


def _campos(texto: str) -> tuple[dict[str, object], str]:
    m = re.match(r"^---\n(.*?)\n---\n?", texto, re.S)
    if not m:
        return {}, texto
    try:
        datos = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return vida._frontmatter(texto)  # type: ignore[return-value]
    return (datos if isinstance(datos, dict) else {}), texto[m.end():]


def _resumen_de(campos: dict[str, object], cuerpo: str) -> str:
    resumen = str(campos.get("resumen") or "").strip()
    if not resumen:
        for bloque in re.split(r"\n\s*\n", re.sub(r"<!--.*?-->", "", cuerpo, flags=re.S)):
            sin_titulos = [l for l in bloque.splitlines() if not l.lstrip().startswith("#")]
            limpio = " ".join(" ".join(sin_titulos).split())
            if limpio and not limpio.startswith(("|", "---")):
                resumen = limpio
                break
    if len(resumen) <= LARGO_RESUMEN:
        return resumen
    return resumen[:LARGO_RESUMEN].rsplit(" ", 1)[0] + " …"


def _fecha_de(campos: dict[str, object], ruta: Path) -> str:
    for clave in ("fecha", "actualizado", "ultima_vez", "fecha_ingesta", "enriquecido"):
        if campos.get(clave):
            return str(campos[clave])
    m = re.match(r"\d{4}-\d{2}-\d{2}", ruta.name)
    return m.group(0) if m else SIN_DATO


def _estatus_de(campos: dict[str, object]) -> str:
    if campos.get("sin_verificar") is True:
        return "sin_verificar"
    return str(campos.get("estatus") or SIN_DATO)


def _confianza_de(campos: dict[str, object]) -> str:
    return str(campos.get("confianza") or campos.get("nivel") or SIN_DATO)


def _quitar(conexion: sqlite3.Connection, rowid: int) -> None:
    conexion.execute("DELETE FROM notas WHERE rowid = ?", (rowid,))
    conexion.execute("DELETE FROM notas_fts WHERE rowid = ?", (rowid,))
    conexion.execute("DELETE FROM notas_vec WHERE rowid = ?", (rowid,))


def _guardar_nota(conexion: sqlite3.Connection, id_nota: str, ruta: Path, tipo: str, texto: str, clave: str) -> None:
    campos, cuerpo = _campos(texto)
    titulo = str(campos.get("titulo") or "").strip() or ruta.stem
    resumen = _resumen_de(campos, cuerpo)
    cursor = conexion.execute(
        "INSERT INTO notas (id, ruta, tipo, titulo, resumen, fecha, estatus, confianza, hash) VALUES (?,?,?,?,?,?,?,?,?)",
        (id_nota, str(ruta), tipo, titulo, resumen, _fecha_de(campos, ruta), _estatus_de(campos), _confianza_de(campos), clave),
    )
    conexion.execute(
        "INSERT INTO notas_fts (rowid, titulo, resumen, cuerpo) VALUES (?,?,?,?)",
        (cursor.lastrowid, titulo, resumen, cuerpo),
    )


def _calcular_vectores(conexion: sqlite3.Connection, tope: int | None) -> int:
    """Los vectores que faltan. Se detiene al primer fallo de Ollama: la
    siguiente corrida retoma lo que quedó."""
    filas = conexion.execute(
        "SELECT n.rowid, n.titulo, n.resumen, n.hash, f.cuerpo FROM notas n JOIN notas_fts f ON f.rowid = n.rowid "
        "WHERE n.hash_vector IS NULL OR n.hash_vector != n.hash"
    ).fetchall()
    calculados = 0
    for fila in filas[:tope]:
        texto = "\n".join((fila["titulo"], fila["resumen"], fila["cuerpo"][:LARGO_PARA_VECTOR]))
        try:
            vector = sqlite_vec.serialize_float32(vectores.embed(texto))
        except (httpx.HTTPError, ValueError, KeyError):
            break
        conexion.execute("DELETE FROM notas_vec WHERE rowid = ?", (fila["rowid"],))
        conexion.execute("INSERT INTO notas_vec (rowid, embedding) VALUES (?, ?)", (fila["rowid"], vector))
        conexion.execute("UPDATE notas SET hash_vector = ? WHERE rowid = ?", (fila["hash"], fila["rowid"]))
        calculados += 1
    return calculados


def actualizar(conexion: sqlite3.Connection, tope_vectores: int | None = None) -> dict[str, int]:
    """Deja el índice igual al disco tocando solo lo que cambió."""
    archivos = _archivos()
    existentes = {f["id"]: f for f in conexion.execute("SELECT rowid, id, hash FROM notas")}
    cambiadas = borradas = 0
    for id_nota, fila in existentes.items():
        if id_nota in archivos:
            continue
        _quitar(conexion, fila["rowid"])
        borradas += 1
    for id_nota, (ruta, tipo) in archivos.items():
        try:
            texto = ruta.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        clave = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        previa = existentes.get(id_nota)
        if previa is not None:
            if previa["hash"] == clave:
                continue
            _quitar(conexion, previa["rowid"])
        _guardar_nota(conexion, id_nota, ruta, tipo, texto, clave)
        cambiadas += 1
    vectores_nuevos = _calcular_vectores(conexion, tope_vectores)
    conexion.commit()
    return {"notas": len(archivos), "cambiadas": cambiadas, "borradas": borradas, "vectores": vectores_nuevos}


def _por_texto(conexion: sqlite3.Connection, q: str, k: int) -> list[int]:
    consulta = vida._consulta_fts(q)
    if not consulta:
        return []
    filas = conexion.execute(
        "SELECT rowid FROM notas_fts WHERE notas_fts MATCH ? ORDER BY bm25(notas_fts, 3, 2, 1) LIMIT ?",
        (consulta, k),
    ).fetchall()
    return [f["rowid"] for f in filas]


def _por_vector(conexion: sqlite3.Connection, q: str, k: int) -> list[int]:
    try:
        vector = sqlite_vec.serialize_float32(vectores.embed(q))
    except (httpx.HTTPError, ValueError, KeyError):
        return []
    filas = conexion.execute(
        "SELECT rowid, distance FROM notas_vec WHERE embedding MATCH ? AND k = ? ORDER BY distance", (vector, k)
    ).fetchall()
    return [f["rowid"] for f in filas if f["distance"] <= filas[0]["distance"] * _HOLGURA_VECTOR]


def buscar(conexion: sqlite3.Connection, q: str, n: int = 8) -> list[Hallazgo]:
    """Texto y vector, fundidos por posición (RRF). Nunca trae el cuerpo."""
    puntos: dict[int, float] = {}
    for lista in (_por_texto(conexion, q, n * 3), _por_vector(conexion, q, n * 3)):
        for posicion, rowid in enumerate(lista):
            puntos[rowid] = puntos.get(rowid, 0.0) + 1 / (_RRF + posicion)
    hallazgos: list[Hallazgo] = []
    por_tipo: dict[str, int] = {}
    for rowid in sorted(puntos, key=lambda r: puntos[r], reverse=True):
        f = conexion.execute(
            "SELECT id, tipo, titulo, resumen, fecha, estatus, confianza FROM notas WHERE rowid = ?", (rowid,)
        ).fetchone()
        if por_tipo.get(f["tipo"], 0) == _TOPE_POR_TIPO:
            continue
        por_tipo[f["tipo"]] = por_tipo.get(f["tipo"], 0) + 1
        hallazgos.append(Hallazgo(*f))
        if len(hallazgos) == n:
            break
    return hallazgos


def leer(conexion: sqlite3.Connection, id_nota: str) -> str | None:
    """El cuerpo de una nota. Solo ids del índice: nunca una ruta libre."""
    fila = conexion.execute("SELECT ruta FROM notas WHERE id = ?", (id_nota,)).fetchone()
    if fila is None:
        return None
    try:
        return Path(fila["ruta"]).read_text(encoding="utf-8")
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza el índice de la mente por hash.")
    parser.add_argument("--reconstruir", action="store_true", help="borra indice.db y lo arma de cero")
    args = parser.parse_args()
    if args.reconstruir:
        ruta_indice().unlink(missing_ok=True)
    conexion = conectar()
    try:
        print(actualizar(conexion))
    finally:
        conexion.close()


if __name__ == "__main__":
    main()

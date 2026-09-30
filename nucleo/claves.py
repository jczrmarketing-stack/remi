"""Claves (3–6 palabras) en el frontmatter de libros, oficios y episodios.

Se generan UNA vez, con Haiku (Ollama de respaldo), desde título + resumen +
cuerpo — y con la misma regla anti-invento que `estado_libro.redactar`: cada
clave tiene que aparecer, literal, en ese mismo texto. Una clave que el
modelo inventó (no está en el texto) se descarta antes de escribir nada.
Alimentan `vectores.py` (título + resumen + claves es lo que se vectoriza).
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import boveda_git
import libros
import pensar

MINIMO = 3
MAXIMO = 6

INSTRUCCIONES = (
    "Te paso el título, el resumen y el cuerpo de una nota. "
    f"Devolvé entre {MINIMO} y {MAXIMO} palabras o frases cortas clave, en minúscula, "
    "separadas por comas, en una sola línea, sin nada antes ni después. "
    "No inventes ninguna palabra que no esté, literal, en el texto que te paso: "
    "cada clave tiene que poder señalarse con el dedo en el título, el resumen o el cuerpo. "
    "Si no hay suficiente texto para sacar tres claves reales, devolvé las que encuentres, "
    "aunque sean menos de tres."
)


def _sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def _aparece_literal(clave: str, fuente_normalizada: str) -> bool:
    clave_normalizada = _sin_acentos(clave.strip())
    return bool(clave_normalizada) and clave_normalizada in fuente_normalizada


def filtrar_inventadas(candidatas: list[str], titulo: str, resumen: str, cuerpo: str) -> list[str]:
    """Descarta cualquier clave que no aparezca, literal, en título+resumen+cuerpo."""
    fuente = _sin_acentos(f"{titulo}\n{resumen}\n{cuerpo}")
    vistas: set[str] = set()
    resultado: list[str] = []
    for candidata in candidatas:
        limpia = candidata.strip().strip(".")
        if not limpia:
            continue
        clave = _sin_acentos(limpia)
        if clave in vistas:
            continue
        if _aparece_literal(limpia, fuente):
            vistas.add(clave)
            resultado.append(limpia.lower())
    return resultado[:MAXIMO]


def _parsear_respuesta(texto: str) -> list[str]:
    primera_linea = texto.strip().splitlines()[0] if texto.strip() else ""
    primera_linea = re.sub(r"(?i)^claves?\s*:\s*", "", primera_linea).strip("[] ")
    return [parte.strip() for parte in primera_linea.split(",") if parte.strip()]


def extraer(titulo: str, resumen: str, cuerpo: str) -> list[str] | None:
    """Entre 3 y 6 claves, ninguna inventada. None si no se pudo sacar ninguna.

    Va por la trastienda de `config/motores.json` (groq → openrouter →
    ollama, por defecto): esto es tarea de fondo, nunca la charla.
    """
    pedido = f"Título: {titulo}\nResumen: {resumen}\nCuerpo:\n{cuerpo[:3000]}"
    pensado = pensar.pensar_con_trastienda(
        pedido, INSTRUCCIONES, aceptar=lambda p: bool(_parsear_respuesta(p.paso_minimo))
    )
    candidatas = _parsear_respuesta(pensado.paso_minimo) if pensado else []
    if not candidatas:
        return None
    filtradas = filtrar_inventadas(candidatas, titulo, resumen, cuerpo)
    return filtradas or None


def _cuerpo_de(texto: str) -> str:
    if not texto.startswith("---"):
        return texto
    partes = texto.split("---", 2)
    return partes[2] if len(partes) >= 3 else texto


def tiene_claves(ruta: Path) -> bool:
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return False
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return False
    return "claves" in libros._frontmatter(partes[1])


def _insertar(ruta: Path, claves: list[str]) -> None:
    original = ruta.read_text()
    if not original.startswith("---"):
        return
    partes = original.split("---", 2)
    if len(partes) < 3:
        return
    frontmatter = partes[1]
    if not frontmatter.endswith("\n"):
        frontmatter += "\n"
    linea = "claves: [" + ", ".join(claves) + "]\n"
    ruta.write_text(f"---{frontmatter}{linea}---{partes[2]}")


def agregar(ruta: Path, tipo: str) -> list[str] | None:
    """Genera y escribe las claves de un archivo que todavía no las tiene.

    Devuelve las claves escritas, o None si no se pudo (sin texto suficiente,
    o el archivo ya las tenía). El archivo queda con un snapshot de la bóveda
    antes y después, como cualquier otra escritura de Remi ahí."""
    if tiene_claves(ruta):
        return None
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None
    campos = libros._frontmatter(partes[1])
    titulo = campos.get("titulo")
    if not isinstance(titulo, str) or not titulo:
        return None
    resumen = campos.get("resumen")
    resumen_txt = resumen if isinstance(resumen, str) else ""
    cuerpo = _cuerpo_de(texto)
    claves = extraer(titulo, resumen_txt, cuerpo)
    if not claves:
        print(f"[claves] {ruta.name}: no saqué ninguna clave real, lo dejo sin tocar", file=sys.stderr)
        return None
    boveda_git.snapshot_antes(f"generar claves de {ruta.name} ({tipo})")
    _insertar(ruta, claves)
    boveda_git.snapshot_despues(f"bóveda: claves de {ruta.name} ({tipo}) — {', '.join(claves)}")
    return claves


def generar_faltantes() -> dict[str, list[str] | None]:
    """Recorre proyectos/, areas/, oficios/ y episodios/ y les agrega claves
    a los que no las tengan. Devuelve {nombre_de_archivo: claves|None}."""
    raiz = libros.carpeta().parent
    resultado: dict[str, list[str] | None] = {}
    for carpeta, tipo in (
        (raiz / "proyectos", "libro"),
        (raiz / "areas", "libro"),
        (raiz / "oficios", "oficio"),
        (raiz / "episodios", "episodio"),
    ):
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.glob("*.md")):
            if tiene_claves(ruta):
                continue
            resultado[str(ruta.relative_to(raiz))] = agregar(ruta, tipo)
    return resultado


if __name__ == "__main__":
    for archivo, claves in generar_faltantes().items():
        print(f"{archivo}: {claves}")

"""Un proyecto es una carpeta. El libro lo dice en `ruta:` del frontmatter.

Una o varias. Un commit o una sesión caen en el libro cuya ruta contiene
esa carpeta. `remi` no se traga a `remi-mente`: se compara por componentes,
no por prefijo de texto. La bóveda es la de siempre (`REMI_CONOCIMIENTO`,
o conocimiento/proyectos, que en esta máquina apunta a remi-mente).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "conocimiento" / "proyectos"


@dataclass(frozen=True)
class Libro:
    archivo: Path
    titulo: str
    tema: str
    resumen: str
    rutas: tuple[str, ...]


def carpeta() -> Path:
    return Path(os.environ.get("REMI_CONOCIMIENTO") or CARPETA)


def _rutas_de(valor: str | list[str] | None) -> tuple[str, ...]:
    if valor is None:
        return ()
    if isinstance(valor, list):
        crudas = valor
    else:
        crudas = [parte.strip() for parte in valor.split(",")]
    limpias: list[str] = []
    for ruta in crudas:
        texto = ruta.strip().strip('"').strip("'")
        if texto:
            limpias.append(str(Path(texto).expanduser()))
    return tuple(limpias)


def _frontmatter(bloque: str) -> dict[str, str | list[str]]:
    """`clave: valor`, o `clave:` seguida de líneas `- item`."""
    campos: dict[str, str | list[str]] = {}
    lineas = bloque.splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if not linea.strip() or linea.lstrip().startswith("- "):
            i += 1
            continue
        if ":" not in linea:
            i += 1
            continue
        clave, valor = linea.split(":", 1)
        clave = clave.strip()
        valor = valor.strip()
        if valor == "":
            items: list[str] = []
            j = i + 1
            while j < len(lineas) and lineas[j].lstrip().startswith("- "):
                items.append(lineas[j].split("-", 1)[1].strip())
                j += 1
            if items:
                campos[clave] = items
                i = j
                continue
        campos[clave] = valor
        i += 1
    return campos


def leer(ruta: Path) -> Libro | None:
    """None si le falta titulo, tema o resumen."""
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None
    campos = _frontmatter(partes[1])
    titulo = campos.get("titulo")
    tema = campos.get("tema")
    resumen = campos.get("resumen")
    if not all(isinstance(c, str) and c for c in (titulo, tema, resumen)):
        return None
    assert isinstance(titulo, str) and isinstance(tema, str) and isinstance(resumen, str)
    return Libro(ruta, titulo, tema, resumen, _rutas_de(campos.get("ruta")))


def listar() -> list[Libro]:
    origen = carpeta()
    if not origen.is_dir():
        return []
    libros: list[Libro] = []
    for ruta in sorted(origen.glob("*.md")):
        libro = leer(ruta)
        if libro is not None:
            libros.append(libro)
    return libros


def _contiene(raiz: str, candidato: str) -> bool:
    """La carpeta del evento está dentro de la ruta del libro, o es ella."""
    try:
        Path(candidato).expanduser().resolve().relative_to(Path(raiz).expanduser().resolve())
    except (ValueError, OSError):
        return False
    return True


def por_ruta(ruta: str) -> Libro | None:
    """El libro de la ruta más específica que contiene esta carpeta."""
    mejor: Libro | None = None
    mejor_largo = -1
    for libro in listar():
        for candidata in libro.rutas:
            if _contiene(candidata, ruta) and len(candidata) > mejor_largo:
                mejor = libro
                mejor_largo = len(candidata)
    return mejor

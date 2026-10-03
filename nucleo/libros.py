"""Un proyecto es una carpeta. El libro lo dice en `ruta:` del frontmatter.

Una o varias. Un commit o una sesión caen en el libro cuya ruta contiene
esa carpeta. `remi` no se traga a `remi-mente`: se compara por componentes,
no por prefijo de texto. La bóveda es la de siempre (`REMI_CONOCIMIENTO`,
o conocimiento/proyectos, que en esta máquina apunta a remi-mente).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

CARPETA = Path(__file__).resolve().parent.parent / "conocimiento" / "proyectos"


@dataclass(frozen=True)
class Fase:
    nombre: str
    alcance: str
    monto: float | None
    listo_cuando: str
    estado: str


@dataclass(frozen=True)
class Libro:
    archivo: Path
    titulo: str
    tema: str
    resumen: str
    rutas: tuple[str, ...]
    compartible: bool = False
    # «tipo: propio|cliente» y «fases:» (lista de Fase) — encargo H, el
    # camino sale del SOP. Ninguno de los dos es obligatorio: la mayoría de
    # los libros de hoy no los tienen todavía.
    tipo: str | None = None
    fases: tuple[Fase, ...] = ()
    # Forma A (T2): el cliente del proyecto, del frontmatter `cliente:`.
    # None si no es de un tipo cliente o nadie lo escribió todavía.
    cliente: str | None = None


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


_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def fecha_corta(dia: date) -> str:
    """«30-sep»: la fecha que acompaña a todo lo viejo que entra al contexto
    (encargo del 2-oct, tarea 3: un 401 del 30-sep salió como si pasara hoy)."""
    return f"{dia.day}-{_MESES[dia.month - 1]}"


def fecha_del_nombre(ruta: Path) -> date | None:
    """La fecha del nombre de un episodio o una lección (AAAA-MM-DD-…)."""
    try:
        return date.fromisoformat(ruta.name[:10])
    except ValueError:
        return None


def fuera_del_estante(ruta: Path) -> bool:
    """Una nota de la bóveda archivada (`estado: archivada`) o fusionada en
    otra (`fusionado_en: …`). Sigue en disco —nunca se borra— pero ningún
    lector la cuenta: ni la asociación por vectores, ni las claves, ni la
    noche, ni «el último episodio» (plan de cierre, F3.2 y la limpieza del
    2/10/2026)."""
    try:
        texto = ruta.read_text()
    except OSError:
        return True
    if not texto.startswith("---"):
        return False
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return False
    campos = _frontmatter(partes[1])
    return campos.get("estado") == "archivada" or bool(campos.get("fusionado_en"))


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


def _fases_de(bloque: str) -> tuple[Fase, ...]:
    """«fases» es la única clave del frontmatter con estructura anidada
    (lista de diccionarios). El resto de `_frontmatter()` es a mano porque
    `resumen`/`titulo` traen dos puntos sueltos («App web: mandás…») que
    rompen YAML de verdad — probado: `yaml.safe_load()` del frontmatter
    entero falla en varios libros reales. Acá sí vale la pena: se aísla
    solo el bloque de «fases:» (desde esa línea hasta la próxima clave de
    primer nivel) y se lo pasa a `yaml.safe_load()`, aislado del resto.
    Cualquier error de forma deja fases vacío — nunca rompe `leer()`."""
    lineas = bloque.splitlines()
    inicio = next((i for i, l in enumerate(lineas) if l.rstrip() == "fases:" or l.startswith("fases:")), None)
    if inicio is None:
        return ()
    fin = len(lineas)
    for j in range(inicio + 1, len(lineas)):
        if lineas[j].strip() and not lineas[j].startswith((" ", "\t", "-")):
            fin = j
            break
    try:
        datos = yaml.safe_load("\n".join(lineas[inicio:fin]))
    except yaml.YAMLError:
        return ()
    crudas = datos.get("fases") if isinstance(datos, dict) else None
    if not isinstance(crudas, list):
        return ()
    resultado: list[Fase] = []
    for item in crudas:
        if not isinstance(item, dict):
            continue
        monto_crudo = item.get("monto")
        try:
            monto = float(monto_crudo) if monto_crudo is not None else None
        except (TypeError, ValueError):
            monto = None
        resultado.append(
            Fase(
                nombre=str(item.get("nombre") or ""),
                alcance=str(item.get("alcance") or ""),
                monto=monto,
                listo_cuando=str(item.get("listo_cuando") or ""),
                estado=str(item.get("estado") or ""),
            )
        )
    return tuple(resultado)


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
    compartible = str(campos.get("compartible", "")).strip().lower() == "true"
    tipo_crudo = campos.get("tipo")
    tipo = tipo_crudo if isinstance(tipo_crudo, str) and tipo_crudo in ("propio", "cliente") else None
    fases = _fases_de(partes[1])
    cliente_crudo = campos.get("cliente")
    cliente = cliente_crudo if isinstance(cliente_crudo, str) and cliente_crudo else None
    return Libro(ruta, titulo, tema, resumen, _rutas_de(campos.get("ruta")), compartible, tipo, fases, cliente)


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


def _raiz_principal_de_worktree(gitfile: Path) -> Path | None:
    """`gitfile` es el `.git` (archivo, no carpeta) de un worktree: dice
    `gitdir: <repo-principal>/.git/worktrees/<nombre>`. Devuelve la raíz del
    repo principal, o None si el archivo no tiene esa forma."""
    try:
        contenido = gitfile.read_text().strip()
    except OSError:
        return None
    if not contenido.startswith("gitdir:"):
        return None
    gitdir = Path(contenido.split(":", 1)[1].strip())
    partes = gitdir.parts
    if "worktrees" not in partes or partes[-2] != "worktrees":
        return None
    indice_git = partes.index("worktrees") - 1
    if indice_git < 0 or partes[indice_git] != ".git":
        return None
    return Path(*partes[:indice_git])


def _raiz_real(ruta: str) -> str:
    """Si `ruta` cae dentro de un worktree de git, la reescribe con la raíz
    del repo principal y el mismo sufijo relativo — un commit en
    `remi-nucleo` (worktree de `remi`) cae en el libro de `remi`, igual que
    uno hecho en el checkout principal."""
    camino = Path(ruta).expanduser().resolve()
    for candidato in (camino, *camino.parents):
        git = candidato / ".git"
        if git.is_file():
            principal = _raiz_principal_de_worktree(git)
            if principal is None:
                return ruta
            return str(principal / camino.relative_to(candidato))
        if git.is_dir():
            return ruta
    return ruta


def _contiene(raiz: str, candidato: str) -> bool:
    """La carpeta del evento está dentro de la ruta del libro, o es ella."""
    try:
        Path(candidato).expanduser().resolve().relative_to(Path(raiz).expanduser().resolve())
    except (ValueError, OSError):
        return False
    return True


def por_ruta(ruta: str) -> Libro | None:
    """El libro de la ruta más específica que contiene esta carpeta."""
    ruta = _raiz_real(ruta)
    mejor: Libro | None = None
    mejor_largo = -1
    for libro in listar():
        for candidata in libro.rutas:
            if _contiene(candidata, ruta) and len(candidata) > mejor_largo:
                mejor = libro
                mejor_largo = len(candidata)
    return mejor


_TITULO_REGLAS = "## Reglas de este proyecto"


def reglas_de_este_proyecto(archivo: Path) -> list[str]:
    """Las líneas de «## Reglas de este proyecto» (T9.2) — [] si el libro
    no tiene ninguna todavía."""
    texto = archivo.read_text()
    if texto.startswith("---"):
        partes = texto.split("---", 2)
        cuerpo = partes[2] if len(partes) >= 3 else texto
    else:
        cuerpo = texto
    lineas = cuerpo.splitlines()
    inicio = next((i for i, l in enumerate(lineas) if l.strip() == _TITULO_REGLAS), None)
    if inicio is None:
        return []
    fin = next((j for j in range(inicio + 1, len(lineas)) if lineas[j].startswith("## ")), len(lineas))
    return [l.strip(" -") for l in lineas[inicio + 1 : fin] if l.strip()]

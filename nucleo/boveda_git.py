"""Cada escritura de Remi en la bóveda queda con revert real.

El incidente del 30-sep (docs/BITACORA.md, «0b Haiku escribe el Estado — y
un incidente con los libros reales») pisó cuatro libros sin que hubiera con
qué revertir: la bóveda no tenía git. Ahora sí. Antes de que Remi escriba
algo en la bóveda (Estado, episodio, claves, consolidación), un commit deja
el estado previo a salvo; después de escribir, otro commit dice qué se tocó
y por qué. Cualquier pisón, con `git log` + `git diff`/`git revert` en la
bóveda, se puede deshacer.

Si la bóveda no es un repo git todavía, o `git` no está disponible, esto no
rompe nada: no deja rastro y lo anota una vez en stderr.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import libros


def raiz() -> Path:
    """La carpeta de la bóveda (padre de proyectos/, episodios/, oficios/)."""
    return libros.carpeta().parent.resolve()


def _es_repo(carpeta: Path) -> bool:
    return (carpeta / ".git").is_dir()


def _hay_cambios(carpeta: Path) -> bool:
    resultado = subprocess.run(
        ["git", "-C", str(carpeta), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    return bool(resultado.stdout.strip())


# F3.5 / F4.2: la bóveda de verdad. Una prueba nunca la commitea: si lo
# intenta, revienta (fuera del try de abajo, para que la suite falle en rojo
# en vez de tragárselo).
BOVEDA_REAL = (Path(__file__).resolve().parent.parent / "conocimiento").resolve()


def _commit(mensaje: str) -> None:
    carpeta = raiz()
    if os.environ.get("PYTEST_CURRENT_TEST") and carpeta == BOVEDA_REAL:
        raise RuntimeError(f"una prueba intentó commitear la bóveda real: {mensaje}")
    if not _es_repo(carpeta):
        return
    try:
        if not _hay_cambios(carpeta):
            return
        subprocess.run(["git", "-C", str(carpeta), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(carpeta), "commit", "-m", mensaje],
            check=True, capture_output=True,
        )
    except Exception as error:  # noqa: BLE001 — un commit de la bóveda no puede tumbar el núcleo
        print(f"[boveda_git] no pude commitear ({type(error).__name__}): {mensaje}", file=sys.stderr)


def snapshot_antes(que_va_a_tocar: str) -> None:
    """Deja a salvo lo que había, antes de que Remi lo pise."""
    _commit(f"bóveda: snapshot antes de tocar {que_va_a_tocar}")


def snapshot_despues(que_toco_y_por_que: str) -> None:
    """Qué cambió y por qué, después de escribir."""
    _commit(que_toco_y_por_que)

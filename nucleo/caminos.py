"""La sección «## Camino» de un libro de proyecto: hitos «- [ ] …» / «- [x] …».

Se lee siempre; se escribe solo para marcar un hito [x] — y solo cuando ya
existe una tarea con ese mismo texto en estado `hecha`. Nunca se escribe un
hito nuevo ni se reordena nada: eso es cosa de quien edita el libro a mano.

El chequeo es reactivo (se hace al leer, no al cerrar una tarea): así no
hace falta tocar las rutas que ya cierran tareas en servidor.py (/mensaje,
POST /tarea/{id}/estado), que no son de esta tarea.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import libros

TITULO = "## Camino"


@dataclass(frozen=True)
class Hito:
    texto: str
    hecho: bool


def _cuerpo(texto: str) -> str:
    if not texto.startswith("---"):
        return texto
    partes = texto.split("---", 2)
    return partes[2] if len(partes) >= 3 else texto


def _indice(lineas: list[str]) -> int | None:
    for i, linea in enumerate(lineas):
        if linea.strip() == TITULO:
            return i
    return None


def _fin(lineas: list[str], inicio: int) -> int:
    for j in range(inicio + 1, len(lineas)):
        if lineas[j].startswith("## "):
            return j
    return len(lineas)


def _parsear(cuerpo: str) -> list[Hito]:
    lineas = cuerpo.splitlines()
    inicio = _indice(lineas)
    if inicio is None:
        return []
    fin = _fin(lineas, inicio)
    hitos: list[Hito] = []
    for linea in lineas[inicio + 1 : fin]:
        limpia = linea.strip()
        if limpia.startswith("- [x]") or limpia.startswith("- [X]"):
            hitos.append(Hito(texto=limpia[5:].strip(), hecho=True))
        elif limpia.startswith("- [ ]"):
            hitos.append(Hito(texto=limpia[5:].strip(), hecho=False))
    return hitos


def leer_hitos(archivo: Path) -> list[Hito]:
    """Los hitos del libro, en el orden en que están escritos."""
    return _parsear(_cuerpo(archivo.read_text()))


def siguiente_abierto(hitos: list[Hito]) -> Hito | None:
    return next((h for h in hitos if not h.hecho), None)


def _marcar(archivo: Path, texto_hito: str) -> None:
    """Pasa «- [ ] texto» a «- [x] texto» dentro de ## Camino. El resto del
    libro queda intacto: solo se toca esa línea."""
    original = archivo.read_text()
    lineas = original.splitlines()
    inicio = _indice(lineas)
    if inicio is None:
        return
    fin = _fin(lineas, inicio)
    for i in range(inicio + 1, fin):
        limpia = lineas[i].strip()
        if limpia.startswith("- [ ]") and limpia[5:].strip() == texto_hito:
            sangria = lineas[i][: len(lineas[i]) - len(lineas[i].lstrip())]
            lineas[i] = f"{sangria}- [x] {texto_hito}"
            break
    else:
        return
    archivo.write_text("\n".join(lineas) + ("\n" if original.endswith("\n") else ""))


def marcar_hitos_cumplidos(conexion: sqlite3.Connection, libro: libros.Libro) -> list[Hito]:
    """Revisa cada hito abierto contra `tareas`: si hay una tarea `hecha`
    con el mismo título, la marca [x] en el archivo. Devuelve los hitos ya
    actualizados (para que quien llame no tenga que releer el archivo)."""
    hitos = leer_hitos(libro.archivo)
    cambiaron = False
    actualizados: list[Hito] = []
    for hito in hitos:
        if hito.hecho:
            actualizados.append(hito)
            continue
        fila = conexion.execute(
            "SELECT 1 FROM tareas WHERE titulo = ? AND estado = 'hecha' LIMIT 1",
            (hito.texto,),
        ).fetchone()
        if fila is not None:
            _marcar(libro.archivo, hito.texto)
            actualizados.append(Hito(texto=hito.texto, hecho=True))
            cambiaron = True
        else:
            actualizados.append(hito)
    return leer_hitos(libro.archivo) if cambiaron else actualizados


def hitos_de_tema(conexion: sqlite3.Connection, tema: str) -> tuple[list[Hito], Hito | None] | None:
    """(hitos, siguiente abierto) del libro de ese tema. None si no hay
    libro con ese tema."""
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        return None
    hitos = marcar_hitos_cumplidos(conexion, libro)
    return hitos, siguiente_abierto(hitos)

"""Suite de INV3RZA (4-nov): lo que el panel escribe en la mente desde los pisos.

- POST /suite/guardar: manda una idea (un tema del Editor, por ejemplo) al cajón de otro piso,
  mente/negocio/cajon/<piso>.md, una línea por idea. suite.py la pinta en «Ideas guardadas».
- GET/POST /suite/norte: el Norte de INV3RZA, guiado de a una pregunta, en mente/negocio/norte.md.
  Se puede dejar a medias y retomar: cada respuesta se guarda al instante.

La mente se ubica con REMI_MENTE (leída en cada llamada, así las pruebas usan tmp_path).
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import suite

router = APIRouter(prefix="/suite", tags=["suite"])

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
LINEA_CAJON = re.compile(r"^- (\d{4}-\d{2}-\d{2}) · (.*?)(?: \(desde ([^()]*)\))?\s*$")
PREGUNTAS = (
    "¿A quién le sirves?",
    "¿Qué problema le resuelves?",
    "¿Qué vendes y cuánto cuesta?",
    "¿Cómo vas a conseguir clientes sin contratar a nadie?",
    "¿Qué no vas a hacer?",
    "En una frase: ¿qué es INV3RZA en un año?",
)
# Cómo se llama cada respuesta en la lista «Tu Norte» de Dirección.
CORTAS = ("A quién", "Problema", "Oferta y precio", "Clientes", "Lo que no", "En un año")
ENCABEZADO = re.compile(r"^## (\d)\. .*$", re.MULTILINE)


def mente() -> Path:
    return Path(os.environ.get("REMI_MENTE") or suite.MENTE)


def _limpio(texto: str, maximo: int) -> str:
    return re.sub(r"\s+", " ", texto).strip()[:maximo].strip()


# ---------- Cajón de ideas por piso ----------

def guardar_en_cajon(piso: str, texto: str, fuente: str = "", hoy: date | None = None, raiz: Path | None = None) -> str:
    """Agrega una línea al cajón del piso y la devuelve. Crea el archivo si no existe."""
    nombres = {pid: nombre for pid, nombre, _, _ in suite.PISOS}
    if piso not in nombres:
        raise ValueError(f"piso desconocido: {piso}")
    texto = _limpio(texto, 300).replace(" · ", ", ")
    fuente = _limpio(fuente, 60).replace("(", "").replace(")", "")
    if not texto:
        raise ValueError("texto vacío")
    hoy = hoy or date.today()
    ruta = (raiz or mente()) / "negocio" / "cajon" / f"{piso}.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        ruta.write_text(
            f"---\ntipo: cajon\npiso: {piso}\nfecha: {hoy.isoformat()}\n"
            f"fuente: ideas mandadas desde otros pisos de la Suite. Lo lee la Suite en «Ideas guardadas».\n---\n"
            f"# Ideas guardadas para {nombres[piso]}\n\n",
            encoding="utf-8",
        )
    linea = f"- {hoy.isoformat()} · {texto}" + (f" (desde {fuente})" if fuente else "")
    with ruta.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")
    return linea


def leer_cajon(piso: str, raiz: Path | None = None, cuantas: int = 5) -> list[list[str]]:
    """Las ideas del cajón, las más nuevas primero, como filas [texto, «4 nov, desde X»]."""
    try:
        lineas = ((raiz or mente()) / "negocio" / "cajon" / f"{piso}.md").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    filas = []
    for linea in reversed(lineas):
        m = LINEA_CAJON.match(linea)
        if not m:
            continue
        a, mes, dia = (int(x) for x in m.group(1).split("-"))
        cuando = f"{dia} {MESES[mes - 1]}" if 1 <= mes <= 12 else m.group(1)
        filas.append([m.group(2), f"{cuando}, desde {m.group(3)}" if m.group(3) else cuando])
        if len(filas) >= cuantas:
            break
    return filas


# ---------- El Norte ----------

def leer_norte(raiz: Path | None = None) -> dict:
    """{"existe", "preguntas": [{n, pregunta, respuesta}], "completo", "siguiente", "estatus"}."""
    respuestas = [""] * len(PREGUNTAS)
    existe = False
    try:
        texto = ((raiz or mente()) / "negocio" / "norte.md").read_text(encoding="utf-8")
        existe = True
    except OSError:
        texto = ""
    if texto.startswith("---"):
        texto = texto.split("---", 2)[2] if texto.count("---") >= 2 else ""
    marcas = list(ENCABEZADO.finditer(texto))
    for i, m in enumerate(marcas):
        n = int(m.group(1))
        if 1 <= n <= len(PREGUNTAS):
            fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
            respuestas[n - 1] = texto[m.end():fin].strip()
    faltan = [i + 1 for i, r in enumerate(respuestas) if not r]
    return {
        "existe": existe,
        "preguntas": [{"n": i + 1, "pregunta": p, "respuesta": respuestas[i]} for i, p in enumerate(PREGUNTAS)],
        "completo": not faltan,
        "siguiente": faltan[0] if faltan else None,
        "estatus": "confirmado" if not faltan else "borrador",
    }


def guardar_norte(n: int, respuesta: str, hoy: date | None = None, raiz: Path | None = None) -> dict:
    if not 1 <= n <= len(PREGUNTAS):
        raise ValueError(f"pregunta desconocida: {n}")
    respuesta = respuesta.strip()
    if not respuesta:
        raise ValueError("respuesta vacía")
    actual = leer_norte(raiz)
    respuestas = [p["respuesta"] for p in actual["preguntas"]]
    respuestas[n - 1] = respuesta
    completo = all(respuestas)
    hoy = hoy or date.today()
    cuerpo = "".join(f"## {i + 1}. {p}\n\n{respuestas[i]}\n\n" if respuestas[i] else f"## {i + 1}. {p}\n\n" for i, p in enumerate(PREGUNTAS))
    ruta = (raiz or mente()) / "negocio" / "norte.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f".norte.{os.getpid()}.tmp")
    tmp.write_text(
        f"---\ntipo: negocio\nfecha: {hoy.isoformat()}\nfuente: preguntas guiadas de la Suite (Dirección). Lo lee la Suite en «Tu Norte».\n"
        f"estatus: {'confirmado' if completo else 'borrador'}\n---\n# El Norte de INV3RZA\n\n{cuerpo}",
        encoding="utf-8",
    )
    os.replace(tmp, ruta)
    return leer_norte(raiz)


def lista_tu_norte(norte: dict) -> dict | None:
    """La lista «Tu Norte» para Dirección: solo si el Norte existe y tiene alguna respuesta."""
    filas = []
    for p in norte.get("preguntas") or []:
        r = _limpio(p["respuesta"], 400)
        if r:
            filas.append([r if len(r) <= 90 else r[:88].rsplit(" ", 1)[0] + "…", CORTAS[p["n"] - 1]])
    if not norte.get("existe") or not filas:
        return None
    return {"titulo": "Tu Norte", "fuente": "de norte.md" if norte.get("completo") else "a medias, de norte.md", "filas": filas}


# ---------- Rutas ----------

class Guardar(BaseModel):
    piso: str
    texto: str = Field(min_length=1, max_length=2000)
    fuente: str = ""


class RespuestaNorte(BaseModel):
    n: int
    respuesta: str = Field(min_length=1, max_length=8000)


@router.post("/guardar")
def guardar(cuerpo: Guardar) -> dict:
    if cuerpo.piso not in {pid for pid, *_ in suite.PISOS}:
        raise HTTPException(422, "Ese piso no existe.")
    try:
        linea = guardar_en_cajon(cuerpo.piso, cuerpo.texto, cuerpo.fuente)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    nombre = next(nombre for pid, nombre, *_ in suite.PISOS if pid == cuerpo.piso)
    return {"ok": True, "piso": cuerpo.piso, "nombre": nombre, "linea": linea}


@router.get("/norte")
def norte() -> dict:
    return leer_norte()


@router.post("/norte")
def norte_guardar(cuerpo: RespuestaNorte) -> dict:
    try:
        return guardar_norte(cuerpo.n, cuerpo.respuesta)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

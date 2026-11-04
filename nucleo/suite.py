"""La Suite de INV3RZA (3-nov): todo lo que pintan el inicio, el edificio y los 7 pisos, en una sola respuesta.

Fuentes, en orden de verdad:
- la tarea de hoy de Remi (remi.db) manda sobre el foco escrito en la ficha;
- mente/negocio/suite.md: el Norte, el foco por defecto y, por piso, tu paso y lo que entra;
- en vivo: los temas del Editor (mente/mundo/newsletter/_editor-*.json), la bóveda (proceso de
  ingesta, catálogo, agenda.json) y el estado de cada agente (agentes_estado).
Nada se inventa: si una fuente falta, esa parte sale vacía con su mensaje, nunca con relleno.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from datetime import date, datetime
from pathlib import Path

import yaml

import agentes_estado
import donde_boveda

MENTE = Path(os.environ.get("REMI_MENTE") or Path.home() / "proyectos" / "mente")
PISOS = [  # id, nombre, para qué sirve, color
    ("direccion", "Dirección", "Hacia dónde va todo.", "#FF2D55"),
    ("inteligencia", "Inteligencia", "Qué cambió y qué te sirve.", "#5AE4E0"),
    ("oferta", "Oferta", "Qué vendes y a quién.", "#FFD60A"),
    ("marketing", "Marketing", "Que te encuentren.", "#FF9F0A"),
    ("ventas", "Ventas", "De conversación a dinero.", "#C6F432"),
    ("ingenieria", "Ingeniería", "Lo que construye y mantiene todo.", "#3D7BFF"),
    ("administracion", "Administración", "Dinero, trámites y facturas.", "#BF5AF2"),
]
ACCION_TEMA = {"hoy": "Hoy", "tener en cuenta": "Tener en cuenta", "solo saber": "Solo saber"}


def leer_ficha(ruta: Path | None = None) -> dict:
    ruta = ruta or MENTE / "negocio" / "suite.md"
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not texto.startswith("---"):
        return {}
    try:
        return yaml.safe_load(texto.split("---", 2)[1]) or {}
    except yaml.YAMLError:
        return {}


def temas_del_editor(hoy: date, carpeta: Path | None = None) -> tuple[list[dict], str]:
    """Los temas del último día que escribió el Editor (hoy o antes). Devuelve (temas, fecha)."""
    carpeta = carpeta or MENTE / "mundo" / "newsletter"
    archivos = sorted(p for p in carpeta.glob("_editor-*.json") if p.stem[8:] <= hoy.isoformat()) if carpeta.exists() else []
    for archivo in reversed(archivos):
        try:
            temas = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(temas, list) and temas:
            return temas, archivo.stem[8:]
    return [], ""


def boveda_en_vivo(raiz: Path | None = None, hoy: date | None = None) -> dict:
    raiz = raiz or donde_boveda.ubicar()
    salida = {"leyendo": False, "calificados": None, "leidos_hoy": None, "agenda": {}}
    if raiz is None:
        return salida
    try:
        salida["leyendo"] = subprocess.run(["pgrep", "-f", "youtube_catalogo.py --continuo"], capture_output=True, timeout=3).returncode == 0
    except (OSError, subprocess.SubprocessError):
        pass
    bd = raiz / "cache" / "youtube" / "catalogo.db"
    if bd.exists():
        try:
            con = sqlite3.connect(f"file:{bd}?mode=ro", uri=True, timeout=2)
            salida["calificados"] = con.execute("SELECT count(*) FROM videos WHERE relevancia IS NOT NULL").fetchone()[0]
            salida["leidos_hoy"] = con.execute("SELECT count(*) FROM videos WHERE ingerido_en LIKE ?", ((hoy or date.today()).isoformat() + "%",)).fetchone()[0]
            con.close()
        except sqlite3.Error:
            pass
    try:
        salida["agenda"] = json.loads((raiz / "cache" / "agenda.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return salida


def _hora(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%-H:%M") if iso else ""
    except ValueError:
        return ""


def armar(foco_de_hoy: dict | None = None, hoy: date | None = None, ficha: dict | None = None,
          boveda: dict | None = None, temas: tuple[list[dict], str] | None = None, agentes: dict | None = None) -> dict:
    hoy = hoy or date.today()
    ficha = ficha if ficha is not None else leer_ficha()
    boveda = boveda if boveda is not None else boveda_en_vivo(hoy=hoy)
    temas, fecha_temas = temas if temas is not None else temas_del_editor(hoy)
    if agentes is None:
        agentes = {k: agentes_estado.vivo(k, v) for k, v in agentes_estado.catalogo().items()}
    pisos_ficha = ficha.get("pisos") or {}
    foco = foco_de_hoy or ficha.get("foco") or {"titulo": "", "contexto": ""}

    pisos = []
    for pid, nombre, para, color in PISOS:
        datos = pisos_ficha.get(pid) or {}
        entra = [dict(e) for e in (datos.get("entra") or [])]
        paso = dict(datos.get("paso") or {})
        if pid == "inteligencia":
            if temas:
                primero = next((t for t in temas if t.get("accion") == "hoy"), temas[0])
                paso = {"titulo": primero.get("titular", ""), "contexto": ("Para ti: " + primero["para_ti"]) if primero.get("para_ti") else "", "accion": "Leer en Notion"}
            entra = [
                {"titulo": "Temas del Editor", "fuente": f"del {fecha_temas}" if fecha_temas and fecha_temas != hoy.isoformat() else "de hoy",
                 "filas": [[t.get("titular", ""), ACCION_TEMA.get(t.get("accion", ""), "")] for t in temas[:5]],
                 "vacio": "El Editor publica a las 11:00."},
                {"titulo": "La bóveda", "fuente": "en vivo", "filas": [
                    ["YouTube", "Leyendo ahora" if boveda.get("leyendo") else "En pausa"],
                    *([["Videos leídos hoy", str(boveda["leidos_hoy"])]] if boveda.get("leidos_hoy") is not None else []),
                    *([["Videos calificados", f"{boveda['calificados']:,}".replace(",", ".")]] if boveda.get("calificados") is not None else []),
                ]},
            ]
        if pid == "ingenieria":
            ag = boveda.get("agenda") or {}
            filas = [[n, f"{'Hoy' if (ag.get(k) or {}).get('hecho') == hoy.isoformat() else 'Última'} {_hora((ag.get(k) or {}).get('ultima'))}".strip()]
                     for k, n in (("noche", "La bóveda trabaja de noche"), ("diaria", "Newsletter de las 11:00"), ("salud", "Revisión de salud"), ("semanal", "Resumen del domingo")) if (ag.get(k) or {}).get("ultima")]
            entra.append({"titulo": "Horario automático", "fuente": "de la agenda", "filas": filas, "vacio": "La agenda no ha corrido todavía."})
        gente = [a for a in agentes.values() if a.get("piso") == pid]
        luz = any(a["estado"] == "trabajando" for a in gente) or (pid == "inteligencia" and bool(boveda.get("leyendo")))
        pisos.append({"id": pid, "nombre": nombre, "para": para, "color": color, "paso": paso, "luz": luz, "agentes": gente, "entra": entra})

    return {"fecha": hoy.isoformat(), "foco": foco, "norte": ficha.get("norte") or {},
            "remi": agentes.get("remi") or {}, "pisos": pisos}

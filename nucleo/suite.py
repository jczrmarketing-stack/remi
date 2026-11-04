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
    salida = {"leyendo": False, "calificados": None, "leidos_hoy": None, "agenda": {}, "enfriando_hasta": None}
    if raiz is None:
        return salida
    try:   # YouTube bloqueó la IP: la ingesta espera sola (youtube_catalogo.py, 1 h → 24 h)
        hasta = json.loads((raiz / "cache" / "youtube" / "enfriar.json").read_text(encoding="utf-8")).get("hasta")
        if hasta and hasta > datetime.now().timestamp():
            salida["enfriando_hasta"] = datetime.fromtimestamp(hasta).strftime("%-H:%M")
    except (OSError, ValueError, AttributeError):
        pass
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


def cobros_de_remi() -> list[list[str]]:
    """Las entregas y cobros que Remi lleva en remi.db (lo que le dices: «Alfonso pagó 2.000»).
    Vacío si todavía no hay ninguna: entonces manda lo escrito en la ficha."""
    try:
        import db
        import entregas
        conexion = db.conectar()
        try:
            filas = entregas.listar_entregas(conexion)
        finally:
            conexion.close()
    except Exception:  # noqa: BLE001
        return []
    nombre = {"camino": "En camino", "entregada": "Entregada, por cobrar", "pagada": "Pagada"}
    salida = []
    for e in sorted(filas, key=lambda e: (e.estado == "pagada", str(e.fecha)))[:6]:
        monto = f" · US${e.monto:,.0f}".replace(",", ".") if e.monto else ""
        salida.append([e.cliente, f"{nombre.get(e.estado, e.estado)}{monto}"])
    return salida


def _hora(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%-H:%M") if iso else ""
    except ValueError:
        return ""


def armar(foco_de_hoy: dict | None = None, hoy: date | None = None, ficha: dict | None = None,
          boveda: dict | None = None, temas: tuple[list[dict], str] | None = None, agentes: dict | None = None,
          cobros: list[list[str]] | None = None, pisos_publicados: dict | None = None,
          cajones: dict | None = None, norte: dict | None = None) -> dict:
    import suite_rutas  # aquí y no arriba: suite_rutas importa este módulo
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
                    ["YouTube", "Leyendo ahora" if boveda.get("leyendo") else (f"YouTube bloqueó; vuelve a las {boveda['enfriando_hasta']}" if boveda.get("enfriando_hasta") else "En pausa")],
                    *([["Videos leídos hoy", str(boveda["leidos_hoy"])]] if boveda.get("leidos_hoy") is not None else []),
                    *([["Videos calificados", f"{boveda['calificados']:,}".replace(",", ".")]] if boveda.get("calificados") is not None else []),
                ]},
            ]
        if pid == "ventas":
            vivos = cobros if cobros is not None else cobros_de_remi()
            if vivos:
                entra = [{"titulo": "Entregas y cobros", "fuente": "de Remi", "filas": vivos}] + [e for e in entra if e.get("titulo") != "Entregas y cobros"]
        ideas = suite_rutas.leer_cajon(pid) if cajones is None else (cajones.get(pid) or [])
        if ideas:  # lo que llegó desde otros pisos (POST /suite/guardar), las más nuevas primero
            previa = next((e for e in entra if e.get("titulo") == "Ideas guardadas"), None)
            nueva = {"titulo": "Ideas guardadas", "fuente": "desde otros pisos", "filas": ideas}
            entra = [nueva if e is previa else e for e in entra] if previa else entra + [nueva]
        if pid == "direccion":
            n = suite_rutas.leer_norte() if norte is None else norte
            tu_norte = suite_rutas.lista_tu_norte(n)
            if tu_norte:
                entra = [tu_norte] + [e for e in entra if e.get("titulo") != "Tu Norte"]
            if n.get("completo"):
                paso = {"titulo": "Tu Norte está escrito.", "contexto": "Revísalo con Remi y cambia lo que no suene a ti. Está en mente/negocio/norte.md.", "accion": "Revisar el Norte con Remi"}
            else:
                hechas = sum(1 for p in n.get("preguntas") or [] if p.get("respuesta"))
                if hechas:
                    paso = {**paso, "contexto": f"Vas en la pregunta {hechas + 1} de 6. Sigue donde quedaste.", "accion": "Seguir con el Norte"}
                paso["ruta"] = "/d/direccion/norte"
        if pid == "ingenieria":
            ag = boveda.get("agenda") or {}
            filas = [[n, f"{'Hoy' if (ag.get(k) or {}).get('hecho') == hoy.isoformat() else 'Última'} {_hora((ag.get(k) or {}).get('ultima'))}".strip()]
                     for k, n in (("noche", "La bóveda trabaja de noche"), ("diaria", "Newsletter de las 11:00"), ("salud", "Revisión de salud"), ("semanal", "Resumen del domingo")) if (ag.get(k) or {}).get("ultima")]
            entra.append({"titulo": "Horario automático", "fuente": "de la agenda", "filas": filas, "vacio": "La agenda no ha corrido todavía."})
        publicado = agentes_estado.leer_piso(pid) if pisos_publicados is None else (pisos_publicados.get(pid) or {})
        if publicado.get("paso"):
            paso = dict(publicado["paso"])
        for titulo, lista in (publicado.get("entra") or {}).items():
            entra = [e for e in entra if e.get("titulo") != titulo] + [lista]
        gente = [a for a in agentes.values() if a.get("piso") == pid]
        luz = any(a["estado"] == "trabajando" for a in gente) or (pid == "inteligencia" and bool(boveda.get("leyendo")))
        pisos.append({"id": pid, "nombre": nombre, "para": para, "color": color, "paso": paso, "luz": luz, "agentes": gente, "entra": entra})

    return {"fecha": hoy.isoformat(), "foco": foco, "norte": ficha.get("norte") or {},
            "remi": agentes.get("remi") or {}, "pisos": pisos}

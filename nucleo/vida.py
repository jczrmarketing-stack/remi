"""La mente de Juan Camilo como archivos: quién es, su negocio, supuestos, bandeja y búsqueda.

Solo stdlib, para que el hook de inicio de sesión arranque en milisegundos y
sin instalar nada. `remi_mcp.py` la expone como herramientas MCP.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(os.environ.get("REMI_RAIZ") or Path(__file__).resolve().parent.parent)
MENTE = Path(os.environ.get("REMI_MENTE") or Path.home() / "proyectos" / "mente")
# El orden es el del estado vivo: primero quién es, luego en qué anda.
ARCHIVOS_YO = ("perfil.md", "metas.md", "recursos.md", "restricciones.md", "valores-y-reglas.md")
FUERA_DE_BUSQUEDA = {".git", ".obsidian", "plantillas"}
PRESUPUESTO_CARACTERES = 5000  # ≈ 1.500 tokens en español
TIPOS = ("decision", "idea", "hecho", "supuesto", "pendiente")


def _boveda() -> Path | None:
    for candidato in (os.environ.get("REMI_BOVEDA"), "/Volumes/ORGANIC/boveda", str(RAIZ.parent / "boveda")):
        if candidato and Path(candidato).is_dir():
            return Path(candidato)
    return None


def _hoy() -> date:
    return date.fromisoformat(os.environ["REMI_HOY"]) if os.environ.get("REMI_HOY") else date.today()


def _frontmatter(texto: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\n(.*?)\n---\n?", texto, re.S)
    if not m:
        return {}, texto
    datos = {}
    for linea in m.group(1).splitlines():
        if ":" in linea:
            k, v = linea.split(":", 1)
            datos[k.strip()] = v.strip()
    return datos, texto[m.end():]


def _leer(relativa: str) -> str:
    ruta = MENTE / relativa
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


_SUPUESTO = re.compile(r"^- \[( |x|!)\] (.+?) · desde (\d{4}-\d{2}-\d{2}) · revisar (\d{4}-\d{2}-\d{2})\s*$")


def _supuestos_vencidos(hoy: date) -> list[str]:
    salida = []
    for linea in _leer("aprendido/supuestos.md").splitlines():
        m = _SUPUESTO.match(linea)
        if m and m.group(1) == " " and date.fromisoformat(m.group(4)) <= hoy:
            salida.append(f"- {m.group(2)} (desde {m.group(3)}) — ¿sigue siendo cierto?")
    return salida


def _bandeja_reciente(n: int = 5) -> list[str]:
    lineas = [l for l in _leer("bandeja/bandeja.md").splitlines() if l.startswith("- ")]
    return lineas[-n:]


def construir_estado(hoy: date | None = None) -> str:
    hoy = hoy or _hoy()
    datos, frentes = _frontmatter(_leer("negocio/frentes.md"))
    yo = [_frontmatter(_leer(f"yo/{nombre}"))[1].strip() for nombre in ARCHIVOS_YO]
    yo = [parte for parte in yo if parte]
    if not frentes.strip() and not yo:
        return f"Remi no tiene estado todavía: faltan {MENTE}/yo y {MENTE}/negocio/frentes.md."
    try:
        edad = (hoy - date.fromisoformat(datos.get("actualizado", ""))).days
    except ValueError:
        edad = -1
    aviso = f"Hoy es {hoy.isoformat()}. "
    if edad < 0:
        aviso += "No sé de cuándo es este estado: trátalo como posiblemente viejo."
    elif edad == 0:
        aviso += "Estado actualizado hoy."
    else:
        aviso += f"Este estado tiene {edad} día(s); lo marcado como visto puede haber cambiado."
    # Lo que nunca se recorta: quién es, supuestos vencidos y lo anotado hace poco.
    # Lo que cede espacio: frentes y, de último, el bloque del CRM.
    vencidos = _supuestos_vencidos(hoy)
    bloque_supuestos = "# Supuestos por revisar\n" + "\n".join(vencidos) if vencidos else ""
    bandeja = _bandeja_reciente()
    bloque_bandeja = "# Anotado hace poco\n" + "\n".join(bandeja) if bandeja else ""
    # Un servidor MCP abierto antes de la mudanza sigue escribiendo en las rutas viejas.
    restos = [d for d in ("vida", "experiencia") if (MENTE / d).exists()]
    aviso_restos = f"Ojo: hay notas en rutas viejas de la mente ({', '.join(restos)}/): falta pasarlas a su carpeta." if restos else ""
    crm_datos, crm_cuerpo = _frontmatter(_leer("negocio/crm.md"))
    bloque_crm = ""
    if crm_cuerpo.strip():
        try:
            crm_edad = (hoy - date.fromisoformat(crm_datos.get("actualizado", ""))).days
        except ValueError:
            crm_edad = -1
        nota = "" if 0 <= crm_edad <= 1 else f"\n(Ojo: este bloque se sacó de Notion hace {crm_edad} día(s)" + ("" if crm_edad >= 0 else ", fecha desconocida") + ".)"
        bloque_crm = crm_cuerpo.strip() + nota
    fijos = [p for p in (aviso, aviso_restos, *yo, bloque_supuestos, bloque_bandeja) if p]
    disponible = PRESUPUESTO_CARACTERES - sum(len(p) + 2 for p in fijos) - 4
    bloque_frentes = frentes.strip()
    if bloque_frentes and bloque_crm:
        cupo_frentes = max(0, int(disponible * 0.65))
    else:
        cupo_frentes = max(0, disponible)
    bloque_frentes = _recortar(bloque_frentes, cupo_frentes, "negocio/frentes.md")
    cupo_crm = max(0, disponible - len(bloque_frentes))
    bloque_crm = _recortar(bloque_crm, cupo_crm, "negocio/crm.md")
    partes = [p for p in (aviso, aviso_restos, *yo, bloque_frentes, bloque_supuestos, bloque_crm, bloque_bandeja) if p]
    texto = "\n\n".join(partes)
    if len(texto) > PRESUPUESTO_CARACTERES + 200:  # red de seguridad; no debería pasar
        texto = texto[:PRESUPUESTO_CARACTERES].rsplit("\n", 1)[0] + "\n[…recortado por presupuesto; usa `preguntar` para el resto]"
    return texto


def _recortar(bloque: str, cupo: int, archivo: str) -> str:
    """Corta un bloque por líneas enteras para que quepa en `cupo`, y dice dónde está el resto."""
    if not bloque or len(bloque) <= cupo:
        return bloque
    cola = f"\n[… sigue en {archivo}; pídelo con `preguntar`]"
    if cupo <= len(cola) + 40:
        return f"[{archivo}: no cupo en el presupuesto; pídelo con `preguntar`]"
    corte = bloque[: cupo - len(cola)].rsplit("\n", 1)[0]
    return corte + cola


def _archivos_de_busqueda() -> list[Path]:
    raices = [MENTE]
    b = _boveda()
    if b:
        raices += [b / d for d in ("03_oro", "02_procesado", "memoria/entradas")]
    archivos: list[Path] = []
    for raiz in raices:
        if raiz.is_dir():
            archivos += [p for p in raiz.rglob("*.md") if not FUERA_DE_BUSQUEDA.intersection(p.parts)]
    return archivos


_VACIAS = frozenset("el la los las un una unos unas de del al y o u en con por para que se su sus es son fue a lo le les mi tu me te como mas pero sin sobre entre cual cuales hay ya".split())


def _consulta_fts(q: str) -> str:
    terminos = [t for t in re.findall(r"\w{2,}", q.lower()) if t not in _VACIAS]
    return " OR ".join(f'"{t}"' for t in terminos[:12])


def buscar(q: str, n: int = 5) -> list[tuple[str, str]]:
    consulta = _consulta_fts(q)
    if not consulta:
        return []
    con = sqlite3.connect(":memory:")
    try:
        con.execute("create virtual table t using fts5(ruta unindexed, titulo, cuerpo, tokenize='unicode61 remove_diacritics 2')")
        for p in _archivos_de_busqueda():
            try:
                txt = p.read_text(encoding="utf-8")
            except OSError:
                continue
            datos, cuerpo = _frontmatter(txt)
            titulo = datos.get("titulo", "").strip('"') or p.stem
            con.execute("insert into t values (?,?,?)", (str(p), titulo, cuerpo))
        filas = con.execute(
            "select ruta, snippet(t, 2, '«', '»', ' … ', 24) from t where t match ? order by bm25(t, 0, 3, 1) limit ?",
            (consulta, n),
        ).fetchall()
    finally:
        con.close()
    return [(Path(r).name if not str(r).startswith(str(MENTE)) else str(Path(r).relative_to(MENTE)), s) for r, s in filas]


def agregar(texto: str, tipo: str, revisar_en_dias: int = 14) -> str:
    texto = " ".join(texto.split())
    if not texto:
        return "No anoté nada: el texto llegó vacío."
    if tipo not in TIPOS:
        return f"Tipo «{tipo}» no existe. Usa uno de: {', '.join(TIPOS)}."
    (MENTE / "bandeja").mkdir(parents=True, exist_ok=True)
    (MENTE / "aprendido").mkdir(parents=True, exist_ok=True)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M") if not os.environ.get("REMI_HOY") else f"{os.environ['REMI_HOY']} 00:00"
    with open(MENTE / "bandeja" / "bandeja.md", "a", encoding="utf-8") as f:
        f.write(f"- {ahora} [{tipo}] {texto}\n")
    if tipo == "supuesto":
        hoy = _hoy()
        revisar = date.fromordinal(hoy.toordinal() + max(1, revisar_en_dias))
        with open(MENTE / "aprendido" / "supuestos.md", "a", encoding="utf-8") as f:
            f.write(f"- [ ] {texto} · desde {hoy.isoformat()} · revisar {revisar.isoformat()}\n")
        return f"Anotado como supuesto; lo reviso el {revisar.isoformat()}."
    return "Anotado en la bandeja."



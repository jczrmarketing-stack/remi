"""El cerebro vivo de Remi, como servidor MCP global (stdio).

Cualquier sesión de Claude lo abre y sabe en qué está Juan Camilo sin que él
se lo cuente de nuevo. Cuatro herramientas, ninguna llama a un modelo de pago:

- estado_vivo  — su vida hoy en ≤ ~1.500 tokens, con la edad del dato.
- preguntar    — busca en conocimiento/ y en la bóveda (texto, sin tokens).
- anotar       — deja algo en la bandeja o abre un supuesto.
- supuestos    — lo que se dio por cierto y ya toca revisar.

Solo stdlib + mcp. Los archivos viven en conocimiento/vida/ (git, legibles
desde Obsidian). Nada sale del Mac.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from mcp.server.mcpserver import MCPServer

RAIZ = Path(os.environ.get("REMI_RAIZ") or Path(__file__).resolve().parent.parent)
VIDA = RAIZ / "conocimiento" / "vida"
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


def _leer(nombre: str) -> str:
    ruta = VIDA / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


_SUPUESTO = re.compile(r"^- \[( |x|!)\] (.+?) · desde (\d{4}-\d{2}-\d{2}) · revisar (\d{4}-\d{2}-\d{2})\s*$")


def _supuestos_vencidos(hoy: date) -> list[str]:
    salida = []
    for linea in _leer("supuestos.md").splitlines():
        m = _SUPUESTO.match(linea)
        if m and m.group(1) == " " and date.fromisoformat(m.group(4)) <= hoy:
            salida.append(f"- {m.group(2)} (desde {m.group(3)}) — ¿sigue siendo cierto?")
    return salida


def _bandeja_reciente(n: int = 5) -> list[str]:
    lineas = [l for l in _leer("bandeja.md").splitlines() if l.startswith("- ")]
    return lineas[-n:]


def construir_estado(hoy: date | None = None) -> str:
    hoy = hoy or _hoy()
    datos, cuerpo = _frontmatter(_leer("estado.md"))
    if not cuerpo.strip():
        return "Remi no tiene estado todavía: falta conocimiento/vida/estado.md."
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
    partes = [aviso, cuerpo.strip()]
    crm_datos, crm_cuerpo = _frontmatter(_leer("crm.md"))
    if crm_cuerpo.strip():
        try:
            crm_edad = (hoy - date.fromisoformat(crm_datos.get("actualizado", ""))).days
        except ValueError:
            crm_edad = -1
        nota = "" if 0 <= crm_edad <= 1 else f"\n(Ojo: este bloque se sacó de Notion hace {crm_edad} día(s)" + ("" if crm_edad >= 0 else ", fecha desconocida") + ".)"
        partes.append(crm_cuerpo.strip() + nota)
    vencidos = _supuestos_vencidos(hoy)
    if vencidos:
        partes.append("# Supuestos por revisar\n" + "\n".join(vencidos))
    bandeja = _bandeja_reciente()
    if bandeja:
        partes.append("# Anotado hace poco\n" + "\n".join(bandeja))
    texto = "\n\n".join(partes)
    if len(texto) > PRESUPUESTO_CARACTERES:
        recorte = texto[:PRESUPUESTO_CARACTERES].rsplit("\n", 1)[0]
        texto = recorte + "\n[…recortado por presupuesto; usa `preguntar` para el resto]"
    return texto


def _archivos_de_busqueda() -> list[Path]:
    raices = [RAIZ / "conocimiento"]
    b = _boveda()
    if b:
        raices += [b / d for d in ("03_oro", "02_procesado", "memoria/entradas")]
    archivos: list[Path] = []
    for raiz in raices:
        if raiz.is_dir():
            archivos += [p for p in raiz.rglob("*.md") if ".git" not in p.parts]
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
    return [(Path(r).name if not str(r).startswith(str(RAIZ)) else str(Path(r).relative_to(RAIZ)), s) for r, s in filas]


def agregar(texto: str, tipo: str, revisar_en_dias: int = 14) -> str:
    texto = " ".join(texto.split())
    if not texto:
        return "No anoté nada: el texto llegó vacío."
    if tipo not in TIPOS:
        return f"Tipo «{tipo}» no existe. Usa uno de: {', '.join(TIPOS)}."
    VIDA.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M") if not os.environ.get("REMI_HOY") else f"{os.environ['REMI_HOY']} 00:00"
    with open(VIDA / "bandeja.md", "a", encoding="utf-8") as f:
        f.write(f"- {ahora} [{tipo}] {texto}\n")
    if tipo == "supuesto":
        hoy = _hoy()
        revisar = date.fromordinal(hoy.toordinal() + max(1, revisar_en_dias))
        with open(VIDA / "supuestos.md", "a", encoding="utf-8") as f:
            f.write(f"- [ ] {texto} · desde {hoy.isoformat()} · revisar {revisar.isoformat()}\n")
        return f"Anotado como supuesto; lo reviso el {revisar.isoformat()}."
    return "Anotado en la bandeja."


servidor = MCPServer(
    "remi",
    instructions=(
        "Remi es el contexto vivo de Juan Camilo (negocio y vida). Al empezar una sesión que dependa de "
        "su situación, llama `estado_vivo` una vez. Antes de preguntarle algo que ya debería saberse, usa "
        "`preguntar`. Cuando él decida algo, o aparezca un dato que cambie su situación, usa `anotar`. "
        "Si `estado_vivo` trae supuestos por revisar, confírmalos con él en una sola pregunta corta."
    ),
)


@servidor.tool(description="La vida y el negocio de Juan Camilo hoy, en pocas líneas, con la edad del dato. Llámala al empezar.")
def estado_vivo() -> str:
    return construir_estado()


@servidor.tool(description="Busca en el conocimiento de Remi y en la bóveda (sin gastar modelo). Úsala antes de preguntarle algo a Juan Camilo.")
def preguntar(q: str) -> str:
    hallazgos = buscar(q)
    if not hallazgos:
        return f"No hay nada sobre «{q}» en el conocimiento ni en la bóveda."
    return "\n".join(f"{ruta}: {frag}" for ruta, frag in hallazgos)


@servidor.tool(description="Deja algo anotado. tipo: decision | idea | hecho | supuesto | pendiente. Un supuesto se vuelve a revisar solo.")
def anotar(texto: str, tipo: str = "hecho", revisar_en_dias: int = 14) -> str:
    return agregar(texto, tipo, revisar_en_dias)


@servidor.tool(description="Supuestos abiertos que ya toca confirmar o dar por rotos.")
def supuestos() -> str:
    v = _supuestos_vencidos(_hoy())
    return "\n".join(v) if v else "No hay supuestos por revisar hoy."


if __name__ == "__main__":
    servidor.run()

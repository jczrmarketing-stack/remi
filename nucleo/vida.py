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
FUERA_DE_BUSQUEDA = {".git", ".obsidian", "plantillas", "dashboards"}
PRESUPUESTO_CARACTERES = 5000  # ≈ 1.500 tokens en español
TIPOS = ("decision", "idea", "hecho", "supuesto", "pendiente")
# Tipos con destino propio en la mente (F1.3). Los de TIPOS siguen cayendo en la bandeja.
TIPOS_CON_DESTINO = {
    "decision": "aprendido/decisiones",
    "investigacion": "mundo/investigaciones",
    "leccion": "aprendido/lecciones",
    "resultado": "aprendido/diario",
    "hipotesis": None,          # bandeja, marcada
    "hecho_sobre_mi": None,     # bandeja/por-confirmar.md + aviso
}
UMBRAL_COBERTURA = 0.5  # fracción de términos de la consulta que una ficha debe contener para entrar
PRESUPUESTO_HOOK = 2400  # ≈ 600 tokens


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


DIAS_DECISION_VIGENTE = 90


def _decisiones_vigentes(hoy: date | None = None, n: int = 8) -> list[str]:
    """Las últimas decisiones anotadas (aprendido/decisiones/AAAA-MM-DD-*.md), más
    recientes primero. Una decisión vieja no desaparece: deja de mostrarse a los 90
    días, pero sigue en la mente para `preguntar`."""
    hoy = hoy or _hoy()
    carpeta = MENTE / "aprendido" / "decisiones"
    if not carpeta.is_dir():
        return []
    salida = []
    for ruta in sorted(carpeta.glob("*.md"), reverse=True):
        try:
            fecha = date.fromisoformat(ruta.name[:10])
        except ValueError:
            continue
        if (hoy - fecha).days > DIAS_DECISION_VIGENTE:
            continue
        datos, _cuerpo = _frontmatter(ruta.read_text(encoding="utf-8", errors="replace"))
        titulo = str(datos.get("titulo") or ruta.stem[11:].replace("-", " ")).strip().strip('"')
        if titulo:
            salida.append(f"- {fecha.isoformat()}: {titulo}")
        if len(salida) == n:
            break
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
    decisiones = _decisiones_vigentes(hoy)
    bloque_decisiones = "# Decisiones vigentes (no las vuelvas a abrir sin motivo nuevo)\n" + "\n".join(decisiones) if decisiones else ""
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
    fijos = [p for p in (aviso, aviso_restos, *yo, bloque_decisiones, bloque_supuestos, bloque_bandeja) if p]
    disponible = PRESUPUESTO_CARACTERES - sum(len(p) + 2 for p in fijos) - 4
    bloque_frentes = frentes.strip()
    if bloque_frentes and bloque_crm:
        cupo_frentes = max(0, int(disponible * 0.65))
    else:
        cupo_frentes = max(0, disponible)
    bloque_frentes = _recortar(bloque_frentes, cupo_frentes, "negocio/frentes.md")
    cupo_crm = max(0, disponible - len(bloque_frentes))
    bloque_crm = _recortar(bloque_crm, cupo_crm, "negocio/crm.md")
    partes = [p for p in (aviso, aviso_restos, *yo, bloque_decisiones, bloque_frentes, bloque_supuestos, bloque_crm, bloque_bandeja) if p]
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
    if not MENTE.is_dir():
        return []
    return [p for p in MENTE.rglob("*.md") if not FUERA_DE_BUSQUEDA.intersection(p.parts)]


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


_URL = re.compile(r"https?://\S+")


def _slug(texto: str, n: int = 60) -> str:
    import unicodedata
    plano = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    plano = re.sub(r"[^a-z0-9]+", "-", plano).strip("-")
    return plano[:n].rstrip("-") or "nota"


def _terminos(q: str) -> list[str]:
    import unicodedata
    plano = "".join(c for c in unicodedata.normalize("NFKD", q.lower()) if not unicodedata.combining(c))
    vistos: dict[str, None] = {}
    for t in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", plano):
        if t not in _VACIAS and t not in _VACIAS_HOOK:
            vistos.setdefault(t, None)
    return list(vistos)[:10]


_VACIAS_HOOK = frozenset(
    "para como esta este estos estas pero donde cuando sobre entre hasta desde porque"
    " that this with from what which would could should there their about into then than"
    " puedo quiero hazme dame dime mira revisa crea haz pues entonces tambien ahora algo"
    " sirve sirven mejor cual cuales tengo tiene tienen vamos hacer hace quiero necesito".split()
)


def buscar_indice(q: str, n: int = 4, ruta_db: Path | None = None) -> list[dict]:
    """Fichas del índice (`indice.db`) solo con FTS y stdlib: el hook corre con el
    python del sistema, sin sqlite-vec. Umbral: la ficha debe cubrir al menos la
    mitad de los términos de la consulta y estar a menos de la mitad del mejor
    puntaje bm25. Nunca devuelve el cuerpo."""
    ruta_db = ruta_db or (MENTE / "indice.db")
    terminos = _terminos(q)
    if len(terminos) < 2 or not ruta_db.exists():
        return []
    consulta = " OR ".join(f'"{t}"' for t in terminos)
    try:
        con = sqlite3.connect(f"file:{ruta_db}?mode=ro", uri=True, timeout=1)
    except sqlite3.Error:
        return []
    try:
        con.row_factory = sqlite3.Row
        filas = con.execute(
            "SELECT n.id, n.tipo, n.titulo, n.resumen, n.fecha, n.estatus, n.confianza, "
            "bm25(notas_fts, 3, 2, 1) AS puntaje, snippet(notas_fts, 2, '', '', ' ', 24) AS trozo "
            "FROM notas_fts JOIN notas n ON n.rowid = notas_fts.rowid "
            "WHERE notas_fts MATCH ? ORDER BY puntaje LIMIT ?",
            (consulta, n * 4),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    if not filas:
        return []
    mejor = filas[0]["puntaje"]
    minimo = max(1, int(len(terminos) * UMBRAL_COBERTURA + 0.999))
    salida: list[dict] = []
    for f in filas:
        import unicodedata
        texto = "".join(c for c in unicodedata.normalize("NFKD", f"{f['titulo']} {f['resumen']} {f['trozo']}".lower()) if not unicodedata.combining(c))
        cobertura = sum(1 for t in terminos if t in texto)
        if cobertura < minimo or f["puntaje"] > mejor * 0.5:
            continue
        salida.append({k: f[k] for k in ("id", "tipo", "titulo", "resumen", "fecha", "estatus", "confianza")})
        if len(salida) == n:
            break
    return salida


def fichas_para_contexto(fichas: list[dict], presupuesto: int = PRESUPUESTO_HOOK) -> str:
    lineas = ["LA MENTE YA TIENE ALGO SOBRE ESTO (Remi). Úsalo antes de buscar en la web o de preguntarle a Juan Camilo; para el cuerpo, `leer(id)` del MCP remi; si lo usas, di de qué nota salió."]
    for f in fichas:
        resumen = " ".join(str(f["resumen"]).split())[:180]
        lineas.append(f"- [{f['id']}] {f['tipo']} · {f['fecha']} · {f['estatus']}/{f['confianza']} · {f['titulo']}: {resumen}")
    texto = "\n".join(lineas)
    return texto[:presupuesto]


def _avisar_telegram(texto: str) -> bool:
    """POST al núcleo para que lo mande por Telegram. Sin red o sin núcleo: False y nada se rompe."""
    import json
    import urllib.request
    try:
        cfg = json.loads((RAIZ / "config" / "nucleo.json").read_text(encoding="utf-8"))
        pedido = urllib.request.Request(
            f"http://{cfg['host']}:{cfg['puerto']}/telegram/avisar",
            data=json.dumps({"texto": texto}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(pedido, timeout=3):
            return True
    except Exception:  # noqa: BLE001 — un aviso que falla no tumba un anotar
        return False


def anotar(texto: str, tipo: str = "hecho", revisar_en_dias: int = 14, fuentes: str = "") -> str:
    """Salida con compuerta. Lo que toca `yo/` queda por confirmar; una
    investigación exige URL; lo aprendido se escribe directo con fecha."""
    texto = " ".join(texto.split())
    if not texto:
        return "No anoté nada: el texto llegó vacío."
    if tipo in TIPOS and tipo != "decision":
        return agregar(texto, tipo, revisar_en_dias)
    if tipo not in TIPOS_CON_DESTINO:
        return f"Tipo «{tipo}» no existe. Usa uno de: {', '.join(list(TIPOS_CON_DESTINO) + list(TIPOS))}."
    hoy = _hoy().isoformat()
    (MENTE / "bandeja").mkdir(parents=True, exist_ok=True)
    urls = _URL.findall(texto) + _URL.findall(fuentes or "")
    if tipo == "investigacion" and not urls:
        return "No anoté la investigación: necesita al menos una URL en el texto o en `fuentes`. Sin fuente va como hipótesis (tipo='hipotesis')."
    if tipo == "hipotesis":
        (MENTE / "bandeja").mkdir(parents=True, exist_ok=True)
        with open(MENTE / "bandeja" / "bandeja.md", "a", encoding="utf-8") as f:
            f.write(f"- {hoy} [hipotesis] {texto}\n")
        return "Anotado como hipótesis en la bandeja (sin fuente, no es hecho)."
    if tipo == "hecho_sobre_mi":
        (MENTE / "bandeja").mkdir(parents=True, exist_ok=True)
        with open(MENTE / "bandeja" / "por-confirmar.md", "a", encoding="utf-8") as f:
            f.write(f"- [ ] {texto} · dicho por Claude el {hoy}\n")
        avisado = _avisar_telegram(f"¿Guardo esto en tu perfil? «{texto}». Márcalo en bandeja/por-confirmar.md (Obsidian) o dime sí/no.")
        return "Queda por confirmar en bandeja/por-confirmar.md" + (" y te lo pregunté por Telegram." if avisado else ". No pude avisar por Telegram: confírmalo en Obsidian.")
    carpeta = MENTE / TIPOS_CON_DESTINO[tipo]
    carpeta.mkdir(parents=True, exist_ok=True)
    if tipo == "resultado":
        ruta = carpeta / f"{hoy}.md"
        nuevo = not ruta.exists()
        with open(ruta, "a", encoding="utf-8") as f:
            if nuevo:
                f.write(f"---\ntipo: diario\nfecha: {hoy}\n---\n\n# {hoy}\n\n")
            f.write(f"- [resultado] {texto}\n")
        return f"Anotado en el diario de {hoy}."
    titulo = texto.split(". ")[0][:90].rstrip(".")
    ruta = carpeta / f"{hoy}-{_slug(titulo)}.md"
    if ruta.exists():
        ruta = carpeta / f"{hoy}-{_slug(titulo)}-{datetime.now().strftime('%H%M%S')}.md"
    estatus = {"decision": "decidido", "investigacion": "hipotesis", "leccion": "leccion"}[tipo]
    frontmatter = [
        "---", f'titulo: "{titulo}"', f"tipo: {tipo}", f"fecha: {hoy}", f"estatus: {estatus}",
        "confianza: media", "fuente: claude",
    ]
    if urls:
        frontmatter.append("fuentes: [" + ", ".join(f'"{u}"' for u in dict.fromkeys(urls)) + "]")
    frontmatter.append("---")
    ruta.write_text("\n".join(frontmatter) + f"\n\n# {titulo}\n\n{texto}\n", encoding="utf-8")
    with open(MENTE / "bandeja" / "bandeja.md", "a", encoding="utf-8") as f:
        f.write(f"- {hoy} [{tipo}] {titulo} → {ruta.relative_to(MENTE).as_posix()}\n")
    return f"Anotado: {ruta.relative_to(MENTE).as_posix()}."


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



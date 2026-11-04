"""El Clasificador de INV3RZA: el productor ejecutivo del piso Inteligencia (4-nov).

Cada noche ordena lo que entró a la bóveda el último día (noticias de la newsletter y videos ingeridos):
a cada pieza le pone una ficha (nivel 1–3, para qué le sirve a JC, a qué frente toca) con la suscripción de
Claude (`claude -p`, nunca API pagada) y la conecta con hasta 3 piezas parecidas que la bóveda ya tenía
(embeddings locales de Ollama). Si Claude no puede, ficha una versión local sin LLM (frente por palabras
clave, nivel por la relevancia que ya puso la bóveda o su clasificador local) y el bot de alertas lo cuenta
una sola vez. Las fichas viven en su propia base (cache/clasificador-agente.db): no toca tablas ajenas.
El domingo escribe un memo corto con lo que cambió y si conviene ajustar algo, y deja una línea para la
newsletter (`linea_para_newsletter`).

    python3 clasificador.py --diario            # fichar lo del último día y publicarlo en la Suite
    python3 clasificador.py --semanal           # fichar lo pendiente + memo de la semana (domingo)
    python3 clasificador.py --probar            # el diario sin escribir nada: imprime las fichas
    python3 clasificador.py --semanal --probar  # el memo sin escribir nada: lo imprime
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BOVEDA = Path(os.environ.get("BOVEDA_RAIZ") or Path.home() / "proyectos" / "boveda")
MENTE = Path(os.environ.get("REMI_MENTE") or Path.home() / "proyectos" / "mente")
sys.path.insert(0, str(BOVEDA))
NUCLEO = Path(__file__).resolve().parents[2] / "nucleo"
BD = Path(os.environ.get("CLASIFICADOR_BD") or BOVEDA / "cache" / "clasificador-agente.db")

MODELO = os.environ.get("CLASIFICADOR_MODELO", "haiku")          # fichas: tarea corta y repetitiva
MODELO_MEMO = os.environ.get("CLASIFICADOR_MODELO_MEMO", "sonnet")
TOPE_SEG = 900
LOTE = 40
UMBRAL = float(os.environ.get("CLASIFICADOR_UMBRAL") or 0.72)   # coseno mínimo para llamar «parecida» a otra pieza
MISMA = 0.95                                                     # de aquí para arriba es la misma pieza, no una conexión
MAX_CONEXIONES = 3
VENTANA_H = 26                                                   # «el último día», con margen por si la agenda se corre
VENTANA_NOTICIAS_H = 72                                          # la bóveda califica algunas noticias tarde: se miran 3 días
HORA_DIARIO = "21:30"
FRENTES = ("upvisuals", "fiverr", "llc", "remi", "inverza", "organic-cash", "malik", "general")
NOMBRE_FRENTE = {"upvisuals": "UpVisuals", "fiverr": "Fiverr", "llc": "Omniway LLC", "remi": "Remi", "inverza": "INVERZA",
                 "organic-cash": "Organic Cash", "malik": "Malik", "general": "General"}
USOS = ("decidir", "vender", "construir", "aprender", "vigilar")
TIPOS_MEMO = ("seguir", "ajustar", "empezar", "pivotar")
_RUTAS_CLAUDE = ("~/.local/bin/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude", "~/.claude/local/claude", "~/.npm-global/bin/claude")

# Versión local (sin LLM): la primera regla que encaja gana. Específicos primero; remi es amplio.
PALABRAS_FRENTE = [
    ("upvisuals", ("upvisuals", "alfonso", "generador de imágenes", "generación de imágenes", "image generat", "image model",
                   "text-to-image", "stable diffusion", "midjourney", "flux", "imagen con ia", "ai image")),
    ("fiverr", ("fiverr", "upwork", "gig ", "gigs", "marketplace de freelance")),
    ("llc", ("llc", "wyoming", "irs", "ein ", "form 5472", "registered agent", "impuesto", "taxes", " tax ")),
    ("malik", ("malik", "facturación", "factura", "invoice")),
    ("organic-cash", ("organic cash", "ingreso pasivo", "passive income")),
    ("inverza", ("inverza", "inv3rza", "agencia", "agency", "seguros", "insurance", "hispan", "cold email", "outreach",
                 "conseguir clientes", "get clients", "lead gen", "oferta", "offer")),
    ("remi", ("claude code", "mcp", "agente", "agent", "obsidian", "notion", "asistente", "tdah", "adhd", "ollama",
              "embedding", " rag", "automatiza", "automation", "segundo cerebro", "second brain")),
]
PALABRAS_USO = [
    ("vender", ("cliente", "client", "ventas", "sales", "vender", "sell", "pricing", "precios", "marketing", "oferta", "offer",
                "lead", "freelanc", "agencia", "agency", "outreach", "revenue", "facturar", "mrr", "arr", "ingresos")),
    ("construir", ("código", "codigo", "code", "mcp", "agente", "agent", "api", "framework", "open source", "github", "sdk",
                   "tutorial", "workflow", "automatiza", "automation", "prompt", "build")),
    ("decidir", ("regulación", "regulation", "ley ", "law", "cuota", "plan ", "precio de", "price", "adquiere", "acquir",
                 "cierra", "shuts down", "impuesto", "tax", "prohíbe", "ban")),
    ("vigilar", ("rumor", "filtra", "leak", "benchmark", "lanza", "launch", "anuncia", "announc")),
]


# ---------- piezas de la Suite y de la bóveda (nunca rompen la corrida) ----------

def _reportar(estado: str, ahora: str = "", ultimo: str | None = None) -> None:
    """Le cuenta a la Suite qué hace el Clasificador (estado/agentes/clasificador.json)."""
    try:
        if str(NUCLEO) not in sys.path:
            sys.path.append(str(NUCLEO))
        import agentes_estado
        agentes_estado.avisar("clasificador", estado, ahora, ultimo)
    except Exception:  # noqa: BLE001
        pass


def _publicar_piso(filas: list[list[str]]) -> None:
    if str(NUCLEO) not in sys.path:
        sys.path.append(str(NUCLEO))
    import agentes_estado
    agentes_estado.publicar_piso("inteligencia", "clasificador",
                                 entra=[{"titulo": "La bóveda ordenada", "fuente": "del Clasificador", "filas": filas}])


def _modulo_boveda(nombre: str):
    """Un módulo de la bóveda por su archivo. El clasificador local se llama igual que este agente:
    importarlo por nombre traería este mismo archivo."""
    clave = f"boveda_{nombre}"
    if clave in sys.modules:
        return sys.modules[clave]
    spec = importlib.util.spec_from_file_location(clave, BOVEDA / f"{nombre}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[clave] = mod
    spec.loader.exec_module(mod)
    return mod


def _solo_lectura(ruta: Path) -> sqlite3.Connection | None:
    if not ruta.exists():
        return None
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


# ---------- la base propia ----------

ESQUEMA = """
CREATE TABLE IF NOT EXISTS fichas (clave TEXT PRIMARY KEY, tipo TEXT, origen_id TEXT, titulo TEXT, fuente TEXT, enlace TEXT,
    nivel INTEGER, uso TEXT, frente TEXT, por_que TEXT, por TEXT, conexiones TEXT, creada_en TEXT);
CREATE TABLE IF NOT EXISTS vectores (clave TEXT NOT NULL, modelo TEXT NOT NULL, vec TEXT NOT NULL, PRIMARY KEY (clave, modelo));
CREATE TABLE IF NOT EXISTS memos (semana TEXT PRIMARY KEY, ruta TEXT, linea TEXT, notion_url TEXT, por TEXT, en TEXT);
CREATE TABLE IF NOT EXISTS avisos (dia TEXT NOT NULL, motivo TEXT NOT NULL, PRIMARY KEY (dia, motivo));
"""


def abrir(ruta: Path | None = None, probar: bool = False) -> sqlite3.Connection:
    """La base del Clasificador. En prueba: una copia en memoria de lo que haya (nunca escribe el archivo)."""
    ruta = ruta or BD
    if probar:
        con = sqlite3.connect(":memory:")
        if ruta.exists():
            sqlite3.connect(f"file:{ruta}?mode=ro", uri=True).backup(con)
    else:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(ruta), timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def _avisar_una_vez(con: sqlite3.Connection, motivo: str, texto: str, avisar=None, hoy: date | None = None) -> bool:
    """Un aviso por motivo y por día: si la noche falla dos veces, JC se entera una."""
    dia = (hoy or date.today()).isoformat()
    if con.execute("SELECT 1 FROM avisos WHERE dia = ? AND motivo = ?", (dia, motivo)).fetchone():
        return False
    try:
        if avisar is None:
            import alertas
            avisar = alertas.enviar
        avisar(texto)
    except Exception:  # noqa: BLE001 — sin bot no se cae la corrida
        pass
    con.execute("INSERT OR IGNORE INTO avisos (dia, motivo) VALUES (?, ?)", (dia, motivo))
    con.commit()
    return True


# ---------- lo que entró ----------

def _resumen_video(nota: str, mente: Path) -> str:
    """El resumen que la bóveda ya escribió del video (mente/mundo/fuentes/youtube/<x>.md)."""
    m = re.search(r"mundo/\S+\.md", nota or "")
    if not m:
        return ""
    try:
        texto = (mente / m.group(0)).read_text(encoding="utf-8")
    except OSError:
        return ""
    s = re.search(r"^## Resumen\s*$(.*?)(?=^## |\Z)", texto, re.M | re.S)
    lineas = [l[2:].strip() for l in (s.group(1).splitlines() if s else []) if l.startswith("- ")]
    return " ".join(lineas[:3])[:500]


def piezas_nuevas(ahora: datetime | None = None, horas: int = VENTANA_H, boveda: Path | None = None, mente: Path | None = None) -> list[dict]:
    """Noticias útiles (relevancia ≥ 2 que puso la bóveda; solo la representante de cada historia) y videos
    ingeridos en la ventana. El ruido sin calificar (ofertas de empleo, Product Hunt) no gasta suscripción."""
    boveda, mente = boveda or BOVEDA, mente or MENTE
    ahora = ahora or datetime.now()
    desde_local = (ahora - timedelta(hours=horas)).isoformat(timespec="seconds")
    desde_utc = (ahora.astimezone(timezone.utc) - timedelta(hours=max(horas, VENTANA_NOTICIAS_H))).isoformat(timespec="seconds")
    piezas: list[dict] = []
    con = _solo_lectura(boveda / "cache" / "newsletter.db")
    if con:
        try:
            for f in con.execute("SELECT id, fuente, nombre, titulo, link, extracto, resumen_es, relevancia FROM items "
                                 "WHERE visto_en >= ? AND descartado_por IS NULL AND relevancia >= 2 "
                                 "AND (grupo IS NULL OR grupo = id) ORDER BY visto_en", (desde_utc,)):
                piezas.append({"clave": f"n:{f['id']}", "tipo": "noticia", "origen_id": f["id"], "titulo": f["titulo"] or "",
                               "resumen": (f["resumen_es"] or f["extracto"] or "")[:500], "fuente": f["nombre"] or f["fuente"] or "",
                               "enlace": f["link"] or "", "relevancia": f["relevancia"],
                               "texto_emb": f"{f['titulo'] or ''} — {(f['extracto'] or '')[:200]}".strip(" —")})
        finally:
            con.close()
    con = _solo_lectura(boveda / "cache" / "youtube" / "catalogo.db")
    if con:
        try:
            for f in con.execute("SELECT id, canal, titulo, relevancia, nota FROM videos WHERE estado = 'ingerido' AND ingerido_en >= ? "
                                 "ORDER BY ingerido_en", (desde_local,)):
                piezas.append({"clave": f"v:{f['id']}", "tipo": "video", "origen_id": f["id"], "titulo": f["titulo"] or "",
                               "resumen": _resumen_video(f["nota"], mente), "fuente": f["canal"] or "",
                               "enlace": f"https://www.youtube.com/watch?v={f['id']}", "relevancia": f["relevancia"],
                               "texto_emb": f"{f['titulo']} ({f['canal']})"})   # igual que compuerta.vectores_catalogo
        finally:
            con.close()
    return piezas


def sin_fichar(con: sqlite3.Connection, piezas: list[dict]) -> list[dict]:
    hechas = {r[0] for r in con.execute("SELECT clave FROM fichas")}
    return [p for p in piezas if p["clave"] not in hechas]


# ---------- la ficha ----------

def _primera(reglas, texto: str, defecto: str) -> str:
    t = f" {texto.lower()} "
    for valor, palabras in reglas:
        if any(p in t for p in palabras):
            return valor
    return defecto


def frente_por_palabras(texto: str) -> str:
    return _primera(PALABRAS_FRENTE, texto, "general")


def uso_por_palabras(texto: str) -> str:
    return _primera(PALABRAS_USO, texto, "aprender")


def relevancia_local(pieza: dict, vec: list[float] | None) -> int | None:
    """La relevancia que ya puso la bóveda; si no hay, la del clasificador local (si está entrenado y activo)."""
    if pieza.get("relevancia") is not None:
        return int(pieza["relevancia"])
    if not vec:
        return None
    try:
        cl = _modulo_boveda("clasificador")
        modelo = cl.cargar(cl.MODELO_NOTICIAS) if pieza["tipo"] == "noticia" else cl.cargar(cl.MODELO)
        if pieza["tipo"] == "noticia" and not cl.activo(modelo):
            return None
        return cl.relevancia(cl.probabilidad(modelo, vec)) if modelo else None
    except Exception:  # noqa: BLE001
        return None


def ficha_local(pieza: dict, vec: list[float] | None = None) -> dict:
    texto = f"{pieza['titulo']} {pieza.get('resumen', '')}"
    rel = relevancia_local(pieza, vec)
    return {"nivel": max(1, min(3, rel if rel is not None else 1)), "uso": uso_por_palabras(texto),
            "frente": frente_por_palabras(texto), "por_que": "", "por": "local"}


def _parsear_json(texto: str) -> dict:
    t = (texto or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    if not t.startswith("{"):
        a, b = t.find("{"), t.rfind("}")
        t = t[a:b + 1] if a >= 0 and b > a else "{}"
    datos = json.loads(t)
    return datos if isinstance(datos, dict) else {}


def leer_respuesta(texto: str, piezas: list[dict]) -> dict[str, dict]:
    """Las fichas de Claude, validadas: solo ids reales; nivel 1–3; uso y frente de la lista o el neutro."""
    datos = _parsear_json(texto)
    validas = {p["clave"] for p in piezas}
    salida: dict[str, dict] = {}
    for f in datos.get("fichas") or []:
        if not isinstance(f, dict) or f.get("id") not in validas:
            continue
        try:
            nivel = max(1, min(3, int(f.get("nivel") or 1)))
        except (TypeError, ValueError):
            nivel = 1
        uso = str(f.get("uso") or "").strip().lower()
        frente = str(f.get("frente") or "").strip().lower()
        salida[f["id"]] = {"nivel": nivel, "uso": uso if uso in USOS else "aprender",
                           "frente": frente if frente in FRENTES else "general",
                           "por_que": str(f.get("por_que") or "").strip()[:200], "por": "claude"}
    return salida


def binario_claude() -> str | None:
    """launchd corre con un PATH mínimo: se busca la CLI donde suele estar."""
    hallado = shutil.which("claude")
    if hallado:
        return hallado
    for ruta in _RUTAS_CLAUDE:
        p = Path(ruta).expanduser()
        if p.exists():
            return str(p)
    return None


def _registrar_consumo(correr, modelo: str, segundos: float, salida=None, returncode: int = 0, error: str | None = None) -> None:
    """Anota la llamada en `consumo_claude` (nucleo/consumo.py). Solo con la CLI real: las pruebas inyectan `correr` y no escriben en la base. Nunca rompe al agente."""
    if correr is not None:
        return
    try:
        if str(NUCLEO) not in sys.path:
            sys.path.append(str(NUCLEO))
        import consumo
        consumo.registrar("clasificador", modelo, segundos, salida, returncode, error)
    except Exception:  # noqa: BLE001
        pass


def llamar_claude(sistema: str, mensaje: str, modelo: str = MODELO, correr=None, binario: str | None = None) -> str | None:
    """`claude -p` con la suscripción Max: sin variables ANTHROPIC_* (nunca la API pagada) y sin herramientas."""
    binario = binario or binario_claude()
    if not binario:
        raise RuntimeError("no encuentro la CLI de Claude (claude)")
    entorno = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")}
    comando = [binario, "-p", "--model", modelo, "--output-format", "json", "--system-prompt", sistema, "--tools", "",
               "--setting-sources", "", "--no-session-persistence", "--strict-mcp-config", "--max-turns", "3"]
    inicio = time.perf_counter()
    try:
        r = (correr or subprocess.run)(comando, input=mensaje, capture_output=True, text=True, timeout=TOPE_SEG, env=entorno, cwd=str(AQUI))
    except subprocess.TimeoutExpired:
        _registrar_consumo(correr, modelo, time.perf_counter() - inicio, error="timeout")
        raise
    except OSError as exc:
        _registrar_consumo(correr, modelo, 0, error=f"{type(exc).__name__}: {exc}")
        raise
    _registrar_consumo(correr, modelo, time.perf_counter() - inicio, getattr(r, "stdout", None), getattr(r, "returncode", 0))
    datos = json.loads(r.stdout or "{}")
    if datos.get("is_error"):
        raise RuntimeError(f"la CLI avisó un error: {str(datos.get('result'))[:200]}")
    return datos.get("result")


def _instrucciones() -> str:
    return (AQUI / "instrucciones.md").read_text(encoding="utf-8")


def _sin_frontmatter(texto: str) -> str:
    return texto.split("---", 2)[2].strip() if texto.startswith("---") and texto.count("---") >= 2 else texto.strip()


def ficha_de_jc(mente: Path | None = None) -> str:
    mente = mente or MENTE
    partes = []
    for rel in ("yo/metas.md", "negocio/frentes.md"):
        try:
            partes.append(_sin_frontmatter((mente / rel).read_text(encoding="utf-8"))[:2500])
        except OSError:
            pass
    return "\n\n".join(partes)


def fichar_con_claude(piezas: list[dict], claude=None, mente: Path | None = None) -> dict[str, dict]:
    """Fichas en lotes. Un lote roto levanta la excepción: el que llama decide la versión local."""
    sistema = _instrucciones()
    salida: dict[str, dict] = {}
    for i in range(0, len(piezas), LOTE):
        grupo = piezas[i:i + LOTE]
        entrada = [{"id": p["clave"], "tipo": p["tipo"], "titulo": p["titulo"], "resumen": p["resumen"][:400], "fuente": p["fuente"]} for p in grupo]
        mensaje = ("Tarea: fichas.\n\nPiezas (JSON):\n" + json.dumps(entrada, ensure_ascii=False) + "\n\nFicha de JC:\n" + ficha_de_jc(mente))
        respuesta = (claude or (lambda s, m: llamar_claude(s, m, MODELO)))(sistema, mensaje)
        leidas = leer_respuesta(respuesta, grupo)
        if not leidas:
            raise RuntimeError("Claude no devolvió ninguna ficha válida")
        salida.update(leidas)
    return salida


# ---------- vectores y conexiones ----------

def _modelo_emb() -> str:
    try:
        return _modulo_boveda("compuerta").modelo_embeddings()
    except Exception:  # noqa: BLE001
        return "qwen3-embedding:0.6b"


def embed_ollama(textos: list[str]) -> list[list[float]] | None:
    """Por defecto: Ollama local (qwen3-embedding:0.6b en 127.0.0.1:11434), lo mismo que usa la compuerta."""
    return _modulo_boveda("compuerta").embed(textos)


def _vectores_boveda(boveda: Path, modelo: str) -> dict[str, list[float]]:
    """Los vectores que la bóveda ya calculó, por clave del Clasificador (n:<id>, v:<id>)."""
    salida: dict[str, list[float]] = {}
    for prefijo, rel in (("n", ("cache", "newsletter.db")), ("v", ("cache", "youtube", "catalogo.db"))):
        con = _solo_lectura(boveda.joinpath(*rel))
        if not con:
            continue
        try:
            for i, vec in con.execute("SELECT id, vec FROM vectores WHERE modelo = ?", (modelo,)):
                salida[f"{prefijo}:{i}"] = json.loads(vec)
        except sqlite3.Error:
            pass
        finally:
            con.close()
    return salida


def vectores_de(con: sqlite3.Connection, piezas: list[dict], embed=None, boveda: Path | None = None,
                guardar: bool = True, de_boveda: dict | None = None) -> dict[str, list[float]]:
    """Vector de cada pieza: el de la bóveda, el propio guardado o uno nuevo (que se guarda en la base propia)."""
    modelo = _modelo_emb()
    de_boveda = de_boveda if de_boveda is not None else _vectores_boveda(boveda or BOVEDA, modelo)
    vecs = {p["clave"]: de_boveda[p["clave"]] for p in piezas if p["clave"] in de_boveda}
    buscadas = {p["clave"] for p in piezas}
    for clave, vec in con.execute("SELECT clave, vec FROM vectores WHERE modelo = ?", (modelo,)):
        if clave not in vecs and clave in buscadas:
            vecs[clave] = json.loads(vec)
    faltan = [p for p in piezas if p["clave"] not in vecs]
    for i in range(0, len(faltan), 64):
        grupo = faltan[i:i + 64]
        try:
            nuevos = (embed or embed_ollama)([p["texto_emb"] for p in grupo])
        except Exception:  # noqa: BLE001 — sin Ollama no hay conexiones, pero sí fichas
            nuevos = None
        if not nuevos or len(nuevos) != len(grupo):
            break
        for p, v in zip(grupo, nuevos):
            vecs[p["clave"]] = v
        if guardar:
            con.executemany("INSERT OR REPLACE INTO vectores (clave, modelo, vec) VALUES (?, ?, ?)",
                            [(p["clave"], modelo, json.dumps(v)) for p, v in zip(grupo, nuevos)])
            con.commit()
    return vecs


def _unitario(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def pozo(con: sqlite3.Connection, boveda: Path | None = None, de_boveda: dict | None = None) -> list[tuple[str, str, list[float]]]:
    """Las piezas que ya existían y valen como conexión: las fichadas por el Clasificador, las noticias
    útiles (relevancia ≥ 2) y los videos ingeridos de la bóveda. (clave, título, vector unitario)."""
    boveda = boveda or BOVEDA
    modelo = _modelo_emb()
    de_boveda = de_boveda if de_boveda is not None else _vectores_boveda(boveda, modelo)
    titulos: dict[str, str] = {}
    for clave, titulo in con.execute("SELECT clave, titulo FROM fichas"):
        titulos[clave] = titulo or ""
    for prefijo, rel, sql in (("n", ("cache", "newsletter.db"), "SELECT id, titulo FROM items WHERE relevancia >= 2 AND descartado_por IS NULL "
                               "AND (grupo IS NULL OR grupo = id)"),
                              ("v", ("cache", "youtube", "catalogo.db"), "SELECT id, titulo FROM videos WHERE estado = 'ingerido'")):
        c = _solo_lectura(boveda.joinpath(*rel))
        if not c:
            continue
        try:
            for i, titulo in c.execute(sql):
                titulos.setdefault(f"{prefijo}:{i}", titulo or "")
        except sqlite3.Error:
            pass
        finally:
            c.close()
    propios = {k: json.loads(v) for k, v in con.execute("SELECT clave, vec FROM vectores WHERE modelo = ?", (modelo,))}
    salida = []
    for clave, titulo in titulos.items():
        vec = propios.get(clave) or de_boveda.get(clave)
        if vec:
            salida.append((clave, titulo, _unitario(vec)))
    return salida


def conectar(clave: str, vec: list[float], pozo_: list[tuple[str, str, list[float]]], umbral: float = UMBRAL) -> list[dict]:
    """Hasta 3 piezas parecidas (coseno ≥ umbral), sin contarse a sí misma ni a sus duplicados."""
    u = _unitario(vec)
    candidatas = []
    for otra, titulo, w in pozo_:
        if otra == clave:
            continue
        sim = sum(a * b for a, b in zip(u, w))
        if umbral <= sim < MISMA:
            candidatas.append({"clave": otra, "titulo": titulo, "sim": round(sim, 3)})
    candidatas.sort(key=lambda c: c["sim"], reverse=True)
    return candidatas[:MAX_CONEXIONES]


# ---------- la corrida diaria ----------

def _corto(t: str, n: int = 48) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def filas_suite(nuevas: list[dict], total: int) -> list[list[str]]:
    """3–5 filas útiles para «La bóveda ordenada»."""
    if not nuevas:
        return [["Hoy", "Nada nuevo que fichar"], ["Fichadas en total", str(total)], ["Vuelve", f"Mañana a las {HORA_DIARIO}"]]
    n3 = [f for f in nuevas if f["nivel"] == 3]
    filas = [["Entraron", f"{len(nuevas)} piezas, {len(n3)} accionables"]]
    usos: dict[str, int] = {}
    for f in nuevas:
        usos[f["uso"]] = usos.get(f["uso"], 0) + 1
    if usos.get("vender"):
        filas.append(["Para vender", f"{usos['vender']} {'pieza nueva' if usos['vender'] == 1 else 'piezas nuevas'}"])
    otro = max((u for u in usos if u != "vender"), key=lambda u: usos[u], default=None)
    if otro:
        filas.append([f"Para {otro}", f"{usos[otro]} {'pieza' if usos[otro] == 1 else 'piezas'}"])
    frentes: dict[str, int] = {}
    for f in nuevas:
        if f["frente"] != "general":
            frentes[f["frente"]] = frentes.get(f["frente"], 0) + 1
    if frentes:
        top = max(frentes, key=lambda k: frentes[k])
        filas.append([f"Toca a {NOMBRE_FRENTE[top]}", f"{frentes[top]} {'pieza' if frentes[top] == 1 else 'piezas'}"])
    mejor = max(((f, c) for f in nuevas for c in f.get("conexiones") or []), key=lambda fc: fc[1]["sim"], default=None)
    if mejor:
        filas.append(["Conectado", f"{_corto(mejor[0]['titulo'], 40)} con {_corto(mejor[1]['titulo'], 40)}"])
    elif n3:
        filas.append(["Lo más accionable", _corto(n3[0]["titulo"], 80)])
    return filas[:5]


def _guardar(con: sqlite3.Connection, f: dict, cuando: str) -> None:
    con.execute("INSERT OR IGNORE INTO fichas (clave, tipo, origen_id, titulo, fuente, enlace, nivel, uso, frente, por_que, por, conexiones, creada_en) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f["clave"], f["tipo"], f["origen_id"], f["titulo"], f["fuente"], f["enlace"], f["nivel"], f["uso"], f["frente"],
                 f["por_que"], f["por"], None if f.get("conexiones") is None else json.dumps(f["conexiones"], ensure_ascii=False), cuando))


def fichar(con: sqlite3.Connection, piezas: list[dict], ahora: datetime, probar: bool = False, claude=None, embed=None,
           avisar=None, boveda: Path | None = None, mente: Path | None = None) -> tuple[list[dict], str]:
    """Ficha y conecta las piezas que no tienen ficha. Devuelve (fichas nuevas, quién fichó: claude|local|nadie)."""
    boveda = boveda or BOVEDA
    nuevas = sin_fichar(con, piezas)
    de_boveda = _vectores_boveda(boveda, _modelo_emb())
    pozo_ = pozo(con, boveda, de_boveda)                       # antes de guardar: solo lo que ya existía
    vecs = vectores_de(con, nuevas, embed, boveda, guardar=not probar, de_boveda=de_boveda)
    por = "nadie"
    del_llm: dict[str, dict] = {}
    if nuevas:
        try:
            del_llm = fichar_con_claude(nuevas, claude, mente)
            por = "claude"
        except Exception as exc:  # noqa: BLE001 — sin Claude sale la versión local
            por = "local"
            if not probar:
                _avisar_una_vez(con, "fichas", f"El Clasificador no pudo fichar con Claude ({type(exc).__name__}: {str(exc)[:150]}). "
                                f"Fichó la versión local sin LLM.", avisar, ahora.date())
    cuando = ahora.isoformat(timespec="seconds")
    salida = []
    for p in nuevas:
        ficha = del_llm.get(p["clave"]) or ficha_local(p, vecs.get(p["clave"]))
        vec = vecs.get(p["clave"])
        f = {**p, **ficha, "conexiones": conectar(p["clave"], vec, pozo_) if vec else None}
        salida.append(f)
        if not probar:
            _guardar(con, f, cuando)
    if not probar:
        con.commit()
    return salida, por


def reconectar(con: sqlite3.Connection, embed=None, boveda: Path | None = None, dias: int = 7) -> int:
    """Las fichas que quedaron sin conexiones porque Ollama no estaba: se intenta otra vez (máx. una semana)."""
    desde = (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")
    filas = [dict(r) for r in con.execute("SELECT clave, tipo, titulo, fuente FROM fichas WHERE conexiones IS NULL AND creada_en >= ?", (desde,))]
    if not filas:
        return 0
    piezas = [{**f, "texto_emb": f"{f['titulo']} ({f['fuente']})" if f["tipo"] == "video" else f["titulo"]} for f in filas]
    de_boveda = _vectores_boveda(boveda or BOVEDA, _modelo_emb())
    vecs = vectores_de(con, piezas, embed, boveda, de_boveda=de_boveda)
    pozo_ = pozo(con, boveda, de_boveda)
    hechas = 0
    for p in piezas:
        if p["clave"] in vecs:
            con.execute("UPDATE fichas SET conexiones = ? WHERE clave = ?",
                        (json.dumps(conectar(p["clave"], vecs[p["clave"]], pozo_), ensure_ascii=False), p["clave"]))
            hechas += 1
    con.commit()
    return hechas


def diario(ahora: datetime | None = None, probar: bool = False, claude=None, embed=None, avisar=None, publicar=None,
           con: sqlite3.Connection | None = None, boveda: Path | None = None, mente: Path | None = None, horas: int = VENTANA_H) -> dict:
    ahora = ahora or datetime.now()
    if not probar:
        _reportar("trabajando", "Fichando lo que entró a la bóveda")
    try:
        r = _diario(ahora, probar, claude, embed, avisar, publicar, con, boveda, mente, horas)
    except Exception as exc:
        if not probar:
            _reportar("error", f"Se cayó: {type(exc).__name__}")
        raise
    if not probar:
        _reportar("durmiendo", f"Vuelve mañana a las {HORA_DIARIO}",
                  ultimo=f"Fichó {len(r['fichas'])} piezas el {ahora.day}-{ahora.month:02d}" + (" (versión local)" if r["por"] == "local" else ""))
    return r


def _diario(ahora, probar, claude, embed, avisar, publicar, con, boveda, mente, horas) -> dict:
    propia = con is None
    con = con or abrir(probar=probar)
    try:
        piezas = piezas_nuevas(ahora, horas, boveda, mente)
        nuevas, por = fichar(con, piezas, ahora, probar, claude, embed, avisar, boveda, mente)
        if not probar:
            reconectar(con, embed, boveda)
        total = con.execute("SELECT COUNT(*) FROM fichas").fetchone()[0] + (len(nuevas) if probar else 0)
        filas = filas_suite(nuevas, total)
        if not probar:
            (publicar or _publicar_piso)(filas)
        return {"fichas": nuevas, "por": por, "filas": filas}
    finally:
        if propia:
            con.close()


# ---------- el memo semanal ----------

def semana_de(d: date) -> str:
    a, s, _ = d.isocalendar()
    return f"{a}-W{s:02d}"


def _rango(semana: str) -> tuple[date, date]:
    a, s = semana.split("-W")
    lunes = date.fromisocalendar(int(a), int(s), 1)
    return lunes, lunes + timedelta(days=6)


def ruta_memo(semana: str, mente: Path | None = None) -> Path:
    return (mente or MENTE) / "mundo" / "newsletter" / f"_memo-{semana}.md"


def de_la_semana(con: sqlite3.Connection, semana: str) -> list[dict]:
    lunes, domingo = _rango(semana)
    filas = con.execute("SELECT * FROM fichas WHERE creada_en >= ? AND creada_en < ? ORDER BY nivel DESC, creada_en",
                        (lunes.isoformat(), (domingo + timedelta(days=1)).isoformat())).fetchall()
    return [{**dict(f), "conexiones": json.loads(f["conexiones"]) if f["conexiones"] else []} for f in filas]


def _conteo(fichas: list[dict], campo: str) -> dict[str, int]:
    c: dict[str, int] = {}
    for f in fichas:
        c[str(f[campo])] = c.get(str(f[campo]), 0) + 1
    return dict(sorted(c.items(), key=lambda kv: kv[1], reverse=True))


def para_el_memo(fichas: list[dict]) -> dict:
    fuertes = [f for f in fichas if f["nivel"] >= 2][:40]
    conexiones = sorted(((f["titulo"], c["titulo"], c["sim"]) for f in fichas for c in f["conexiones"]), key=lambda x: x[2], reverse=True)[:5]
    return {"total": len(fichas), "por_frente": _conteo(fichas, "frente"), "por_uso": _conteo(fichas, "uso"), "por_nivel": _conteo(fichas, "nivel"),
            "piezas": [{"titulo": f["titulo"], "nivel": f["nivel"], "uso": f["uso"], "frente": f["frente"], "por_que": f["por_que"],
                        "fuente": f["fuente"]} for f in fuertes],
            "conexiones": [{"pieza": a, "se_parece_a": b} for a, b, _ in conexiones]}


def leer_memo(texto: str) -> dict:
    datos = _parsear_json(texto)
    linea = str(datos.get("linea") or "").strip()
    if not linea:
        raise ValueError("el memo llegó sin línea")
    rec = datos.get("recomendacion") if isinstance(datos.get("recomendacion"), dict) else {}
    tipo = str(rec.get("tipo") or "seguir").strip().lower()
    return {"linea": linea[:200], "cambio": [str(x).strip() for x in datos.get("cambio") or [] if str(x).strip()][:3],
            "recomendacion": {"tipo": tipo if tipo in TIPOS_MEMO else "seguir", "texto": str(rec.get("texto") or "").strip()},
            "vigilar": [str(x).strip() for x in datos.get("vigilar") or [] if str(x).strip()][:2], "por": "claude"}


def memo_local(semana: str, fichas: list[dict]) -> dict:
    """Sin Claude: el conteo honesto y ninguna recomendación inventada."""
    d = para_el_memo(fichas)
    frentes = [k for k in d["por_frente"] if k != "general"]
    n3 = [f for f in fichas if f["nivel"] == 3]
    linea = (f"Semana {semana}: {d['total']} piezas, {len(n3)} accionables"
             + (f"; la mayoría toca a {NOMBRE_FRENTE.get(frentes[0], frentes[0])}." if frentes else "."))
    cambio = [f"Lo más accionable: {_corto(f['titulo'], 90)}." for f in n3[:3]]
    return {"linea": linea, "cambio": cambio, "recomendacion": {"tipo": "seguir", "texto": "Sin lectura de Claude esta semana: solo el conteo, ninguna recomendación."},
            "vigilar": [], "por": "automatico"}


def markdown_memo(semana: str, memo: dict, fichas: list[dict], hoy: date) -> str:
    d = para_el_memo(fichas)
    usos = ", ".join(f"{v} para {k}" for k, v in d["por_uso"].items())
    lineas = ["---", "tipo: memo", f"semana: {semana}", f"fecha: {hoy.isoformat()}", f"linea: {json.dumps(memo['linea'], ensure_ascii=False)}",
              f"recomendacion: {memo['recomendacion']['tipo']}", f"por: {memo['por']}", "fuente: agente Clasificador (fichas de la bóveda)", "---",
              f"# Memo de la semana {semana}", "", memo["linea"], ""]
    if memo["cambio"]:
        lineas += ["## Qué cambió"] + [f"- {c}" for c in memo["cambio"]] + [""]
    rec = memo["recomendacion"]
    lineas += ["## Qué haría", f"**{rec['tipo'].capitalize()}.** {rec['texto']}".strip(), ""]
    if memo["vigilar"]:
        lineas += ["## Vigilar"] + [f"- {v}" for v in memo["vigilar"]] + [""]
    lineas += ["## Lo que entró", f"- {d['total']} piezas" + (f": {usos}." if usos else ".")]
    lineas += [f"- Conectado: {c['pieza']} con {c['se_parece_a']}" for c in d["conexiones"][:3]]
    return "\n".join(lineas).rstrip() + "\n"


def _bloques_notion(md: str, rt) -> list[dict]:
    cuerpo = md.split("---", 2)[2] if md.startswith("---") else md
    bloques = []
    for l in cuerpo.splitlines():
        l = l.replace("**", "").rstrip()
        if not l.strip() or l.startswith("# "):
            continue
        if l.startswith("## "):
            bloques.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": rt(l[3:])}})
        elif l.startswith("- "):
            bloques.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(l[2:])}})
        else:
            bloques.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(l)}})
    return bloques


def publicar_notion(semana: str, md: str, linea: str, hoy: date, tok: str | None = None, post=None) -> str | None:
    """Una página en la base «Newsletter» (o bajo NOTION_MEMO_PADRE si se define). Sin token o si Notion
    no acepta, None: el memo se queda en el markdown."""
    import newsletter_notion as nn
    tok = tok if tok is not None else nn.token()
    if not tok:
        return None
    titulo = f"Memo de la semana {semana}"
    padre = os.environ.get("NOTION_MEMO_PADRE")
    if padre:
        cuerpo = {"parent": {"page_id": padre}, "properties": {"title": {"title": nn._rt(titulo)}}}
    else:
        cuerpo = {"parent": {"database_id": nn.base()}, "properties": {
            "Tema": {"title": nn._rt(titulo)}, "Fecha": {"date": {"start": hoy.isoformat()}}, "En una línea": {"rich_text": nn._rt(linea)},
            "Formato": {"select": {"name": "Memo"}}, "Clave": {"rich_text": nn._rt(f"memo-{semana}")}}}
    cuerpo.update({"icon": {"emoji": "🧭"}, "children": _bloques_notion(md, nn._rt)})
    try:
        r = (post or nn._post)("/pages", cuerpo, tok)
    except Exception:  # noqa: BLE001
        return None
    return r.get("url") or "publicada"


def semanal(hoy: date | None = None, probar: bool = False, claude=None, embed=None, avisar=None, publicar=None, notion=None,
            con: sqlite3.Connection | None = None, boveda: Path | None = None, mente: Path | None = None) -> dict:
    hoy = hoy or date.today()
    if not probar:
        _reportar("trabajando", "Escribiendo el memo de la semana")
    try:
        r = _semanal(hoy, probar, claude, embed, avisar, publicar, notion, con, boveda, mente)
    except Exception as exc:
        if not probar:
            _reportar("error", f"Se cayó el memo: {type(exc).__name__}")
        raise
    if not probar:
        _reportar("durmiendo", f"Vuelve mañana a las {HORA_DIARIO}", ultimo=f"Escribió el memo {r['semana']}" + (" (automático)" if r["memo"]["por"] != "claude" else ""))
    return r


def _semanal(hoy, probar, claude, embed, avisar, publicar, notion, con, boveda, mente) -> dict:
    mente = mente or MENTE
    propia = con is None
    con = con or abrir(probar=probar)
    try:
        ahora = datetime.combine(hoy, datetime.now().time())
        fichar(con, piezas_nuevas(ahora, VENTANA_H, boveda, mente), ahora, probar, claude, embed, avisar, boveda, mente)  # lo pendiente
        semana = semana_de(hoy)
        fichas = de_la_semana(con, semana)
        anterior = linea_para_newsletter(semana_de(hoy - timedelta(days=7)), mente)
        try:
            mensaje = ("Tarea: memo.\n\nSemana " + semana + " (JSON):\n" + json.dumps(para_el_memo(fichas), ensure_ascii=False)
                       + ("\n\nMemo de la semana pasada: " + anterior if anterior else "") + "\n\nFicha de JC:\n" + ficha_de_jc(mente))
            memo = leer_memo((claude or (lambda s, m: llamar_claude(s, m, MODELO_MEMO)))(_instrucciones(), mensaje))
        except Exception as exc:  # noqa: BLE001
            memo = memo_local(semana, fichas)
            if not probar:
                _avisar_una_vez(con, "memo", f"El Clasificador no pudo escribir el memo con Claude ({type(exc).__name__}: {str(exc)[:150]}). "
                                f"Quedó la versión automática.", avisar, hoy)
        md = markdown_memo(semana, memo, fichas, hoy)
        if probar:
            return {"semana": semana, "memo": memo, "markdown": md, "notion": None}
        ruta = ruta_memo(semana, mente)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = ruta.with_suffix(".tmp")
        tmp.write_text(md, encoding="utf-8")
        os.replace(tmp, ruta)
        previa = con.execute("SELECT notion_url FROM memos WHERE semana = ?", (semana,)).fetchone()
        url = previa[0] if previa and previa[0] else (notion or publicar_notion)(semana, md, memo["linea"], hoy)
        con.execute("INSERT OR REPLACE INTO memos (semana, ruta, linea, notion_url, por, en) VALUES (?,?,?,?,?,?)",
                    (semana, str(ruta), memo["linea"], url, memo["por"], datetime.now().isoformat(timespec="seconds")))
        con.commit()
        (publicar or _publicar_piso)(filas_memo(semana, memo, fichas))
        return {"semana": semana, "memo": memo, "markdown": md, "notion": url, "ruta": str(ruta)}
    finally:
        if propia:
            con.close()


def filas_memo(semana: str, memo: dict, fichas: list[dict]) -> list[list[str]]:
    d = para_el_memo(fichas)
    filas = [["Memo " + semana, _corto(memo["linea"], 90)], ["Qué haría", memo["recomendacion"]["tipo"].capitalize()],
             ["La semana", f"{d['total']} piezas fichadas"]]
    if d["por_uso"].get("vender"):
        filas.append(["Para vender", f"{d['por_uso']['vender']} piezas en la semana"])
    return filas


def linea_para_newsletter(semana: str | date, mente: Path | None = None) -> str:
    """UNA línea del memo para la newsletter del domingo. Vacía si esa semana no hay memo."""
    semana = semana_de(semana) if isinstance(semana, date) else str(semana)
    try:
        texto = ruta_memo(semana, mente).read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^linea:\s*(.+)$", texto, re.M)
    if not m:
        return ""
    valor = m.group(1).strip()
    try:
        valor = json.loads(valor) if valor.startswith('"') else valor
    except ValueError:
        pass
    return f"Memo de la semana: {valor}" if valor else ""


def _imprimir_diario(r: dict) -> str:
    lineas = [f"{len(r['fichas'])} piezas nuevas (fichó: {r['por']})"]
    for f in r["fichas"]:
        con_ = "; ".join(_corto(c["titulo"], 40) for c in f.get("conexiones") or [])
        lineas.append(f"- [{f['nivel']}·{f['uso']}·{f['frente']}] {_corto(f['titulo'], 80)}" + (f"  ↔ {con_}" if con_ else ""))
    lineas += ["", "Suite:"] + [f"  {a}: {b}" for a, b in r["filas"]]
    return "\n".join(lineas)


if __name__ == "__main__":
    probar = "--probar" in sys.argv
    if "--semanal" in sys.argv:
        r = semanal(probar=probar)
        print(r["markdown"] if probar else f"memo {r['semana']} → {r.get('ruta')} · Notion: {r.get('notion') or 'no'}")
    elif "--diario" in sys.argv or probar:
        print(_imprimir_diario(diario(probar=probar)))
    else:
        print(__doc__)

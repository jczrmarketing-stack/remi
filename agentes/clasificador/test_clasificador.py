"""El agente Clasificador: fichas validadas, versión local si Claude falla, conexiones por embeddings,
la Suite, el memo semanal. Todo con dobles: ninguna prueba toca la mente, la bóveda ni el estado reales."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("BOVEDA_SIN_LOG", "1")
os.environ.setdefault("REMI_ESTADO_AGENTES", tempfile.mkdtemp())   # la Suite: nunca el estado real
os.environ.setdefault("REMI_ESTADO_PISOS", tempfile.mkdtemp())
os.environ["CLASIFICADOR_BD"] = str(Path(tempfile.mkdtemp()) / "nunca.db")
import clasificador as cl  # noqa: E402

AHORA = datetime(2026, 11, 4, 22, 0)
DOMINGO = date(2026, 11, 8)
VECTORES = {"claude code": [1.0, 0.5, 0.0, 0.0], "fiverr": [0.0, 1.0, 0.0, 0.0], "wyoming": [0.0, 0.0, 1.0, 0.0]}


def embed_falso(textos):
    salida = []
    for t in textos:
        v = next((v for k, v in VECTORES.items() if k in t.lower()), [0.0, 0.0, 0.0, 1.0])
        salida.append(list(v))
    return salida


def _boveda() -> Path:
    raiz = Path(tempfile.mkdtemp())
    (raiz / "cache" / "youtube").mkdir(parents=True)
    modelo = cl._modelo_emb()
    utc = AHORA.astimezone(timezone.utc)
    con = sqlite3.connect(raiz / "cache" / "newsletter.db")
    con.execute("CREATE TABLE items (id TEXT PRIMARY KEY, fuente TEXT, nombre TEXT, titulo TEXT, link TEXT, extracto TEXT, visto_en TEXT, "
                "relevancia INTEGER, resumen_es TEXT, grupo TEXT, descartado_por TEXT)")
    con.execute("CREATE TABLE vectores (id TEXT NOT NULL, modelo TEXT NOT NULL, vec TEXT NOT NULL, PRIMARY KEY (id, modelo))")
    filas = [("viejo", "Agentes con Claude Code para clientes", (utc - timedelta(days=5)).isoformat(), 3, None, None),
             ("n1", "Cómo cobrar más en Fiverr con Claude Code", (utc - timedelta(hours=2)).isoformat(), 3, None, None),
             ("n2", "Wyoming cambia el reporte anual de las LLC", (utc - timedelta(hours=3)).isoformat(), 2, None, None),
             ("n3", "Duplicado de n2", (utc - timedelta(hours=3)).isoformat(), 2, "n2", None),
             ("n5", "Calificada 1", (utc - timedelta(hours=3)).isoformat(), 1, None, None),
             ("n4", "Descartada", (utc - timedelta(hours=3)).isoformat(), 0, None, "compuerta")]
    for i, titulo, visto, rel, grupo, desc in filas:
        con.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?)", (i, "hn", "Hacker News", titulo, f"https://x.com/{i}", "", visto, rel, titulo, grupo, desc))
    con.execute("INSERT INTO vectores VALUES (?,?,?)", ("viejo", modelo, json.dumps([1.0, 0.0, 0.0, 0.0])))
    con.commit(); con.close()
    con = sqlite3.connect(raiz / "cache" / "youtube" / "catalogo.db")
    con.execute("CREATE TABLE videos (id TEXT PRIMARY KEY, canal TEXT, titulo TEXT, relevancia INTEGER, estado TEXT, nota TEXT, ingerido_en TEXT)")
    con.execute("CREATE TABLE vectores (id TEXT NOT NULL, modelo TEXT NOT NULL, vec TEXT NOT NULL, PRIMARY KEY (id, modelo))")
    con.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?)", ("vid00000001", "cole-medin", "Mi fábrica de software con agentes", 3, "ingerido",
                                                              "oro 8  mundo/fuentes/youtube/fabrica-vid00000001.md", (AHORA - timedelta(hours=1)).isoformat()))
    con.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?)", ("vid00000002", "theo", "Video viejo", 2, "ingerido", "", (AHORA - timedelta(days=4)).isoformat()))
    con.commit(); con.close()
    return raiz


def _mente() -> Path:
    m = Path(tempfile.mkdtemp())
    (m / "mundo" / "fuentes" / "youtube").mkdir(parents=True)
    (m / "mundo" / "fuentes" / "youtube" / "fabrica-vid00000001.md").write_text("# x\n\n## Resumen\n- Cientos de PRs por semana con agentes.\n", encoding="utf-8")
    (m / "negocio").mkdir()
    (m / "negocio" / "frentes.md").write_text("---\ntipo: negocio\n---\n# Frentes\nUpVisuals, Fiverr, LLC.\n", encoding="utf-8")
    return m


def claude_falso(llamadas=None):
    def responder(sistema, mensaje):
        if llamadas is not None:
            llamadas.append(mensaje)
        if "Tarea: memo" in mensaje:
            return json.dumps({"linea": "Fiverr y Claude Code: subir precios ya.", "cambio": ["Más demanda de agentes."],
                               "recomendacion": {"tipo": "ajustar", "texto": "Sube el precio del gig de agentes."}, "vigilar": ["Wyoming."]})
        ids = [p["id"] for p in json.loads(mensaje.split("Piezas (JSON):\n", 1)[1].split("\n\nFicha de JC", 1)[0])]
        fichas = [{"id": i, "nivel": 3 if i == "n:n1" else 2, "uso": "vender" if i == "n:n1" else "RARO", "frente": "fiverr" if i == "n:n1" else "otro",
                   "por_que": "Cobra más."} for i in ids]
        return "```json\n" + json.dumps({"fichas": fichas + [{"id": "inventado", "nivel": 3}]}) + "\n```"
    return responder


def test_leer_respuesta_valida_ids_y_normaliza():
    piezas = [{"clave": "n:a"}, {"clave": "v:b"}]
    r = cl.leer_respuesta(json.dumps({"fichas": [{"id": "n:a", "nivel": 9, "uso": "Vender", "frente": "fiverr", "por_que": "x"},
                                                 {"id": "v:b", "nivel": "nada", "uso": "otro", "frente": "marte"}, {"id": "zz", "nivel": 3}]}), piezas)
    assert set(r) == {"n:a", "v:b"}
    assert r["n:a"]["nivel"] == 3 and r["n:a"]["uso"] == "vender" and r["n:a"]["frente"] == "fiverr"
    assert r["v:b"] == {"nivel": 1, "uso": "aprender", "frente": "general", "por_que": "", "por": "claude"}


def test_frente_y_uso_por_palabras():
    assert cl.frente_por_palabras("Wyoming LLC annual report") == "llc"
    assert cl.frente_por_palabras("How I price my Fiverr gigs") == "fiverr"
    assert cl.frente_por_palabras("Claude Code ships MCP hooks") == "remi"
    assert cl.frente_por_palabras("La Luna y los volcanes") == "general"
    assert cl.uso_por_palabras("Cómo conseguir clientes") == "vender" and cl.uso_por_palabras("Historia de Roma") == "aprender"


def test_diario_ficha_conecta_publica_y_no_repite():
    sys.path.append(str(cl.NUCLEO))
    import agentes_estado
    boveda, mente = _boveda(), _mente()
    con = cl.abrir(Path(tempfile.mkdtemp()) / "c.db")
    llamadas, publicadas, avisos = [], [], []
    r = cl.diario(AHORA, claude=claude_falso(llamadas), embed=embed_falso, avisar=avisos.append, publicar=publicadas.append,
                  con=con, boveda=boveda, mente=mente)
    claves = {f["clave"] for f in r["fichas"]}
    assert claves == {"n:n1", "n:n2", "v:vid00000001"}            # sin el viejo, el duplicado, la de relevancia 1, la descartada ni el video viejo
    n1 = next(f for f in r["fichas"] if f["clave"] == "n:n1")
    assert (n1["nivel"], n1["uso"], n1["frente"], r["por"]) == (3, "vender", "fiverr", "claude")
    assert [c["clave"] for c in n1["conexiones"]] == ["n:viejo"]   # coseno 0,89 ≥ umbral
    assert "Cientos de PRs" in llamadas[0] and not avisos
    filas = publicadas[0]
    assert 3 <= len(filas) <= 5 and ["Para vender", "1 pieza nueva"] in filas and any(f[0] == "Conectado" for f in filas)
    assert agentes_estado.leer("clasificador")["estado"] == "durmiendo"
    assert con.execute("SELECT COUNT(*) FROM fichas").fetchone()[0] == 3
    llamadas.clear()
    r2 = cl.diario(AHORA, claude=claude_falso(llamadas), embed=embed_falso, avisar=avisos.append, publicar=publicadas.append, con=con, boveda=boveda, mente=mente)
    assert r2["fichas"] == [] and not llamadas and publicadas[1][0] == ["Hoy", "Nada nuevo que fichar"]


def test_si_claude_falla_ficha_local_y_avisa_una_vez():
    boveda, mente = _boveda(), _mente()
    con = cl.abrir(Path(tempfile.mkdtemp()) / "c.db")
    avisos = []

    def roto(s, m):
        raise RuntimeError("límite de la suscripción")
    r = cl.diario(AHORA, claude=roto, embed=embed_falso, avisar=avisos.append, publicar=lambda f: None, con=con, boveda=boveda, mente=mente)
    por = {f["clave"]: f for f in r["fichas"]}
    assert r["por"] == "local" and por["n:n2"]["frente"] == "llc" and por["n:n2"]["nivel"] == 2 and por["n:n1"]["frente"] == "fiverr"
    assert len(avisos) == 1 and "versión local" in avisos[0]
    con.execute("DELETE FROM fichas")
    cl.diario(AHORA, claude=roto, embed=embed_falso, avisar=avisos.append, publicar=lambda f: None, con=con, boveda=boveda, mente=mente)
    assert len(avisos) == 1                                          # el mismo día no avisa dos veces


def test_probar_no_escribe_nada():
    boveda, mente = _boveda(), _mente()
    ruta = Path(tempfile.mkdtemp()) / "c.db"
    publicadas, avisos = [], []
    con = cl.abrir(ruta, probar=True)
    r = cl.diario(AHORA, probar=True, claude=lambda s, m: (_ for _ in ()).throw(RuntimeError("x")), embed=embed_falso,
                  avisar=avisos.append, publicar=publicadas.append, con=con, boveda=boveda, mente=mente)
    assert len(r["fichas"]) == 3 and r["filas"] and not publicadas and not avisos and not ruta.exists()
    assert con.execute("SELECT COUNT(*) FROM fichas").fetchone()[0] == 0


def test_sin_ollama_quedan_sin_conexiones_y_se_reintentan():
    boveda, mente = _boveda(), _mente()
    con = cl.abrir(Path(tempfile.mkdtemp()) / "c.db")
    hoy_real = datetime.now()
    cl.diario(hoy_real, claude=claude_falso(), embed=lambda t: None, avisar=lambda t: None, publicar=lambda f: None, con=con, boveda=boveda,
              mente=mente, horas=24 * 30)
    assert con.execute("SELECT COUNT(*) FROM fichas WHERE conexiones IS NULL").fetchone()[0] >= 3
    assert cl.reconectar(con, embed_falso, boveda) >= 3
    assert con.execute("SELECT COUNT(*) FROM fichas WHERE conexiones IS NULL").fetchone()[0] == 0


def test_memo_semanal_escribe_publica_y_da_linea():
    boveda, mente = _boveda(), _mente()
    con = cl.abrir(Path(tempfile.mkdtemp()) / "c.db")
    cl.diario(AHORA, claude=claude_falso(), embed=embed_falso, avisar=lambda t: None, publicar=lambda f: None, con=con, boveda=boveda, mente=mente)
    notion, publicadas = [], []
    r = cl.semanal(DOMINGO, claude=claude_falso(), embed=embed_falso, avisar=lambda t: None, publicar=publicadas.append,
                   notion=lambda sem, md, linea, hoy: notion.append((sem, md, linea)) or "https://notion.so/memo", con=con, boveda=boveda, mente=mente)
    ruta = mente / "mundo" / "newsletter" / "_memo-2026-W45.md"
    texto = ruta.read_text(encoding="utf-8")
    assert r["semana"] == "2026-W45" and r["notion"] == "https://notion.so/memo" and notion[0][0] == "2026-W45"
    assert "**Ajustar.** Sube el precio" in texto and "3 piezas" in texto and "recomendacion: ajustar" in texto
    assert cl.linea_para_newsletter("2026-W45", mente) == "Memo de la semana: Fiverr y Claude Code: subir precios ya."
    assert cl.linea_para_newsletter(DOMINGO, mente).endswith("subir precios ya.") and cl.linea_para_newsletter("2026-W40", mente) == ""
    assert publicadas[0][0][0] == "Memo 2026-W45"
    cl.semanal(DOMINGO, claude=claude_falso(), embed=embed_falso, avisar=lambda t: None, publicar=publicadas.append,
               notion=lambda *a: notion.append(a) or "otra", con=con, boveda=boveda, mente=mente)
    assert len(notion) == 1                                          # la página de Notion no se repite


def test_memo_sin_claude_ni_notion_queda_automatico_en_markdown():
    boveda, mente = _boveda(), _mente()
    con = cl.abrir(Path(tempfile.mkdtemp()) / "c.db")
    cl.diario(AHORA, claude=claude_falso(), embed=embed_falso, avisar=lambda t: None, publicar=lambda f: None, con=con, boveda=boveda, mente=mente)
    avisos = []
    r = cl.semanal(DOMINGO, claude=lambda s, m: "no es json", embed=embed_falso, avisar=avisos.append, publicar=lambda f: None,
                   notion=lambda *a: None, con=con, boveda=boveda, mente=mente)
    assert r["memo"]["por"] == "automatico" and r["notion"] is None and len(avisos) == 1
    assert "3 piezas, 1 accionables" in cl.linea_para_newsletter("2026-W45", mente)
    assert cl.publicar_notion("2026-W45", "# x", "l", DOMINGO, tok="") is None   # sin token no publica


def test_publicar_notion_arma_la_pagina():
    enviados = []
    url = cl.publicar_notion("2026-W45", "---\nx: 1\n---\n# Memo\n\nLínea\n\n## Qué cambió\n- **Algo**\n", "Línea", DOMINGO, tok="t",
                             post=lambda ruta, cuerpo, tok: enviados.append(cuerpo) or {"url": "https://notion.so/p"})
    tipos = [b["type"] for b in enviados[0]["children"]]
    assert url == "https://notion.so/p" and tipos == ["paragraph", "heading_2", "bulleted_list_item"]
    assert enviados[0]["properties"]["Clave"]["rich_text"][0]["text"]["content"] == "memo-2026-W45"


def test_llamar_claude_usa_la_suscripcion_sin_api():
    visto = {}

    class R:
        stdout = json.dumps({"result": "{}", "is_error": False})

    def correr(cmd, **kw):
        visto.update(cmd=cmd, env=kw["env"])
        return R()
    os.environ["ANTHROPIC_API_KEY"] = "no-debe-pasar"
    try:
        assert cl.llamar_claude("s", "m", correr=correr, binario="/x/claude") == "{}"
    finally:
        del os.environ["ANTHROPIC_API_KEY"]
    assert "ANTHROPIC_API_KEY" not in visto["env"] and visto["cmd"][:2] == ["/x/claude", "-p"] and "--tools" in visto["cmd"]

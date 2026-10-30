"""Métricas de uso de la mente: cuánto consulta Claude, cuánto le sirve y
cuántas búsquedas web se evita. Solo stdlib: lo usan los hooks (python3 del
sistema), el MCP y la noche.

Vive en `mente/metricas.db` (fuera de git). Si falla, nadie se entera: una
métrica nunca rompe una sesión.

Definiciones honestas (uso.md las repite):
- consulta: una vez que el hook o `preguntar` buscó en la mente.
- con_algo: la consulta devolvió al menos una ficha.
- acierto: después de recibir fichas, Claude pidió `leer` (las usó).
- web_despues: después de recibir fichas, Claude buscó en la web igual.
- web_evitada: con_algo y acierto y sin web_despues. Es un proxy, no una verdad.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import vida

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS consultas (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    origen TEXT NOT NULL,
    sesion TEXT NOT NULL,
    consulta TEXT NOT NULL,
    n INTEGER NOT NULL,
    chars INTEGER NOT NULL,
    ids TEXT NOT NULL,
    acierto INTEGER NOT NULL DEFAULT 0,
    web_despues INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    sesion TEXT NOT NULL,
    tipo TEXT NOT NULL,
    detalle TEXT NOT NULL
);
"""
VENTANA_MIN = 30  # una web o un leer cuentan para la última consulta de la sesión si fue hace menos de esto


def ruta() -> Path:
    return vida.MENTE / "metricas.db"


def _ahora() -> datetime:
    return datetime.fromisoformat(os.environ["REMI_AHORA"]) if os.environ.get("REMI_AHORA") else datetime.now()


def _con() -> sqlite3.Connection:
    ruta().parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta(), timeout=2)
    con.executescript(_ESQUEMA)
    return con


def registrar_consulta(origen: str, sesion: str, consulta: str, ids: list[str], chars: int) -> None:
    try:
        with _con() as con:
            con.execute(
                "INSERT INTO consultas (ts, origen, sesion, consulta, n, chars, ids) VALUES (?,?,?,?,?,?,?)",
                (_ahora().isoformat(timespec="seconds"), origen, sesion or "-", consulta[:300], len(ids), chars, json.dumps(ids)),
            )
    except sqlite3.Error:
        pass


def _ultima(con: sqlite3.Connection, sesion: str) -> sqlite3.Row | None:
    con.row_factory = sqlite3.Row
    fila = con.execute("SELECT id, ts, n FROM consultas WHERE sesion = ? ORDER BY id DESC LIMIT 1", (sesion,)).fetchone()
    if fila is None:
        return None
    if _ahora() - datetime.fromisoformat(fila["ts"]) > timedelta(minutes=VENTANA_MIN):
        return None
    return fila


def marcar(sesion: str, que: str, detalle: str = "") -> None:
    """que: 'acierto' (Claude leyó una nota) | 'web' (buscó en la web) | otro (solo evento)."""
    try:
        with _con() as con:
            con.execute("INSERT INTO eventos (ts, sesion, tipo, detalle) VALUES (?,?,?,?)",
                        (_ahora().isoformat(timespec="seconds"), sesion or "-", que, detalle[:300]))
            columna = {"acierto": "acierto", "web": "web_despues"}.get(que)
            if not columna:
                return
            ultima = _ultima(con, sesion or "-")
            if ultima is not None and ultima["n"] > 0:
                con.execute(f"UPDATE consultas SET {columna} = 1 WHERE id = ?", (ultima["id"],))
    except sqlite3.Error:
        pass


def resumen(dias: int = 7) -> dict:
    desde = (_ahora() - timedelta(days=dias)).isoformat(timespec="seconds")
    vacio = {"dias": dias, "consultas": 0, "con_algo": 0, "aciertos": 0, "web_despues": 0, "web_evitadas": 0, "chars": 0, "tokens_aprox": 0, "por_origen": {}}
    try:
        with _con() as con:
            con.row_factory = sqlite3.Row
            f = con.execute(
                "SELECT COUNT(*) c, SUM(n > 0) a, SUM(acierto) ac, SUM(web_despues) w, "
                "SUM(CASE WHEN n > 0 AND acierto = 1 AND web_despues = 0 THEN 1 ELSE 0 END) ev, SUM(chars) ch "
                "FROM consultas WHERE ts >= ?", (desde,)).fetchone()
            origenes = con.execute("SELECT origen, COUNT(*) c FROM consultas WHERE ts >= ? GROUP BY origen", (desde,)).fetchall()
    except sqlite3.Error:
        return vacio
    chars = int(f["ch"] or 0)
    return {
        "dias": dias, "consultas": int(f["c"] or 0), "con_algo": int(f["a"] or 0), "aciertos": int(f["ac"] or 0),
        "web_despues": int(f["w"] or 0), "web_evitadas": int(f["ev"] or 0), "chars": chars, "tokens_aprox": chars // 4,
        "por_origen": {o["origen"]: int(o["c"]) for o in origenes},
    }


def texto_uso(dias: int = 7, notas_nuevas: int | None = None) -> str:
    r = resumen(dias)
    tasa = f"{100 * r['aciertos'] // r['con_algo']} %" if r["con_algo"] else "sin dato"
    lineas = [
        f"# Uso de la mente · últimos {dias} días",
        "",
        f"Actualizado {_ahora().strftime('%Y-%m-%d %H:%M')}. Lo escribe la noche desde `metricas.db`; cero tokens.",
        "",
        "| Métrica | Valor | Qué significa |",
        "| --- | --- | --- |",
        f"| Consultas | {r['consultas']} | veces que el hook o `preguntar` buscaron en la mente |",
        f"| Con algo | {r['con_algo']} | devolvieron al menos una ficha |",
        f"| Aciertos | {r['aciertos']} ({tasa}) | Claude pidió `leer` después: usó lo que recibió |",
        f"| Web después | {r['web_despues']} | buscó en la web igual: la mente no bastó |",
        f"| Webs evitadas | {r['web_evitadas']} | con algo + acierto + sin web (proxy, no verdad) |",
        f"| Contexto inyectado | ~{r['tokens_aprox']:,} tokens | fichas, nunca cuerpos |",
    ]
    if notas_nuevas is not None:
        lineas.append(f"| Notas nuevas | {notas_nuevas} | entraron a la mente o la bóveda |")
    if r["por_origen"]:
        lineas += ["", "Por origen: " + ", ".join(f"{k} {v}" for k, v in sorted(r["por_origen"].items())) + "."]
    lineas += ["", "Si «Web después» crece y «Aciertos» no, el router o el índice no sirven: se cambia. Si «Consultas» es 0, el hook no está instalado (`python3 scripts/instalar_hook_claude.py --aplicar`)."]
    return "\n".join(lineas) + "\n"

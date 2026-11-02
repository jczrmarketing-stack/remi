"""Evaluación de la búsqueda de la mente (F1.5c). Un cambio de modelo, de
reordenador o de umbral se adopta solo si esto dice que mejora.

Tres fuentes de casos, de más a menos confiable:
1. semilla  — `evaluacion/casos.jsonl` (tipo «busqueda», escritos a mano);
2. reales   — consultas de `metricas.db` seguidas de un `leer` en la misma sesión
              (la nota que Claude abrió es la que sí servía);
3. sintéticas — dos preguntas por nota pública, hechas por un modelo gratis
              (`--generar N`, se guardan en `evaluacion/sinteticas.jsonl`).

Métricas por modo (texto | vector | hibrida | rerank):
  recall@5 — la nota esperada aparece entre las 5 primeras
  MRR      — 1/posición de la primera esperada (0 si no sale)
  tokens   — tamaño medio de lo que se le entregaría a Claude (≈ chars/4)

    python3 nucleo/evaluar.py                  # evalúa y escribe mente/evaluacion.md
    python3 nucleo/evaluar.py --generar 40     # primero crea hasta 40 notas × 2 preguntas
    python3 nucleo/evaluar.py --modos hibrida,rerank --sin-escribir
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import vida

_AQUI = Path(__file__).resolve().parent
CASOS = _AQUI / "evaluacion" / "casos.jsonl"
TIPOS_PUBLICOS = ("fuente", "repo", "investigacion", "campo")  # nunca yo/ ni negocio/ hacia APIs gratis
import donde_boveda  # noqa: E402

BOVEDA = Path(os.environ.get("BOVEDA_RAIZ") or donde_boveda.ubicar() or donde_boveda.INTERNA)


def _dir_eval() -> Path:
    return vida.MENTE / "evaluacion"


# ---------- puro: métricas ----------

def _es(id_nota: str, esperado: str) -> bool:
    """El id del índice es la ruta de la nota («mundo/fuentes/instagram/…-Dc0wusZtJK3.md»);
    los casos escritos a mano traen solo el código del post. Vale igual o contenido."""
    return id_nota == esperado or esperado in id_nota


def recall_en_k(ids: list[str], esperados: list[str], k: int = 5) -> float:
    """1.0 si alguna esperada está entre las k primeras (los casos tienen una o varias válidas)."""
    return 1.0 if any(_es(i, e) for i in ids[:k] for e in esperados) else 0.0


def rr(ids: list[str], esperados: list[str]) -> float:
    for posicion, id_nota in enumerate(ids, start=1):
        if any(_es(id_nota, e) for e in esperados):
            return 1.0 / posicion
    return 0.0


def tokens_de(hallazgos) -> int:
    return round(sum(len(h.titulo) + len(h.resumen) + len(h.id) + 20 for h in hallazgos) / 4)


def resumir(filas: list[dict]) -> dict:
    n = len(filas) or 1
    return {
        "casos": len(filas),
        "recall5": sum(f["recall5"] for f in filas) / n,
        "mrr": sum(f["mrr"] for f in filas) / n,
        "tokens": sum(f["tokens"] for f in filas) / n,
    }


def decidir(base: dict, candidato: dict, margen_tokens: float = 1.1) -> str:
    """Regla de adopción: sube recall@5 y no sube los tokens más de 10 %."""
    if candidato["casos"] == 0:
        return "sin casos"
    if candidato["recall5"] > base["recall5"] and candidato["tokens"] <= base["tokens"] * margen_tokens:
        return "ADOPTAR"
    if candidato["recall5"] == base["recall5"] and candidato["mrr"] > base["mrr"] + 0.02:
        return "adoptar si el costo es bajo (solo mejora el orden)"
    return "no adoptar"


# ---------- casos ----------

def casos_semilla(ruta: Path = CASOS) -> list[dict]:
    casos = []
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                c = json.loads(linea)
                if c.get("tipo") == "busqueda":
                    casos.append({"consulta": c["consulta"], "esperados": c["espera_ids"], "origen": "semilla"})
    return casos


def casos_reales(ruta_db: Path | None = None, dias: int = 60) -> list[dict]:
    ruta_db = ruta_db or (vida.MENTE / "metricas.db")
    if not ruta_db.exists():
        return []
    con = sqlite3.connect(ruta_db)
    try:
        corte = (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")
        consultas = con.execute("SELECT id, ts, sesion, consulta FROM consultas WHERE ts >= ? ORDER BY id", (corte,)).fetchall()
        eventos = con.execute("SELECT ts, sesion, detalle FROM eventos WHERE tipo = 'acierto' AND detalle LIKE '%:%' AND ts >= ?", (corte,)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    casos = []
    for _id, ts, sesion, consulta in consultas:
        t0 = datetime.fromisoformat(ts)
        leidos = [d.rsplit(":", 1)[1] for t, s, d in eventos
                  if s == sesion and t0 <= datetime.fromisoformat(t) <= t0 + timedelta(minutes=30)]
        if leidos and len(consulta.split()) >= 3:
            casos.append({"consulta": consulta, "esperados": sorted(set(leidos)), "origen": "real"})
    return casos


def casos_sinteticos(ruta: Path | None = None) -> list[dict]:
    ruta = ruta or (_dir_eval() / "sinteticas.jsonl")
    if not ruta.exists():
        return []
    return [{**json.loads(l), "origen": "sintetica"} for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def generar_sinteticas(conexion, tope: int, por_nota: int = 2, ruta: Path | None = None) -> int:
    """Pide a un modelo gratis preguntas que cada nota pública responda. Solo notas
    públicas; los motores viven en la bóveda y se importan desde ahí."""
    ruta = ruta or (_dir_eval() / "sinteticas.jsonl")
    sys.path.insert(0, str(BOVEDA))
    import motores  # type: ignore

    ya = {c["nota_id"] for c in casos_sinteticos(ruta) if "nota_id" in c}
    marcas = ",".join("?" for _ in TIPOS_PUBLICOS)
    filas = conexion.execute(
        f"SELECT id, titulo, resumen FROM notas WHERE tipo IN ({marcas}) ORDER BY RANDOM()", TIPOS_PUBLICOS
    ).fetchall()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    hechas = 0
    esquema = {"type": "object", "properties": {"preguntas": {"type": "array", "items": {"type": "string"}}}, "required": ["preguntas"]}
    with ruta.open("a", encoding="utf-8") as f:
        for fila in filas:
            if fila["id"] in ya or not fila["resumen"]:
                continue
            mensajes = [
                {"role": "system", "content": f"Escribe {por_nota} preguntas en español, como las haría una persona que NO conoce la nota, que esta nota responda. No copies el título ni nombres propios si no hace falta. Responde JSON: {{\"preguntas\": [...]}}"},
                {"role": "user", "content": f"Título: {fila['titulo']}\nResumen: {fila['resumen']}"},
            ]
            try:
                datos, _crudo, _motor = motores.completar(mensajes, esquema, publico=True)
            except Exception:  # noqa: BLE001 — sin motor: se detiene, la corrida siguiente retoma
                break
            for pregunta in (datos.get("preguntas") or [])[:por_nota]:
                if isinstance(pregunta, str) and len(pregunta.split()) >= 4:
                    f.write(json.dumps({"consulta": pregunta, "esperados": [fila["id"]], "nota_id": fila["id"]}, ensure_ascii=False) + "\n")
            hechas += 1
            if hechas >= tope:
                break
    return hechas


# ---------- correr ----------

def correr(conexion, casos: list[dict], modos: list[str]) -> dict[str, dict[str, dict]]:
    """{modo: {origen|'todos': resumen}}"""
    import indexar

    salida: dict[str, dict[str, dict]] = {}
    for modo in modos:
        filas = []
        for caso in casos:
            encontrados = indexar.buscar(conexion, caso["consulta"], n=5, modo=modo)
            ids = [h.id for h in encontrados]
            filas.append({"origen": caso["origen"], "recall5": recall_en_k(ids, caso["esperados"]),
                          "mrr": rr(ids, caso["esperados"]), "tokens": tokens_de(encontrados)})
        grupos = {"todos": filas}
        for origen in sorted({f["origen"] for f in filas}):
            grupos[origen] = [f for f in filas if f["origen"] == origen]
        salida[modo] = {g: resumir(v) for g, v in grupos.items()}
    return salida


def informe(resultados: dict[str, dict[str, dict]], modelo: str) -> str:
    modos = list(resultados)
    base = resultados.get("hibrida") or resultados[modos[0]]
    lineas = [f"# Evaluación de la búsqueda — {date.today().isoformat()}", "",
              f"Modelo de embeddings: `{modelo}`. Regla: se adopta lo que sube recall@5 sin subir tokens más de 10 %.", ""]
    for grupo in resultados[modos[0]]:
        lineas += [f"## {grupo} ({resultados[modos[0]][grupo]['casos']} casos)", "",
                   "| modo | recall@5 | MRR | tokens | veredicto vs híbrida |", "|---|---|---|---|---|"]
        for modo in modos:
            r = resultados[modo][grupo]
            veredicto = "—" if modo == "hibrida" else decidir(base[grupo], r)
            lineas.append(f"| {modo} | {r['recall5']:.2f} | {r['mrr']:.2f} | {r['tokens']:.0f} | {veredicto} |")
        lineas.append("")
    return "\n".join(lineas)


def main() -> None:
    import indexar
    import vectores

    ap = argparse.ArgumentParser(description="Evalúa la búsqueda de la mente.")
    ap.add_argument("--modos", default="texto,vector,hibrida,rerank")
    ap.add_argument("--generar", type=int, default=0, help="crear preguntas sintéticas para hasta N notas públicas")
    ap.add_argument("--sin-escribir", action="store_true")
    args = ap.parse_args()
    conexion = indexar.conectar()
    try:
        if args.generar:
            print(f"preguntas sintéticas para {generar_sinteticas(conexion, args.generar)} notas")
        casos = casos_semilla() + casos_reales() + casos_sinteticos()
        if not casos:
            print("sin casos: corre con --generar 40 o usa la mente unos días")
            return
        resultados = correr(conexion, casos, [m.strip() for m in args.modos.split(",") if m.strip()])
        texto = informe(resultados, vectores.firma_modelo())
        print(texto)
        if not args.sin_escribir:
            _dir_eval().mkdir(parents=True, exist_ok=True)
            (vida.MENTE / "evaluacion.md").write_text(texto + "\n", encoding="utf-8")
    finally:
        conexion.close()


if __name__ == "__main__":
    main()

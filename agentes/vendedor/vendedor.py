"""El Vendedor de INV3RZA: piso Ventas (4-nov).

Cada mañana junta la situación real de dinero (entregas de remi.db, negocio/frentes.md, negocio/suite.md y el
CRM si existe), decide UNA acción que acerque a JC a los US$5.000 al mes y la publica como su paso en la Suite.
Redacta los mensajes que hagan falta como borradores en mente/negocio/borradores/. Nunca envía nada a nadie.
Con la suscripción de Claude (`claude -p`, nunca API pagada); si la IA falla, decide por reglas y lo avisa.

    python3 vendedor.py            # la corrida del día
    python3 vendedor.py --probar   # no escribe nada: imprime lo que haría
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parents[1] / "nucleo"
MENTE = Path(os.environ.get("REMI_MENTE") or Path.home() / "proyectos" / "mente")
DB = Path(os.environ.get("REMI_DB_PATH") or NUCLEO / "remi.db")
if str(NUCLEO) not in sys.path:
    sys.path.append(str(NUCLEO))

MODELO = os.environ.get("VENDEDOR_MODELO", "sonnet")
TOPE_SEG = 600
DIAS_CERCA = 14          # una entrega con saldo a 14 días o menos (o vencida) → preparar el cobro
MAX_BORRADORES = 3
_RUTAS_CLAUDE = ("~/.local/bin/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude", "~/.claude/local/claude", "~/.npm-global/bin/claude")
_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_FRENTES_NO_VENTA = ("llc", "legal", "salud", "cuerpo", "remi", "trámite", "tramite")
_CIFRA = re.compile(r"\$\s?(\d[\d.,]*)")


# — Estado en la Suite —

def _suite():
    import agentes_estado
    return agentes_estado


def _reportar(estado: str, ahora: str = "", ultimo: str | None = None) -> None:
    try:
        _suite().avisar("vendedor", estado, ahora, ultimo)
    except Exception:  # noqa: BLE001 — el estado es un extra
        pass


# — La situación real —

def _leer(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8")
    except OSError:
        return ""


def entregas_de_remi(ruta: Path | None = None) -> list[dict]:
    """Las entregas que Remi lleva, en solo lectura. Sin base o sin tabla: lista vacía."""
    ruta = ruta or DB
    if not ruta.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        try:
            filas = con.execute("SELECT cliente, fecha, monto, estado FROM entregas ORDER BY fecha").fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return []
    return [{"cliente": c, "fecha": str(f)[:10], "monto": m, "estado": e} for c, f, m, e in filas]


def ventas_de_la_ficha(texto_suite: str) -> dict:
    """El piso Ventas de suite.md (paso y listas), si yaml está a mano. Si no, {}."""
    if not texto_suite.startswith("---"):
        return {}
    try:
        import yaml
        datos = yaml.safe_load(texto_suite.split("---", 2)[1]) or {}
        return (datos.get("pisos") or {}).get("ventas") or {}
    except Exception:  # noqa: BLE001
        return {}


def juntar(hoy: date, mente: Path | None = None, db: Path | None = None) -> dict:
    mente = mente or MENTE
    suite_md = _leer(mente / "negocio" / "suite.md")
    situacion = {
        "hoy": hoy.isoformat(),
        "entregas": entregas_de_remi(db),
        "frentes": _leer(mente / "negocio" / "frentes.md"),
        "ventas_en_la_suite": ventas_de_la_ficha(suite_md),
        "crm": _leer(mente / "negocio" / "crm.md"),
        "metas": _leer(mente / "yo" / "metas.md"),
    }
    situacion["faltan"] = [k for k in ("entregas", "frentes", "crm", "metas") if not situacion[k]]
    if not suite_md:
        situacion["faltan"].append("suite")
    return situacion


# — Lectura por reglas (sin IA) —

def _num(texto: str) -> int:
    return int(re.sub(r"[.,]", "", texto))


def _usd(n: float | int) -> str:
    return "US$" + f"{int(n):,}".replace(",", ".")


def _fecha_corta(texto: str, hoy: date) -> date | None:
    m = re.search(r"\b(\d{1,2})-(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\b", texto, re.IGNORECASE)
    if not m:
        return None
    try:
        return date(hoy.year, _MESES[m.group(2).lower()], int(m.group(1)))
    except ValueError:
        return None


def saldos_en_frentes(frentes: str, hoy: date) -> list[dict]:
    """«…entrega hacia el 9-nov y ahí cobra el resto (US$2.000)» → un saldo con cliente, proyecto y fecha.
    Solo lo que el texto dice; sin fecha o sin monto no hay saldo."""
    salida, titulo = [], ""
    for linea in frentes.splitlines():
        if linea.startswith("## "):
            titulo = linea[3:].split(":")[0].strip()
            continue
        m = re.search(r"(?:cobra|cobrar|saldo|resto)[^$\n]*?\$\s?(\d[\d.,]*)", linea, re.IGNORECASE)
        if not (m and titulo):
            continue
        cliente = re.search(r"\(([^)]+)\)", titulo)
        fase = re.search(r"\b(Fase \d+)", linea)
        total = _CIFRA.search(linea)
        salida.append({"cliente": cliente.group(1).strip() if cliente else titulo.split("(")[0].strip(),
                       "proyecto": titulo.split("(")[0].strip(), "fase": fase.group(1) if fase else "",
                       "saldo": _num(m.group(1)), "total": _num(total.group(1)) if total and total.start() < m.start() else None,
                       "fecha": _fecha_corta(linea, hoy)})
    return salida


def seguimientos_del_crm(crm: str) -> list[dict]:
    """«- Fiverr: eltondz … → paso: Revisar si respondió · nota» → conversación abierta con su paso."""
    salida, frente = [], ""
    for linea in crm.splitlines():
        if linea.startswith("## "):
            frente = linea[3:].strip().lower()
            continue
        if any(f in frente for f in _FRENTES_NO_VENTA) or not (linea.startswith("- ") and "→ paso:" in linea):
            continue
        que, resto = linea[2:].split("→ paso:", 1)
        quien = re.split(r"[;(]", que)[0].strip()
        if len(quien) > 60:
            quien = quien[:60].rsplit(" ", 1)[0] + "…"
        salida.append({"cliente": quien, "paso": resto.split(" · ")[0].strip()[:120], "fecha": ""})
    return salida


def borrador_de_cobro(cliente: str, saldo: float, proyecto: str = "", fase: str = "", total: float | None = None) -> str:
    trabajo = f"la {fase} de {proyecto}" if fase and proyecto else (f"el trabajo de {proyecto}" if proyecto else "el trabajo")
    cierre = f"para cerrar la {fase}" if fase else "para cerrar esta etapa"
    de_total = f" (de los {_usd(total)} acordados)" if total else ""
    return (f"Hola {cliente},\n\n"
            f"Gracias por la confianza. Te cuento que {trabajo} quedó lista y probada. Te la comparto para que la "
            f"revises con calma y me digas si todo está como lo hablamos.\n\n"
            f"Cuando le des el visto bueno, queda el saldo de {_usd(saldo)}{de_total} {cierre}. "
            f"¿Te paso los datos para hacerlo?\n\n"
            f"Juan Camilo")


def por_reglas(situacion: dict, hoy: date) -> dict:
    """La versión automática: cobrar lo ya ganado primero; si no, la conversación abierta más vieja."""
    frentes = saldos_en_frentes(situacion.get("frentes", ""), hoy)
    pendientes = []
    for e in situacion.get("entregas") or []:
        if e.get("estado") != "pagada" and e.get("monto"):
            extra = next((f for f in frentes if f["cliente"].lower() == str(e["cliente"]).lower()), {})
            try:
                fecha = date.fromisoformat(e["fecha"])
            except (TypeError, ValueError):
                fecha = None
            pendientes.append({**extra, "cliente": e["cliente"], "saldo": e["monto"], "fecha": fecha,
                               "total": extra.get("total") if extra.get("saldo") == e["monto"] else None})
    if not pendientes:
        pendientes = frentes
    seguimiento = [{"cliente": f"{p['cliente']}{', ' + p['fase'] if p.get('fase') else ''}",
                    "paso": f"Cobrar el saldo de {_usd(p['saldo'])} al entregar", "fecha": p["fecha"].isoformat() if p.get("fecha") else ""}
                   for p in pendientes] + seguimientos_del_crm(situacion.get("crm", ""))
    cerca = sorted((p for p in pendientes if p.get("fecha") and p["fecha"] - hoy <= timedelta(days=DIAS_CERCA)), key=lambda p: p["fecha"])
    if cerca:
        p = cerca[0]
        dias = (p["fecha"] - hoy).days
        cuando = "hoy" if dias == 0 else (f"hace {-dias} días" if dias < 0 else f"en {dias} días, el {p['fecha'].day}-{p['fecha'].month:02d}")
        return {"paso": {"titulo": f"Dejar listo el cobro de {_usd(p['saldo'])} a {p['cliente']}.",
                         "contexto": f"Se cobra al entregar{' la ' + p['fase'] if p.get('fase') else ''} ({cuando}). El mensaje ya está en borradores: revísalo y mándalo tú al entregar.",
                         "accion": "Revisar el mensaje"},
                "seguimiento": seguimiento,
                "borradores": [{"cliente": p["cliente"], "para": f"Cobrar el saldo al entregar{' la ' + p['fase'] if p.get('fase') else ''}",
                                "texto": borrador_de_cobro(p["cliente"], p["saldo"], p.get("proyecto", ""), p.get("fase", ""), p.get("total"))}],
                "ultimo": f"Dejó listo el cobro a {p['cliente']}"}
    crm = seguimientos_del_crm(situacion.get("crm", ""))
    if crm:
        return {"paso": {"titulo": crm[0]["paso"][:90], "contexto": f"Conversación abierta en el CRM: {crm[0]['cliente']}.", "accion": "Hacerlo ahora"},
                "seguimiento": seguimiento, "borradores": [], "ultimo": f"Marcó el seguimiento de {crm[0]['cliente'][:40]}"}
    return {"paso": {"titulo": "Contarle a Remi tu próxima entrega.", "contexto": "No encontré entregas con saldo ni conversaciones abiertas en tus datos.",
                     "accion": "Hablar con Remi"}, "seguimiento": seguimiento, "borradores": [], "ultimo": "Sin cobros ni seguimientos a la vista"}


# — Con Claude —

def binario_claude() -> str | None:
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
        consumo.registrar("vendedor", modelo, segundos, salida, returncode, error)
    except Exception:  # noqa: BLE001
        pass


def llamar_claude(sistema: str, mensaje: str, correr=None, binario: str | None = None) -> str | None:
    binario = binario or binario_claude()
    if not binario:
        raise RuntimeError("no encuentro la CLI de Claude (claude)")
    entorno = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")}
    comando = [binario, "-p", "--model", MODELO, "--output-format", "json", "--system-prompt", sistema, "--tools", "",
               "--setting-sources", "", "--no-session-persistence", "--strict-mcp-config", "--max-turns", "3"]
    inicio = time.perf_counter()
    try:
        r = (correr or subprocess.run)(comando, input=mensaje, capture_output=True, text=True, timeout=TOPE_SEG, env=entorno, cwd=str(AQUI))
    except subprocess.TimeoutExpired:
        _registrar_consumo(correr, MODELO, time.perf_counter() - inicio, error="timeout")
        raise
    except OSError as exc:
        _registrar_consumo(correr, MODELO, 0, error=f"{type(exc).__name__}: {exc}")
        raise
    _registrar_consumo(correr, MODELO, time.perf_counter() - inicio, getattr(r, "stdout", None), getattr(r, "returncode", 0))
    datos = json.loads(r.stdout or "{}")
    if datos.get("is_error"):
        raise RuntimeError(f"la CLI avisó un error: {str(datos.get('result'))[:200]}")
    return datos.get("result")


def _json(texto: str) -> dict:
    texto = (texto or "").strip()
    m = re.search(r"\{.*\}", texto, re.DOTALL)
    if not m:
        raise ValueError("la respuesta no trae JSON")
    return json.loads(m.group(0))


def cifras_conocidas(situacion: dict) -> set[int]:
    fuente = json.dumps(situacion, ensure_ascii=False, default=str)
    conocidas = {_num(c) for c in _CIFRA.findall(fuente) if re.search(r"\d", c)}
    conocidas |= {int(e["monto"]) for e in situacion.get("entregas") or [] if e.get("monto")}
    return conocidas


def leer_respuesta(texto: str, situacion: dict) -> dict:
    """El JSON del Vendedor, validado. Si trae una cifra que no está en los datos, se descarta entero."""
    datos = _json(texto)
    paso = datos.get("paso") or {}
    if not isinstance(paso, dict) or not str(paso.get("titulo", "")).strip():
        raise ValueError("la respuesta no trae paso")
    paso = {k: str(paso.get(k) or "").strip() for k in ("titulo", "contexto", "accion")}
    seguimiento = [{k: str(s.get(k) or "").strip() for k in ("cliente", "paso", "fecha")}
                   for s in datos.get("seguimiento") or [] if isinstance(s, dict) and str(s.get("cliente", "")).strip()][:8]
    borradores = [{k: str(b.get(k) or "").strip() for k in ("cliente", "para", "texto")}
                  for b in datos.get("borradores") or [] if isinstance(b, dict) and str(b.get("cliente", "")).strip() and str(b.get("texto", "")).strip()][:MAX_BORRADORES]
    conocidas = cifras_conocidas(situacion)
    escrito = json.dumps([paso, seguimiento, borradores], ensure_ascii=False)
    inventadas = {_num(c) for c in _CIFRA.findall(escrito) if re.search(r"\d", c)} - conocidas
    if inventadas:
        raise ValueError(f"cifras que no están en los datos: {sorted(inventadas)}")
    ultimo = str(datos.get("ultimo") or "").strip()[:120] or f"Publicó: {paso['titulo'][:80]}"
    return {"paso": paso, "seguimiento": seguimiento, "borradores": borradores, "ultimo": ultimo}


# — Lo que deja —

def _slug(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plano).strip("-")[:40] or "cliente"


def ruta_borrador(hoy: date, cliente: str, mente: Path | None = None) -> Path:
    return (mente or MENTE) / "negocio" / "borradores" / f"{hoy.isoformat()}-{_slug(cliente)}.md"


def guardar_borrador(hoy: date, b: dict, origen: str, mente: Path | None = None) -> Path:
    """Escribe el borrador; si ya existe el de hoy (JC pudo editarlo), lo deja como está."""
    ruta = ruta_borrador(hoy, b["cliente"], mente)
    if ruta.exists():
        return ruta
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = (f"---\ntipo: borrador\ncliente: {b['cliente']}\npara: {b['para']}\nfecha: {hoy.isoformat()}\n"
             f"estado: sin enviar\nautor: vendedor ({origen})\n---\n"
             f"# Para {b['cliente']}: {b['para']}\n\nRevísalo y mándalo tú. El Vendedor nunca envía nada.\n\n{b['texto'].strip()}\n")
    tmp = ruta.with_suffix(".md.tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, ruta)
    return ruta


def listas(decision: dict) -> list[dict]:
    return [
        {"titulo": "Seguimiento", "fuente": "del Vendedor",
         "filas": [[s["cliente"], s["paso"] + (f" · {s['fecha']}" if s.get("fecha") else "")] for s in decision["seguimiento"]],
         "vacio": "Nada abierto. Un prospecto cuenta cuando paga."},
        {"titulo": "Borradores listos", "fuente": "del Vendedor",
         "filas": [[b["cliente"], b["para"]] for b in decision["borradores"]],
         "vacio": "Ningún mensaje por mandar hoy."},
    ]


def resumen(decision: dict, origen: str, hoy: date, mente: Path | None = None) -> str:
    lineas = [f"Vendedor · {hoy.isoformat()} · {origen}", f"Paso: {decision['paso']['titulo']}", f"  {decision['paso']['contexto']}"]
    for s in decision["seguimiento"]:
        lineas.append(f"Seguimiento: {s['cliente']} → {s['paso']}{' · ' + s['fecha'] if s.get('fecha') else ''}")
    for b in decision["borradores"]:
        lineas += [f"Borrador → {ruta_borrador(hoy, b['cliente'], mente)} ({b['para']})", b["texto"], ""]
    return "\n".join(lineas)


# — La corrida —

def correr(hoy: date | None = None, probar: bool = False, claude=None, avisar=None, publicar=None, mente: Path | None = None, db: Path | None = None) -> str:
    hoy = hoy or date.today()
    if not probar:
        _reportar("trabajando", "Revisando entregas, cobros y conversaciones")
    try:
        return _correr(hoy, probar, claude, avisar, publicar, mente, db)
    except Exception as exc:
        if not probar:
            _reportar("error", f"Se cayó: {type(exc).__name__}")
        raise


def _correr(hoy, probar, claude, avisar, publicar, mente, db) -> str:
    situacion = juntar(hoy, mente, db)
    automatica = por_reglas(situacion, hoy)
    origen = "IA"
    try:
        sistema = (AQUI / "instrucciones.md").read_text(encoding="utf-8")
        mensaje = ("Situación de hoy (JSON):\n" + json.dumps(situacion, ensure_ascii=False, default=str)
                   + "\n\nPropuesta automática (por reglas):\n" + json.dumps(automatica, ensure_ascii=False))
        decision = leer_respuesta((claude or llamar_claude)(sistema, mensaje), situacion)
    except Exception as exc:  # noqa: BLE001 — sin IA sale la versión por reglas
        decision, origen = automatica, "reglas"
        if not probar:
            try:
                import alertas
                aviso = avisar or alertas.enviar
            except Exception:  # noqa: BLE001
                aviso = None
            if aviso:
                aviso(f"El Vendedor no pudo decidir con la IA hoy ({type(exc).__name__}: {str(exc)[:150]}). Salió la versión por reglas.")
    if probar:
        return resumen(decision, origen + " · prueba, no escribió nada", hoy, mente)
    for b in decision["borradores"]:
        guardar_borrador(hoy, b, origen, mente)
    (publicar or _suite().publicar_piso)("ventas", "vendedor", paso=decision["paso"], entra=listas(decision))
    _reportar("durmiendo", "Vuelve mañana por la mañana", ultimo=decision["ultimo"])
    return resumen(decision, origen, hoy, mente)


if __name__ == "__main__":
    print(correr(probar="--probar" in sys.argv))

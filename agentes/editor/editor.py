"""El Editor de INV3RZA: el primer agente del equipo (3-nov).

Cada mañana (la agenda lo llama a las 11:00) usa la bóveda como herramienta: le pide la diaria del día y los
temas con fondo; con la suscripción de Claude (`claude -p`, nunca API pagada) decide qué le importa a JC, lo
verifica y lo escribe estilo Jarvis (instrucciones.md). Después publica cada tema en Notion y manda UN mensaje
por Telegram. Si el Editor no puede (sin CLI, límite, respuesta rota), sale la versión automática de la
bóveda y el bot de alertas lo cuenta: JC nunca se queda sin su mensaje.

    python3 editor.py            # la corrida del día
    python3 editor.py --probar   # escribe sin publicar ni enviar: imprime el mensaje
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BOVEDA = Path(os.environ.get("BOVEDA_RAIZ") or Path.home() / "proyectos" / "boveda")
MENTE = Path(os.environ.get("REMI_MENTE") or Path.home() / "proyectos" / "mente")
sys.path.insert(0, str(BOVEDA))

MODELO = os.environ.get("EDITOR_MODELO", "sonnet")
TOPE_SEG = 1500
CANDIDATOS = 10
ACCIONES = {"hoy", "tener en cuenta", "solo saber"}
_RUTAS_CLAUDE = ("~/.local/bin/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude", "~/.claude/local/claude", "~/.npm-global/bin/claude")


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


def _sin_frontmatter(texto: str) -> str:
    return texto.split("---", 2)[2].strip() if texto.startswith("---") and texto.count("---") >= 2 else texto.strip()


def ficha_de_jc(mente: Path = MENTE) -> str:
    partes = []
    for rel in ("yo/metas.md", "negocio/frentes.md", "yo/valores-y-reglas.md"):
        try:
            partes.append(_sin_frontmatter((mente / rel).read_text(encoding="utf-8"))[:2500])
        except OSError:
            pass
    return "\n\n".join(partes)


def para_el_editor(candidatos: list[dict]) -> list[dict]:
    """Lo que el Editor necesita de cada tema (sin ruido interno)."""
    return [{"id": c["id"], "resumen_corto": c["linea"], "lo_esencial": c["esencial"], "datos": c["datos"][:6],
             "implicacion_automatica": c["para_ti"], "fuente": c["fuente"], "confianza": c["confianza"],
             "formato": c["formato"], "enlace": c["enlace"]} for c in candidatos]


def llamar_claude(sistema: str, mensaje: str, correr=None, binario: str | None = None) -> str | None:
    binario = binario or binario_claude()
    if not binario:
        raise RuntimeError("no encuentro la CLI de Claude (claude)")
    entorno = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")}
    comando = [binario, "-p", "--model", MODELO, "--output-format", "json", "--system-prompt", sistema,
               "--tools", "WebFetch,WebSearch", "--allowedTools", "WebFetch,WebSearch",
               "--setting-sources", "", "--no-session-persistence", "--strict-mcp-config", "--max-turns", "30"]
    r = (correr or subprocess.run)(comando, input=mensaje, capture_output=True, text=True, timeout=TOPE_SEG, env=entorno, cwd=str(AQUI))
    datos = json.loads(r.stdout or "{}")
    if datos.get("is_error"):
        raise RuntimeError(f"la CLI avisó un error: {str(datos.get('result'))[:200]}")
    return datos.get("result")


def leer_respuesta(texto: str, candidatos: list[dict]) -> list[dict]:
    """El JSON del Editor, validado: ids reales, campos completos, máximo 8."""
    import motores
    datos = motores.parsear_json(texto or "")
    por_id = {c["id"]: c for c in candidatos}
    salida = []
    for t in datos.get("temas") or []:
        if not isinstance(t, dict) or t.get("id") not in por_id or not str(t.get("titular", "")).strip():
            continue
        c = dict(por_id[t["id"]])
        accion = str(t.get("accion") or "solo saber").strip().lower()
        c.update({"tema": str(t["titular"]).strip().rstrip(".")[:200], "linea": str(t["titular"]).strip(),
                  "esencial": [str(t.get("cuerpo") or "").strip()] if str(t.get("cuerpo") or "").strip() else c["esencial"],
                  "datos": [], "para_ti": str(t.get("para_ti") or "").strip(),
                  "accion": accion if accion in ACCIONES else "solo saber", "nota": str(t.get("nota") or "").strip(),
                  "editor": True})
        salida.append(c)
        if len(salida) >= 8:
            break
    return salida


def correr(hoy: date | None = None, probar: bool = False, claude=None, publicar=None, enviar=None, avisar=None, preparar=True, con=None) -> str:
    import newsletter
    import newsletter_notion as nn
    from boveda import candado
    hoy = hoy or date.today()
    if preparar:
        with candado():                 # la agenda pone BOVEDA_ESPERAR_CANDADO: espera su turno
            newsletter.diaria(enviar_telegram=False)
    con = con or newsletter.abrir_bd()
    candidatos = nn.del_dia(con, hoy, n=CANDIDATOS)
    escritos: list[dict] | None = None
    if candidatos:
        try:
            sistema = (AQUI / "instrucciones.md").read_text(encoding="utf-8")
            mensaje = ("Temas de hoy (JSON):\n" + json.dumps(para_el_editor(candidatos), ensure_ascii=False)
                       + "\n\nFicha de JC:\n" + ficha_de_jc())
            escritos = leer_respuesta((claude or llamar_claude)(sistema, mensaje), candidatos)
            if not probar:
                (MENTE / "mundo" / "newsletter").mkdir(parents=True, exist_ok=True)
                (MENTE / "mundo" / "newsletter" / f"_editor-{hoy.isoformat()}.json").write_text(
                    json.dumps(escritos, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 — sin Editor sale la versión automática
            escritos = None
            if not probar:
                import alertas
                (avisar or alertas.enviar)(f"El Editor no pudo escribir la newsletter hoy ({type(exc).__name__}: {str(exc)[:150]}). Salió la versión automática.")
    temas = escritos if escritos is not None else nn.elegir(candidatos)
    if probar:
        return nn.mensaje(temas, hoy, con_notion=False)
    publicadas = (publicar or nn.publicar)(con, temas, hoy)
    texto = newsletter.mensaje_unico(nn.mensaje(temas, hoy, con_notion=bool(publicadas) or bool(nn.token())), hoy)
    if not (enviar or newsletter.enviar)(texto):
        print("no pude mandar el mensaje por Telegram (¿núcleo apagado?)", file=sys.stderr)
    return texto


if __name__ == "__main__":
    print(correr(probar="--probar" in sys.argv, preparar="--sin-preparar" not in sys.argv))

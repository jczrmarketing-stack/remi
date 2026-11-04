"""Los agentes de la línea (Bloque 1): Planificador, Tester, Constructor y Revisor.

Una sola función, `llamar`, corre `claude -p` con la sesión de Max:
- `--json-schema`: cada salida trae campos fijos (`estado`, `motivo` y los del rol).
- `--settings fabrica/portero/settings.json`: el Portero niega push, borrados,
  despliegues y escrituras fuera del worktree (probado con la CLI real el 4-nov).
- `--output-format stream-json --verbose`: cada evento (texto, herramienta,
  resultado) va a `fabrica/pedidos/<id>/eventos.jsonl` para verlo en el panel.
Prefijo fijo primero (instrucciones del rol + CLAUDE.md del worktree) y el
pedido al final por stdin, para aprovechar la caché.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import agentes_estado
import coding
import consumo
import pensar
from fabrica import expediente

Rol = Literal["planificador", "tester", "constructor", "revisor"]
ROLES: tuple[Rol, ...] = ("planificador", "tester", "constructor", "revisor")
ESTADOS = ("hecho", "no_puedo", "necesito_dato")

REPO = expediente.REPO
CONFIG = REPO / "config" / "fabrica.json"
INSTRUCCIONES = REPO / "fabrica" / "agentes"
SETTINGS = REPO / "fabrica" / "portero" / "settings.json"
PORTERO = REPO / "fabrica" / "portero" / "portero.py"
FABRICA_PY = os.environ.get("FABRICA_PY") or "/Users/juancamilo/proyectos/remi/nucleo/.venv/bin/python"

LECTURA = ("Read", "Grep", "Glob")
RECORTE = 600
# En la Suite, la fábrica vive en el piso Ingeniería: Programador y Revisor.
EN_LA_SUITE: dict[Rol, str] = {"planificador": "programador", "tester": "programador",
                               "constructor": "programador", "revisor": "revisor"}

Ejecutar = Callable[[list[str], str, Path, dict[str, str]], Iterator[str]]
"""(comando, stdin, cwd, entorno) → líneas de stdout. Se inyecta en pruebas."""


@dataclass
class Salida:
    estado: str
    motivo: str
    datos: dict[str, Any] = field(default_factory=dict)
    tokens: int = 0


def _lista(maximo: int | None = None) -> dict[str, Any]:
    esquema: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
    if maximo is not None:
        esquema["maxItems"] = maximo
    return esquema


def _esquema(propias: dict[str, Any]) -> dict[str, Any]:
    propiedades = {"estado": {"type": "string", "enum": list(ESTADOS)}, "motivo": {"type": "string"}, **propias}
    return {"type": "object", "properties": propiedades, "required": list(propiedades), "additionalProperties": False}


ESQUEMAS: dict[Rol, dict[str, Any]] = {
    "planificador": _esquema({
        "spec": {"type": "string"},
        "escenarios": _lista(),
        "preguntas": _lista(3),
        "toca": _lista(),
        "riesgo": {"type": "string", "enum": list(expediente.RIESGOS)},
    }),
    "tester": _esquema({"tests": _lista(), "resumen": {"type": "string"}}),
    "constructor": _esquema({"resumen": {"type": "string"}, "archivos": _lista()}),
    "revisor": _esquema({"hallazgos": {"type": "array", "items": {
        "type": "object",
        "properties": {"nivel": {"type": "string", "enum": ["alto", "medio", "bajo"]}, "archivo": {"type": "string"},
                       "linea": {"type": "integer"}, "texto": {"type": "string"}},
        "required": ["nivel", "archivo", "linea", "texto"], "additionalProperties": False}}}),
}


def config() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(CONFIG.read_text(encoding="utf-8"))
    return datos


def _herramientas(rol: Rol) -> str:
    if rol in ("tester", "constructor"):
        return ",".join((*LECTURA, "Edit", "Write", f"Bash({FABRICA_PY} -m pytest:*)"))
    return ",".join(LECTURA)


def _sistema(rol: Rol, cwd: Path) -> str:
    partes = [(INSTRUCCIONES / "comun.md").read_text(encoding="utf-8").replace("{FABRICA_PY}", FABRICA_PY),
              (INSTRUCCIONES / f"{rol}.md").read_text(encoding="utf-8")]
    reglas = cwd / "CLAUDE.md"
    if reglas.is_file():
        partes.append("# CLAUDE.md del repo\n\n" + reglas.read_text(encoding="utf-8"))
    return "\n\n".join(partes)


def comando(rol: Rol, modelo: str, cwd: Path) -> list[str]:
    herramientas = _herramientas(rol)
    return [
        pensar.BINARIO, "-p",
        "--model", modelo,
        "--output-format", "stream-json", "--verbose",
        "--json-schema", json.dumps(ESQUEMAS[rol], ensure_ascii=False),
        "--settings", str(SETTINGS),
        "--system-prompt", _sistema(rol, cwd),
        "--tools", ",".join(h.split("(")[0] for h in dict.fromkeys(herramientas.split(","))),
        "--allowedTools", herramientas,
        "--strict-mcp-config",
        "--setting-sources", "",
        "--no-session-persistence",
        "--max-turns", str(config()["turnos"]),
    ]


def _ejecutar_cli(comando_: list[str], stdin: str, cwd: Path, entorno: dict[str, str]) -> Iterator[str]:
    proceso = subprocess.Popen(comando_, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, cwd=cwd, env=entorno)
    reloj = threading.Timer(float(config()["segundos_por_agente"]), proceso.kill)
    reloj.start()
    try:
        assert proceso.stdin and proceso.stdout
        proceso.stdin.write(stdin)
        proceso.stdin.close()
        for linea in proceso.stdout:
            yield linea.rstrip("\n")
    finally:
        reloj.cancel()
        proceso.wait()


def _resumen_entrada(entrada: Any) -> str:
    if not isinstance(entrada, dict):
        return str(entrada)[:RECORTE]
    for clave in ("file_path", "command", "pattern", "path", "notebook_path"):
        if entrada.get(clave):
            return str(entrada[clave])[:RECORTE]
    return json.dumps(entrada, ensure_ascii=False)[:RECORTE]


def _texto_resultado(contenido: Any) -> str:
    if isinstance(contenido, list):
        contenido = " ".join(str(c.get("text", "")) if isinstance(c, dict) else str(c) for c in contenido)
    return str(contenido)[:RECORTE]


def eventos_de(linea: str, rol: str) -> list[dict[str, Any]]:
    """Lo que el panel muestra de una línea de stream-json. Sin `n` ni `en`."""
    try:
        evento = json.loads(linea)
    except json.JSONDecodeError:
        return []
    if not isinstance(evento, dict):
        return []
    tipo = evento.get("type")
    salida: list[dict[str, Any]] = []
    if tipo == "assistant":
        for parte in (evento.get("message") or {}).get("content") or []:
            if parte.get("type") == "text" and str(parte.get("text", "")).strip():
                salida.append({"rol": rol, "tipo": "texto", "texto": parte["text"]})
            elif parte.get("type") == "thinking" and str(parte.get("thinking", "")).strip():
                salida.append({"rol": rol, "tipo": "pensamiento", "texto": parte["thinking"]})
            elif parte.get("type") == "tool_use" and parte.get("name") != "StructuredOutput":
                salida.append({"rol": rol, "tipo": "herramienta", "herramienta": parte.get("name", ""),
                               "texto": _resumen_entrada(parte.get("input"))})
    elif tipo == "user":
        contenido = (evento.get("message") or {}).get("content")
        for parte in contenido if isinstance(contenido, list) else []:
            if isinstance(parte, dict) and parte.get("type") == "tool_result":
                texto = _texto_resultado(parte.get("content"))
                if texto != "Structured output provided successfully":
                    salida.append({"rol": rol, "tipo": "resultado", "texto": texto})
    elif tipo == "result":
        estructura = evento.get("structured_output") or {}
        motivo = estructura.get("motivo") if isinstance(estructura, dict) else None
        salida.append({"rol": rol, "tipo": "fin", "texto": str(motivo or evento.get("result") or "")[:RECORTE]})
    return salida


def _contar(ruta: Path) -> int:
    try:
        with ruta.open(encoding="utf-8") as archivo:
            return sum(1 for _ in archivo)
    except OSError:
        return 0


def anotar_evento(pedido: str, evento: dict[str, Any]) -> None:
    """Agrega un evento a `eventos.jsonl` con su número y su hora."""
    ruta = expediente.carpeta(pedido) / "eventos.jsonl"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fila = {"n": _contar(ruta), **evento, "en": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")


def _salida_de(final: dict[str, Any] | None) -> Salida:
    if final is None:
        return Salida("no_puedo", "La CLI no devolvió resultado.")
    estructura = final.get("structured_output")
    if not isinstance(estructura, dict):
        try:
            estructura = json.loads(final.get("result") or "")
        except (TypeError, json.JSONDecodeError):
            estructura = None
    if not isinstance(estructura, dict) or estructura.get("estado") not in ESTADOS:
        return Salida("no_puedo", "La CLI devolvió una salida fuera del esquema.")
    return Salida(str(estructura["estado"]), str(estructura.get("motivo", "")), estructura)


def llamar(rol: Rol, mensaje: str, cwd: Path, pedido: str, modelo: str | None = None,
           ejecutar: Ejecutar | None = None) -> Salida:
    """Corre un agente sobre el worktree `cwd`. Nunca levanta salvo `LimiteDeMax`."""
    modelo = modelo or config()["modelos"][rol]
    entorno = pensar._entorno(pensar.MODOS["inteligente"] if modelo == "opus" else None)
    entorno.update(FABRICA_WORKTREE=str(cwd), FABRICA_PORTERO=str(PORTERO), FABRICA_PY=FABRICA_PY)
    suite = EN_LA_SUITE[rol]
    agentes_estado.avisar(suite, "trabajando", ahora=f"{rol.capitalize()}: empezando")
    final: dict[str, Any] | None = None
    error: str | None = None
    arranque = time.perf_counter()
    try:
        for linea in (ejecutar or _ejecutar_cli)(comando(rol, modelo, cwd), mensaje, cwd, entorno):
            for evento in eventos_de(linea, rol):
                anotar_evento(pedido, evento)
                if evento["tipo"] == "herramienta":
                    agentes_estado.avisar(suite, "trabajando",
                                          ahora=f"{rol.capitalize()}: {evento['herramienta']} {evento['texto'][:60]}")
            try:
                datos = json.loads(linea)
            except json.JSONDecodeError:
                if pensar.PATRON_LIMITE_ALCANZADO.search(linea):
                    raise coding.LimiteDeMax(rol)
                continue
            if isinstance(datos, dict) and datos.get("type") == "result":
                final = datos
                if datos.get("is_error") and pensar.PATRON_LIMITE_ALCANZADO.search(str(datos.get("result", ""))):
                    raise coding.LimiteDeMax(rol)
    except coding.LimiteDeMax:
        consumo.registrar(f"fabrica-{rol}", modelo, time.perf_counter() - arranque, error="límite de Max", pedido=pedido)
        agentes_estado.avisar(suite, "esperando", ahora="Max llegó a su límite")
        raise
    except Exception as exc:  # noqa: BLE001 — un agente caído es un no_puedo, no un traceback
        error = f"{type(exc).__name__}: {exc}"
    consumo.registrar(f"fabrica-{rol}", modelo, time.perf_counter() - arranque, final, 0, error, pedido=pedido)
    salida = Salida("no_puedo", f"El agente se cayó: {error}") if error else _salida_de(final)
    entrada, salida_tokens = consumo._tokens(final) if final else (0, 0)
    salida.tokens = entrada + salida_tokens
    agentes_estado.avisar(suite, "esperando", ahora="", ultimo=f"{rol.capitalize()}: {salida.motivo[:80]}")
    return salida

"""La línea de la fábrica (Bloque 1): código determinista que mueve un pedido.

pedir:   expediente + worktree → Planificador → spec → aviso. Pausa.
aprobar: Tester (sus tests deben fallar) → Constructor → verificador (1 vuelve,
         2 para) → Revisor una pasada (solo `alto` vuelve) → máx. 2 vueltas →
         commit con autor de la fábrica → push → PR en borrador → aviso.
Antes de cada agente se mira el tope de tokens del pedido. `no_puedo` y
`necesito_dato` detienen y mandan el motivo. Un pedido a la vez (candado).
Todo lo de afuera vive en `Mundo`, para probar sin CLI ni red.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import consumo
from fabrica import agentes, expediente
from fabrica.agentes import Rol, Salida

AUTOR = ["-c", "user.name=Fábrica INV3RZA", "-c", "user.email=fabrica@inv3rza.local"]
PIE_PR = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


class Ocupada(Exception):
    """Ya hay un pedido corriendo: la v1 lleva uno a la vez."""


class Parada(Exception):
    """La línea se detiene aquí; el motivo va al aviso y a los eventos."""


def _sin_lecciones(tarea: str) -> str:
    return ""


@dataclass
class Mundo:
    llamar: Callable[..., Salida]
    verificar: Callable[[Path, str], tuple[int, str]]
    sh: Callable[[list[str], Path], tuple[int, str]]
    avisar: Callable[[str], Any]
    raiz_repo: Path
    lecciones: Callable[[str], str] = field(default=_sin_lecciones)
    tokens: Callable[[str], int] = field(default=consumo.tokens_del_pedido)


def _sh_real(args: list[str], cwd: Path) -> tuple[int, str]:
    hecho = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=1800)
    return hecho.returncode, (hecho.stdout + hecho.stderr).strip()


def _verificar_real(cwd: Path, base: str) -> tuple[int, str]:
    entorno = {**os.environ, "VERIFICAR_BASE": base, "VERIFICAR_PYTHON": agentes.FABRICA_PY}
    hecho = subprocess.run(["scripts/verificar.sh", "--todo"], cwd=cwd, capture_output=True, text=True,
                           timeout=1800, env=entorno)
    informe = cwd / ".verificar" / "ultimo.md"
    texto = informe.read_text(encoding="utf-8") if informe.is_file() else (hecho.stdout + hecho.stderr)[-4000:]
    return hecho.returncode, texto


def _lecciones_reales(tarea: str) -> str:
    try:
        import coding

        return coding.bloque_de_experiencia(coding.lecciones_para(tarea))
    except Exception:  # noqa: BLE001 — sin bóveda, la línea sigue
        return ""


def _avisar_real(texto: str) -> None:
    import alertas

    alertas.enviar(f"Fábrica · {texto}")


def mundo_real() -> Mundo:
    return Mundo(llamar=agentes.llamar, verificar=_verificar_real, sh=_sh_real, avisar=_avisar_real,
                 raiz_repo=expediente.REPO, lecciones=_lecciones_reales)


# — Candado: un pedido a la vez —

def _ruta_candado() -> Path:
    return expediente._raiz(None) / ".candado"


def _vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def candado() -> Iterator[None]:
    ruta = _ruta_candado()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        dueno = int(ruta.read_text().strip() or 0)
    except (OSError, ValueError):
        dueno = 0
    if dueno and not _vivo(dueno):
        ruta.unlink(missing_ok=True)  # el proceso que lo tenía murió sin soltarlo
    try:
        fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise Ocupada("Ya hay un pedido corriendo.") from None
    with os.fdopen(fd, "w") as archivo:
        archivo.write(str(os.getpid()))
    try:
        yield
    finally:
        ruta.unlink(missing_ok=True)


# — Piezas —

def worktree(raiz_repo: Path, id_: str) -> Path:
    return raiz_repo / ".worktrees" / f"pedido-{id_}"


def _agente(mundo: Mundo, id_: str, rol: Rol, mensaje: str, cwd: Path, modelo: str | None = None) -> Salida:
    tope = int(agentes.config()["tope_tokens_pedido"])
    gastado = mundo.tokens(id_)
    if gastado >= tope:
        raise Parada(f"El pedido llegó a su tope de tokens ({gastado:,} de {tope:,}). Lo dejo aquí.".replace(",", "."))
    salida = mundo.llamar(rol, mensaje, cwd, id_, modelo)
    if salida.estado != "hecho":
        preguntas = salida.datos.get("preguntas") or []
        detalle = "\n".join(f"- {p}" for p in preguntas)
        raise Parada(f"{rol.capitalize()} ({salida.estado}): {salida.motivo}" + (f"\n{detalle}" if detalle else ""))
    return salida


def _mensaje(idea: str, lecciones: str, *partes: tuple[str, str]) -> str:
    bloques = [f"## Pedido\n\n{idea}"]
    if lecciones:
        bloques.append(f"## Bóveda\n\n{lecciones}")
    bloques += [f"## {titulo}\n\n{cuerpo}" for titulo, cuerpo in partes if cuerpo]
    return "\n\n".join(bloques)


def _texto_spec(datos: dict[str, Any]) -> str:
    partes = [str(datos.get("spec", "")).strip()]
    if datos.get("escenarios"):
        partes.append("Escenarios:\n" + "\n".join(f"- {e}" for e in datos["escenarios"]))
    if datos.get("preguntas"):
        partes.append("Preguntas:\n" + "\n".join(f"- {p}" for p in datos["preguntas"]))
    return "\n\n".join(p for p in partes if p)


def _texto_hallazgos(hallazgos: list[dict[str, Any]]) -> str:
    if not hallazgos:
        return "Sin hallazgos."
    return "\n".join(f"- [{h.get('nivel')}] {h.get('archivo')}:{h.get('linea')} — {h.get('texto')}" for h in hallazgos)


def _detener(mundo: Mundo, id_: str, motivo: str) -> None:
    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "parada", "texto": motivo})
    mundo.avisar(f"Pedido {id_} en pausa.\n{motivo}")


# — La línea —

def pedir(idea: str, base: str = "main", mundo: Mundo | None = None, repo: str = "remi") -> str:
    mundo = mundo or mundo_real()
    with candado():
        id_ = expediente.crear(idea, repo, base)
        try:
            meta = expediente.leer(id_)["meta"]
            wt = worktree(mundo.raiz_repo, id_)
            rc, salida = mundo.sh(["git", "worktree", "add", str(wt), "-b", meta["rama"], base], mundo.raiz_repo)
            if rc != 0:
                raise Parada(f"No pude crear el worktree: {salida[-300:]}")
            agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "spec"})
            plan = _agente(mundo, id_, "planificador", _mensaje(idea, mundo.lecciones(idea)), wt)
            expediente.escribir_seccion(id_, "Spec", _texto_spec(plan.datos))
            expediente.cambiar(id_, toca=list(plan.datos.get("toca") or []),
                               riesgo=plan.datos.get("riesgo") or "bajo", estado="spec")
            mundo.avisar(f"Spec lista para «{idea}»:\n\n{_texto_spec(plan.datos)}\n\n"
                         f"Si te sirve: python3 -m fabrica aprobar {id_}")
        except Parada as parada:
            _detener(mundo, id_, str(parada))
    return id_


APROBABLES = ("spec", "aprobado", "construyendo", "revisando")


def aprobar(id_: str, mundo: Mundo | None = None) -> str:
    """Corre del Tester al PR. Devuelve el estado donde quedó el pedido."""
    mundo = mundo or mundo_real()
    meta = expediente.leer(id_)["meta"]
    if meta["estado"] not in APROBABLES:
        raise ValueError(f"El pedido {id_} está en «{meta['estado']}»: no hay nada que aprobar.")
    with candado():
        try:
            _construir(mundo, id_)
        except Parada as parada:
            _detener(mundo, id_, str(parada))
    return str(expediente.leer(id_)["meta"]["estado"])


def _construir(mundo: Mundo, id_: str) -> None:
    datos = expediente.leer(id_)
    meta, secciones = datos["meta"], datos["secciones"]
    idea, spec, base, rama = secciones["Contexto"], secciones["Spec"], str(meta["base"]), str(meta["rama"])
    wt = worktree(mundo.raiz_repo, id_)
    lecciones = mundo.lecciones(idea)
    tope_vueltas = int(agentes.config()["vueltas"])
    if meta["estado"] == "spec":
        expediente.cambiar_estado(id_, "aprobado")
        expediente.escribir_seccion(id_, "Decisión", f"Spec aprobada el {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.")

    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "tests"})
    pruebas = _agente(mundo, id_, "tester", _mensaje(idea, lecciones, ("Spec", spec)), wt)
    tests = [str(t) for t in pruebas.datos.get("tests") or []]
    if not tests:
        raise Parada("Tester (necesito_dato): no dejó tests que correr.")
    rc, salida = mundo.sh([agentes.FABRICA_PY, "-m", "pytest", *tests, "-q"], wt)
    expediente.escribir_seccion(id_, "Tests", f"{pruebas.datos.get('resumen', '')}\n\nArchivos: {', '.join(tests)}\n\n"
                                              f"Antes de construir:\n```\n{salida[-1500:]}\n```")
    if rc == 0:
        raise Parada("Tester (necesito_dato): los tests ya pasan antes de construir; no prueban el cambio.")

    modelo = agentes.config()["modelos"]["constructor_alto"] if meta.get("riesgo") == "alto" else None
    vueltas = int(meta.get("vueltas") or 0)
    nota = ("", "")
    hallazgos: list[dict[str, Any]] = []
    while True:
        expediente.cambiar_estado(id_, "construyendo")
        agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "construir", "vuelta": vueltas})
        obra = _agente(mundo, id_, "constructor",
                       _mensaje(idea, lecciones, ("Spec", spec), ("Tests", ", ".join(tests)), nota), wt, modelo)
        expediente.escribir_seccion(id_, "Construcción", f"{obra.datos.get('resumen', '')}\n\n"
                                                         f"Archivos: {', '.join(obra.datos.get('archivos') or [])}")
        agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "verificar"})
        rc, informe = mundo.verificar(wt, base)
        expediente.escribir_seccion(id_, "Escáneres", f"Verificador: salida {rc}\n\n{informe[-3000:]}")
        if rc == 2:
            raise Parada("El verificador no pudo correr completo: falta herramienta. Mira .verificar/ultimo.md.")
        if rc != 0:
            if vueltas >= tope_vueltas:
                raise Parada(f"Después de {vueltas} vueltas el verificador sigue sin pasar.")
            vueltas += 1
            expediente.cambiar(id_, vueltas=vueltas)
            nota = ("Informe del verificador (arréglalo primero)", informe[-4000:])
            continue
        expediente.cambiar_estado(id_, "revisando")
        mundo.sh(["git", "add", "-A"], wt)
        _, diff = mundo.sh(["git", "diff", "--cached", base], wt)
        revision = _agente(mundo, id_, "revisor", _mensaje(idea, "", ("Spec", spec), ("Diff", f"```diff\n{diff}\n```")), wt)
        hallazgos = list(revision.datos.get("hallazgos") or [])
        expediente.escribir_seccion(id_, "Revisión", _texto_hallazgos(hallazgos))
        altos = [h for h in hallazgos if h.get("nivel") == "alto"]
        if not altos:
            break
        if vueltas >= tope_vueltas:
            raise Parada(f"Después de {vueltas} vueltas el Revisor sigue con hallazgos altos:\n{_texto_hallazgos(altos)}")
        vueltas += 1
        expediente.cambiar(id_, vueltas=vueltas)
        nota = ("Hallazgos altos del Revisor (arréglalos primero)", _texto_hallazgos(altos))

    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "pr"})
    mundo.sh(["git", "add", "-A"], wt)
    rc, salida = mundo.sh(["git", *AUTOR, "commit", "-m", f"Fábrica: {idea.splitlines()[0][:60]}\n\nPedido {id_}."], wt)
    if rc != 0:
        raise Parada(f"No pude hacer el commit: {salida[-300:]}")
    rc, salida = mundo.sh(["git", "push", "-u", "origin", rama], wt)
    if rc != 0:
        raise Parada(f"El push no salió (el gancho pre-push corre el verificador): {salida[-500:]}")
    cuerpo = (f"## Pedido\n\n{idea}\n\n## Spec\n\n{spec}\n\n## Tests\n\n{', '.join(tests)}\n\n"
              f"## Revisión\n\n{_texto_hallazgos(hallazgos)}\n\n"
              f"Vueltas: {vueltas} · Tokens: {mundo.tokens(id_):,}".replace(",", ".") + f"\n\n{PIE_PR}")
    rc, salida = mundo.sh(["gh", "pr", "create", "--draft", "--base", base, "--head", rama,
                           "--title", f"Fábrica: {idea.splitlines()[0][:60]}", "--body", cuerpo], wt)
    if rc != 0:
        raise Parada(f"No pude abrir el PR: {salida[-300:]}")
    url = salida.strip().splitlines()[-1] if salida.strip() else ""
    expediente.cambiar_estado(id_, "pr")
    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "fin", "texto": url})
    mundo.avisar(f"PR en borrador para «{idea.splitlines()[0][:60]}»: {url}\nNada se fusiona sin ti.")

"""La línea de la fábrica (Bloque 1): código determinista que mueve un pedido.

pedir:     expediente + worktree → Planificador → spec → aviso. Pausa.
responder: si el Planificador preguntó, la respuesta entra al Contexto y se replanea.
aprobar:   Tester (sus tests deben FALLAR, rc 1) → Constructor → verificador y los
           tests del Tester (deben PASAR) → Revisor (solo `alto` vuelve) → máx. 2
           vueltas → commit con autor de la fábrica → push → PR en borrador → aviso.
           Un reintento retoma donde paró: sin repetir el Tester ni el commit.
Antes de cada agente se mira el tope de tokens del pedido. `no_puedo`,
`necesito_dato` y el límite de Max detienen y avisan. Un pedido a la vez.
Todo lo de afuera vive en `Mundo`, para probar sin CLI ni red.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import coding
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
    probar: Callable[[list[str], Path], tuple[int, str]]
    avisar: Callable[[str], Any]
    raiz_repo: Path
    lecciones: Callable[[str], str] = field(default=_sin_lecciones)
    tokens: Callable[[str], int] = field(default=consumo.tokens_del_pedido)


def _sh_real(args: list[str], cwd: Path, entorno: dict[str, str] | None = None) -> tuple[int, str]:
    hecho = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=1800, env=entorno)
    return hecho.returncode, (hecho.stdout + hecho.stderr).strip()


def _probar_real(tests: list[str], cwd: Path) -> tuple[int, str]:
    """Los tests del Tester son código escrito por un agente: corren sin credenciales."""
    return _sh_real([agentes.FABRICA_PY, "-m", "pytest", *tests, "-q"], cwd, agentes.entorno_encerrado(dict(os.environ)))


# Un worktree de pedido no trae node_modules: panel y ventanita solo se revisan
# si el cambio los toca (y entonces el verificador avisa que falta `npm install`).
SIN_APPS = ("secretos", "tests_nucleo", "tipos_nucleo", "tests_agentes", "codigo_peligroso", "dependencias")


def revisiones_para(archivos: list[str]) -> list[str]:
    if any(a.startswith("apps/") for a in archivos):
        return ["--todo"]
    return ["--solo", *SIN_APPS]


def _verificar_real(cwd: Path, base: str) -> tuple[int, str]:
    entorno = {**agentes.entorno_encerrado(dict(os.environ)), "VERIFICAR_BASE": base, "VERIFICAR_PYTHON": agentes.FABRICA_PY}
    _sh_real(["git", "add", "-A"], cwd)
    _, cambiados = _sh_real(["git", "diff", "--cached", "--name-only", base], cwd)
    hecho = subprocess.run(["scripts/verificar.sh", *revisiones_para(cambiados.splitlines())], cwd=cwd,
                           capture_output=True, text=True, timeout=1800, env=entorno)
    informe = cwd / ".verificar" / "ultimo.md"
    texto = informe.read_text(encoding="utf-8") if informe.is_file() else (hecho.stdout + hecho.stderr)[-4000:]
    return hecho.returncode, texto


def _lecciones_reales(tarea: str) -> str:
    try:
        return coding.bloque_de_experiencia(coding.lecciones_para(tarea))
    except Exception:  # noqa: BLE001 — sin bóveda, la línea sigue
        return ""


def _avisar_real(texto: str) -> None:
    """Al bot de alertas. Corriendo desde un worktree, el `nucleo/.env` con el chat de
    Juan Camilo está en el checkout principal: se toma de ahí si no hay otro."""
    import alertas

    if not os.environ.get("ALERTAS_CHAT_ID"):
        chat = alertas._env(_repo_principal() / "nucleo" / ".env").get("TELEGRAM_CHAT_ID", "")
        if chat:
            os.environ["ALERTAS_CHAT_ID"] = chat
    alertas.enviar(f"Fábrica · {texto}")


def _repo_principal() -> Path:
    """El checkout principal (padre de `.git`), para que los worktrees de los
    pedidos no queden anidados dentro del worktree desde donde corre la fábrica."""
    rc, salida = _sh_real(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], expediente.REPO)
    return Path(salida).parent if rc == 0 and salida else expediente.REPO


def mundo_real() -> Mundo:
    return Mundo(llamar=agentes.llamar, verificar=_verificar_real, sh=_sh_real, probar=_probar_real,
                 avisar=_avisar_real, raiz_repo=_repo_principal(), lecciones=_lecciones_reales)


def orden_pedir(idea: str) -> str:
    texto = idea.replace('"', "'")
    return f'cd {expediente.REPO / "nucleo"} && {agentes.FABRICA_PY} -m fabrica pedir "{texto}"'


def orden(sub: str, id_: str) -> str:
    """Cómo se corre la fábrica desde la terminal, con las rutas de verdad."""
    return f"cd {expediente.REPO / 'nucleo'} && {agentes.FABRICA_PY} -m fabrica {sub} {id_}"


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
    if salida.estado == "partir":
        partes = [str(p) for p in salida.datos.get("partes") or [] if str(p).strip()]
        detalle = "\n".join(f"- {p}\n  {orden_pedir(p)}" for p in partes)
        raise Parada(f"{rol.capitalize()} (partir): {salida.motivo}\nUn pedido por parte:\n{detalle}")
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
    if str(datos.get("como_se_demuestra") or "").strip():
        partes.append(f"Cómo se demuestra:\n{str(datos['como_se_demuestra']).strip()}")
    if datos.get("preguntas"):
        partes.append("Preguntas:\n" + "\n".join(f"- {p}" for p in datos["preguntas"]))
    return "\n\n".join(p for p in partes if p)


def _texto_hallazgos(hallazgos: list[dict[str, Any]]) -> str:
    if not hallazgos:
        return "Sin hallazgos."
    return "\n".join(f"- [{h.get('nivel')}] {h.get('archivo')}:{h.get('linea')} — {h.get('texto')}" for h in hallazgos)


def _miles(n: int) -> str:
    """3.000.000, como se escribe en español; solo el número (antes se cambiaban todas las comas del PR)."""
    return f"{n:,}".replace(",", ".")


GRAVEDAD = {"alto": 0, "medio": 1, "bajo": 2}


def _contrastar(hallazgos: list[dict[str, Any]], wt: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mejora 5 (6-nov): un hallazgo cuenta solo si cita un archivo que existe y una línea que está en él.
    Los que quedan se ordenan por gravedad; los otros se listan aparte, nunca vuelven al Constructor."""
    validos: list[dict[str, Any]] = []
    descartados: list[dict[str, Any]] = []
    for h in hallazgos:
        ruta = wt / str(h.get("archivo") or "")
        try:
            total = len(ruta.read_text(encoding="utf-8", errors="replace").splitlines()) if ruta.is_file() else -1
        except OSError:
            total = -1
        linea_ = int(h.get("linea") or 0)
        (validos if total >= 0 and 0 <= linea_ <= max(total, 1) else descartados).append(h)
    return sorted(validos, key=lambda h: GRAVEDAD.get(str(h.get("nivel")), 3)), descartados


def _texto_revision(validos: list[dict[str, Any]], descartados: list[dict[str, Any]]) -> str:
    texto = _texto_hallazgos(validos)
    if descartados:
        texto += "\n\nDescartados (citan código que no existe):\n" + "\n".join(
            f"- [{h.get('nivel')}] {h.get('archivo')}:{h.get('linea')} — {h.get('texto')}" for h in descartados)
    return texto


def modelo_revisor(alto: bool) -> str:
    modelos = agentes.config()["modelos"]
    if not alto:
        return str(modelos["revisor"])
    revisor, constructor = str(modelos.get("revisor_alto") or modelos["revisor"]), str(modelos["constructor_alto"])
    return revisor if revisor != constructor else ("sonnet" if constructor == "opus" else "opus")


def _controles(mundo: Mundo, id_: str, base: str, wt: Path, tests: list[str], ocultos: list[str], alto: bool) -> str:
    """Mejora 1 (6-nov): cada control con su resultado; el que no corrió se dice."""
    _, cambiados = mundo.sh(["git", "diff", "--name-only", base, "HEAD"], wt)
    revisiones = revisiones_para(cambiados.splitlines())
    modo = revisiones[0] + (" " + ", ".join(revisiones[1:]) if len(revisiones) > 1 else "")
    revision = expediente.leer(id_)["secciones"]["Revisión"].split("\n\nDescartados")[0]
    cuenta = {n: revision.count(f"- [{n}]") for n in GRAVEDAD}
    descartados = expediente.leer(id_)["secciones"]["Revisión"].count("\n- [") - sum(cuenta.values())
    oculto_txt = (f"{len(ocultos)}, pasan ({', '.join(ocultos)})" if ocultos else "ninguno (este control no corrió)")
    lineas = [f"- Verificador ({modo}): salida 0, PASA",
              f"- Tests del Tester: {', '.join(tests)}, pasan",
              f"- Escenarios ocultos: {oculto_txt}",
              f"- Revisor ({modelo_revisor(alto)}): {sum(cuenta.values())} hallazgos "
              f"({cuenta['alto']} altos, {cuenta['medio']} medios, {cuenta['bajo']} bajos)"
              + (f", {descartados} descartados por citar código que no existe" if descartados > 0 else "")]
    return "## Controles\n\n" + "\n".join(lineas)


def _tests_seguros(tests: list[str]) -> bool:
    """Solo rutas relativas dentro del worktree: nada de `..`, rutas absolutas ni banderas de pytest."""
    return bool(tests) and all(
        t and not t.startswith("-") and not PurePosixPath(t).is_absolute() and ".." not in PurePosixPath(t).parts
        for t in tests)


def _detener(mundo: Mundo, id_: str, motivo: str) -> None:
    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "parada", "texto": motivo})
    mundo.avisar(f"Pedido {id_} en pausa.\n{motivo}")


@contextmanager
def _paradas(mundo: Mundo, id_: str, como_seguir: str) -> Iterator[None]:
    try:
        yield
    except Parada as parada:
        _detener(mundo, id_, f"{parada}\n\nPara seguir: {como_seguir}")
    except coding.LimiteDeMax:
        _detener(mundo, id_, f"Max llegó a su límite de uso. Cuando se renueve: {como_seguir}")


# — La línea —

def _planear(mundo: Mundo, id_: str) -> None:
    datos = expediente.leer(id_)
    meta, idea = datos["meta"], datos["secciones"]["Contexto"]
    wt = worktree(mundo.raiz_repo, id_)
    if not wt.exists():
        rc, salida = mundo.sh(["git", "worktree", "add", str(wt), "-b", meta["rama"], meta["base"]], mundo.raiz_repo)
        if rc != 0:
            raise Parada(f"No pude crear el worktree: {salida[-300:]}")
    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "spec"})
    plan = _agente(mundo, id_, "planificador", _mensaje(idea, mundo.lecciones(idea)), wt)
    expediente.escribir_seccion(id_, "Spec", _texto_spec(plan.datos))
    expediente.cambiar(id_, toca=list(plan.datos.get("toca") or []),
                       riesgo=plan.datos.get("riesgo") or "bajo", estado="spec")
    mundo.avisar(f"Spec lista para «{idea.splitlines()[0][:80]}»:\n\n{_texto_spec(plan.datos)}\n\n"
                 f"Si te sirve, ahora:\n{orden('aprobar', id_)}\n\nO para que la construya la noche:\n"
                 f"{orden('aprobar', id_)} --de-noche")


def pedir(idea: str, base: str = "main", mundo: Mundo | None = None, repo: str = "remi") -> str:
    mundo = mundo or mundo_real()
    with candado():
        id_ = expediente.crear(idea, repo, base)
        with _paradas(mundo, id_, f"{orden('responder', id_)} \"<tu respuesta>\""):
            _planear(mundo, id_)
    return id_


def responder(id_: str, respuesta: str, mundo: Mundo | None = None) -> str:
    """El Planificador preguntó (o se cortó): la respuesta entra al Contexto y se replanea."""
    mundo = mundo or mundo_real()
    expediente.leer(id_)  # KeyError si no existe
    with candado():
        datos = expediente.leer(id_)
        if datos["meta"]["estado"] not in ("idea", "spec"):
            raise ValueError(f"El pedido {id_} ya pasó la spec (está en «{datos['meta']['estado']}»).")
        if respuesta.strip():
            contexto = f"{datos['secciones']['Contexto']}\n\nRespuesta de Juan Camilo: {respuesta.strip()}"
            expediente.escribir_seccion(id_, "Contexto", contexto)
        with _paradas(mundo, id_, f"{orden('responder', id_)} \"<tu respuesta>\""):
            _planear(mundo, id_)
    return str(expediente.leer(id_)["meta"]["estado"])


APROBABLES = ("spec", "aprobado", "construyendo", "revisando")


# — La noche (mejora 4, 6-nov): un pedido por corrida, solo lo que Juan Camilo dejó para la noche —

def encolar(idea: str, base: str = "main", repo: str = "remi") -> str:
    """Deja el pedido en la cola sin gastar: la noche corre el Planificador."""
    id_ = expediente.crear(idea, repo, base)
    expediente.cambiar(id_, noche=1)
    return id_


def aprobar_de_noche(id_: str) -> str:
    """Aprueba la spec sin construir: la próxima noche lo lleva al PR."""
    estado = expediente.leer(id_)["meta"]["estado"]
    if estado != "spec":
        raise ValueError(f"El pedido {id_} está en «{estado}»: solo se deja para la noche una spec lista.")
    expediente.cambiar(id_, estado="aprobado", noche=1)
    expediente.escribir_seccion(id_, "Decisión", f"Spec aprobada el {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, "
                                                 "para construirla de noche.")
    return "aprobado"


def siguiente_de_noche() -> tuple[str, str]:
    """Primero lo aprobado (o lo que paró a medias); si no hay, planear lo encolado. Lo más viejo primero."""
    pedidos = sorted((m for m in expediente.listar() if int(m.get("noche") or 0)), key=lambda m: str(m.get("creado", "")))
    for meta in pedidos:
        if meta["estado"] in ("aprobado", "construyendo", "revisando"):
            return "aprobar", str(meta["pedido"])
    for meta in pedidos:
        if meta["estado"] == "idea":
            return "planear", str(meta["pedido"])
    return "nada", ""


def noche(mundo: Mundo | None = None) -> tuple[str, str]:
    accion, id_ = siguiente_de_noche()
    if accion == "nada":
        return accion, id_
    mundo = mundo or mundo_real()
    with candado():
        if accion == "aprobar":
            with _paradas(mundo, id_, orden("aprobar", id_)):
                _construir(mundo, id_)
        else:
            with _paradas(mundo, id_, f"{orden('responder', id_)} \"<tu respuesta>\""):
                _planear(mundo, id_)
    return accion, id_


def aprobar(id_: str, mundo: Mundo | None = None) -> str:
    """Corre del Tester al PR, o retoma donde paró. Devuelve el estado donde quedó el pedido."""
    mundo = mundo or mundo_real()
    expediente.leer(id_)  # KeyError si no existe
    with candado():
        estado = expediente.leer(id_)["meta"]["estado"]
        if estado not in APROBABLES:
            raise ValueError(f"El pedido {id_} está en «{estado}»: no hay nada que aprobar.")
        with _paradas(mundo, id_, orden("aprobar", id_)):
            _construir(mundo, id_)
    return str(expediente.leer(id_)["meta"]["estado"])


def _tests_del_expediente(texto: str, prefijo: str = "Archivos: ") -> list[str]:
    for linea in texto.splitlines():
        if linea.startswith(prefijo):
            return [t.strip() for t in linea[len(prefijo):].split(",") if t.strip() and t.strip() != "ninguno"]
    return []


def _probar_antes(mundo: Mundo, id_: str, idea: str, spec: str, lecciones: str, wt: Path) -> tuple[list[str], list[str]]:
    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "tests"})
    pruebas = _agente(mundo, id_, "tester", _mensaje(idea, lecciones, ("Spec", spec)), wt)
    tests = [str(t) for t in pruebas.datos.get("tests") or []]
    ocultos = [str(t) for t in pruebas.datos.get("ocultos") or []]
    if not _tests_seguros(tests):
        raise Parada(f"Tester (necesito_dato): los tests deben ser rutas dentro del worktree; dejó {tests or 'ninguno'}.")
    if ocultos and (not _tests_seguros(ocultos) or set(ocultos) & set(tests)):
        raise Parada(f"Tester (necesito_dato): los ocultos deben ser archivos propios dentro del worktree; dejó {ocultos}.")
    rc, salida = mundo.probar(tests, wt)
    rc_oc, salida_oc = mundo.probar(ocultos, wt) if ocultos else (1, "")
    expediente.escribir_seccion(id_, "Tests", f"{pruebas.datos.get('resumen', '')}\n\nArchivos: {', '.join(tests)}\n"
                                              f"Ocultos: {', '.join(ocultos) or 'ninguno'}\n\n"
                                              f"Antes de construir:\n```\n{salida[-1500:]}\n```")
    if rc == 0:
        raise Parada("Tester (necesito_dato): los tests ya pasan antes de construir; no prueban el cambio.")
    if rc != 1:
        raise Parada(f"Tester (no_puedo): los tests no se pudieron correr (pytest salió {rc}).\n{salida[-500:]}")
    if rc_oc == 0:
        raise Parada("Tester (necesito_dato): los escenarios ocultos ya pasan antes de construir; no prueban el cambio.")
    if rc_oc != 1:
        raise Parada(f"Tester (no_puedo): los ocultos no se pudieron correr (pytest salió {rc_oc}).\n{salida_oc[-500:]}")
    _esconder(id_, wt, ocultos)
    return tests, ocultos


# — Escenarios ocultos (mejora 2, 6-nov): el Constructor nunca los ve —
# Viven en la carpeta del pedido (fuera del worktree, y el Portero niega leer fuera).
# Entran al worktree solo mientras corren, y para siempre justo antes del commit.

def _guardados(id_: str) -> Path:
    return expediente.carpeta(id_) / "ocultos"


def _esconder(id_: str, wt: Path, ocultos: list[str]) -> None:
    for rel in ocultos:
        origen, destino = wt / rel, _guardados(id_) / rel
        if not origen.is_file():
            raise Parada(f"Tester (no_puedo): dijo que escribió el oculto {rel}, pero no está en el worktree.")
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origen), destino)


def _poner_ocultos(id_: str, wt: Path, ocultos: list[str]) -> None:
    for rel in ocultos:
        guardado = _guardados(id_) / rel
        if not guardado.is_file():
            raise Parada(f"No encuentro el escenario oculto {rel} en la carpeta del pedido.")
        (wt / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guardado, wt / rel)


def _quitar_ocultos(wt: Path, ocultos: list[str]) -> None:
    for rel in ocultos:
        (wt / rel).unlink(missing_ok=True)


FALLA_PYTEST = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)", re.M)


def _probar_ocultos(mundo: Mundo, id_: str, wt: Path, ocultos: list[str]) -> tuple[int, list[str]]:
    """Corre los ocultos y devuelve solo los nombres de los que fallan: ni su código ni su assert."""
    _poner_ocultos(id_, wt, ocultos)
    try:
        rc, salida = mundo.probar(ocultos, wt)
    finally:
        _quitar_ocultos(wt, ocultos)
    return rc, FALLA_PYTEST.findall(salida) or ([f"{len(ocultos)} archivo(s) oculto(s), salida {rc}"] if rc else [])


def _construir(mundo: Mundo, id_: str) -> None:
    datos = expediente.leer(id_)
    meta, secciones = datos["meta"], datos["secciones"]
    idea, spec, base, rama = secciones["Contexto"], secciones["Spec"], str(meta["base"]), str(meta["rama"])
    wt = worktree(mundo.raiz_repo, id_)
    lecciones = mundo.lecciones(idea)
    estado = meta["estado"]
    if estado == "spec":
        expediente.cambiar_estado(id_, "aprobado")
        expediente.escribir_seccion(id_, "Decisión", f"Spec aprobada el {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.")
        estado = "aprobado"

    if estado == "aprobado":
        tests, ocultos = _probar_antes(mundo, id_, idea, spec, lecciones, wt)
        nota = ("", "")
    else:
        # Reintento tras una parada: el código del Constructor ya está en el worktree,
        # así que no se repite el Tester (sus tests ya pasarían) y las vueltas cuentan de nuevo.
        tests = _tests_del_expediente(secciones["Tests"])
        ocultos = _tests_del_expediente(secciones["Tests"], "Ocultos: ")
        if not _tests_seguros(tests):
            raise Parada("No encuentro los tests del Tester en el expediente.")
        expediente.cambiar(id_, vueltas=0)
        anterior = secciones["Revisión"] if estado == "revisando" else secciones["Escáneres"]
        nota = ("Lo que quedó pendiente en el intento anterior", anterior[-4000:])

    _, ya_hecho = mundo.sh(["git", "log", "--oneline", f"{base}..HEAD"], wt)
    if estado == "revisando" and ya_hecho.strip():
        hallazgos_txt = secciones["Revisión"]  # paró en el push o el PR: el commit ya existe
    else:
        _vueltas(mundo, id_, idea, spec, base, lecciones, tests, wt, nota, meta.get("riesgo") == "alto", ocultos)
        hallazgos_txt = expediente.leer(id_)["secciones"]["Revisión"]
        _poner_ocultos(id_, wt, ocultos)   # pasaron: desde ahora son tests del repo y van en el PR
        _, ya_hecho = mundo.sh(["git", "log", "--oneline", f"{base}..HEAD"], wt)

    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "pr"})
    if not ya_hecho.strip():
        mundo.sh(["git", "add", "-A"], wt)
        rc, salida = mundo.sh(["git", *AUTOR, "commit", "-m", f"Fábrica: {idea.splitlines()[0][:60]}\n\nPedido {id_}."], wt)
        if rc != 0:
            raise Parada(f"No pude hacer el commit: {salida[-300:]}")
    rc, salida = mundo.sh(["git", "push", "-u", "origin", rama], wt)
    if rc != 0:
        raise Parada(f"El push no salió (el gancho pre-push corre el verificador): {salida[-500:]}")
    vueltas = expediente.leer(id_)["meta"].get("vueltas", 0)
    oculto_txt = (f"{len(ocultos)}, pasan ({', '.join(ocultos)})" if ocultos else "ninguno (este control no corrió)")
    controles = _controles(mundo, id_, base, wt, tests, ocultos, meta.get("riesgo") == "alto")
    cuerpo = (f"## Pedido\n\n{idea}\n\n## Spec\n\n{spec}\n\n## Tests\n\n{', '.join(tests)}\n\n"
              f"Escenarios ocultos: {oculto_txt}\n\n{controles}\n\n"
              f"## Revisión\n\n{hallazgos_txt}\n\n"
              f"Vueltas: {vueltas} · Tokens: {_miles(mundo.tokens(id_))}\n\n{PIE_PR}")
    rc, salida = mundo.sh(["gh", "pr", "create", "--draft", "--base", base, "--head", rama,
                           "--title", f"Fábrica: {idea.splitlines()[0][:60]}", "--body", cuerpo], wt)
    if rc != 0:
        raise Parada(f"No pude abrir el PR: {salida[-300:]}")
    url = salida.strip().splitlines()[-1] if salida.strip() else ""
    expediente.cambiar_estado(id_, "pr")
    agentes.anotar_evento(id_, {"rol": "linea", "tipo": "fin", "texto": url})
    mundo.avisar(f"PR en borrador para «{idea.splitlines()[0][:60]}»: {url}\nNada se fusiona sin ti.")


def _vueltas(mundo: Mundo, id_: str, idea: str, spec: str, base: str, lecciones: str, tests: list[str], wt: Path,
             nota: tuple[str, str], alto: bool, ocultos: list[str] | None = None) -> list[dict[str, Any]]:
    """Constructor → verificador + tests del Tester → Revisor, hasta que pase o se acaben las 2 vueltas."""
    modelo = agentes.config()["modelos"]["constructor_alto"] if alto else None
    tope = int(agentes.config()["vueltas"])
    vueltas = 0
    while True:
        expediente.cambiar_estado(id_, "construyendo")
        agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "construir", "vuelta": vueltas})
        obra = _agente(mundo, id_, "constructor",
                       _mensaje(idea, lecciones, ("Spec", spec), ("Tests", ", ".join(tests)), nota), wt, modelo)
        expediente.escribir_seccion(id_, "Construcción", f"{obra.datos.get('resumen', '')}\n\n"
                                                         f"Archivos: {', '.join(obra.datos.get('archivos') or [])}")
        agentes.anotar_evento(id_, {"rol": "linea", "tipo": "estacion", "texto": "verificar"})
        rc, informe = mundo.verificar(wt, base)
        rc_tests, salida_tests = mundo.probar(tests, wt)
        expediente.escribir_seccion(id_, "Escáneres", f"Verificador: salida {rc}\n\n{informe[-3000:]}\n\n"
                                                      f"Tests del Tester: salida {rc_tests}\n```\n{salida_tests[-1000:]}\n```")
        if rc == 2:
            raise Parada("El verificador no pudo correr completo: falta herramienta. Mira .verificar/ultimo.md.")
        if rc != 0 or rc_tests != 0:
            if vueltas >= tope:
                raise Parada(f"Después de {vueltas} vueltas el verificador o los tests del Tester siguen sin pasar.")
            vueltas += 1
            expediente.cambiar(id_, vueltas=vueltas)
            nota = ("Informe del verificador y de los tests (arréglalo primero)",
                    f"{informe[-3000:]}\n\nTests del Tester (salida {rc_tests}):\n{salida_tests[-1000:]}")
            continue
        if ocultos:
            rc_oc, fallan = _probar_ocultos(mundo, id_, wt, ocultos)
            escaneres = expediente.leer(id_)["secciones"]["Escáneres"]
            expediente.escribir_seccion(id_, "Escáneres", f"{escaneres}\n\nEscenarios ocultos: salida {rc_oc}"
                                                          + (f" · no se cumplen: {', '.join(fallan)}" if rc_oc else ""))
            if rc_oc != 0:
                if vueltas >= tope:
                    raise Parada(f"Después de {vueltas} vueltas hay escenarios ocultos que no se cumplen: {', '.join(fallan)}")
                vueltas += 1
                expediente.cambiar(id_, vueltas=vueltas)
                nota = ("Escenarios ocultos que no se cumplen (no los ves: vuelve a leer la spec y su «cómo se demuestra»)",
                        "\n".join(f"- {f}" for f in fallan))
                continue
        expediente.cambiar_estado(id_, "revisando")
        mundo.sh(["git", "add", "-A"], wt)
        rc_diff, diff = mundo.sh(["git", "diff", "--cached", base], wt)
        if rc_diff != 0:
            raise Parada(f"No pude sacar el diff para el Revisor: {diff[-300:]}")
        revision = _agente(mundo, id_, "revisor", _mensaje(idea, "", ("Spec", spec), ("Diff", f"```diff\n{diff}\n```")), wt,
                           modelo_revisor(alto))
        hallazgos, descartados = _contrastar(list(revision.datos.get("hallazgos") or []), wt)
        expediente.escribir_seccion(id_, "Revisión", _texto_revision(hallazgos, descartados))
        altos = [h for h in hallazgos if h.get("nivel") == "alto"]
        if not altos:
            return hallazgos
        if vueltas >= tope:
            raise Parada(f"Después de {vueltas} vueltas el Revisor sigue con hallazgos altos:\n{_texto_hallazgos(altos)}")
        vueltas += 1
        expediente.cambiar(id_, vueltas=vueltas)
        nota = ("Hallazgos altos del Revisor (arréglalos primero)", _texto_hallazgos(altos))

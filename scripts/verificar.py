#!/usr/bin/env python3
"""El verificador de INV3RZA (4-nov-2026): lo que no depende de la opinión de una IA.

Corre, de lo más barato a lo más caro, todo lo que puede decir «sí» o «no» sin opinar:
secretos, tests, tipos, código peligroso y dependencias con fallas conocidas. Se detiene en el
primer fallo (salvo con --todo). Solo bloquea lo NUEVO: lo que ya fallaba vive en la línea base
(scripts/verificar/linea-base/) y se ve como aviso, nunca como bloqueo.

    python3 scripts/verificar.py                       # verifica el cambio (se detiene en el primer fallo)
    python3 scripts/verificar.py --todo                # corre todo aunque algo falle
    python3 scripts/verificar.py --actualizar-linea-base   # guarda lo que falla hoy como línea base

Salida: 0 = pasa · 1 = no pasa · 2 = incompleto (falta una herramienta, nada falló).
Deja el resumen en .verificar/ultimo.md y .verificar/ultimo.json: la fábrica lo copia al expediente.

Variables:
  VERIFICAR_BASE      contra qué comparar (por defecto, el punto donde la rama sale de main)
  VERIFICAR_PYTHON    un python con las dependencias del núcleo (por defecto: uv run --project nucleo python)
  VERIFICAR_SEMGREP   configuraciones de Semgrep separadas por espacio (por defecto: p/python p/typescript p/secrets)
Herramientas: gitleaks, semgrep y osv-scanner (en macOS: brew install gitleaks semgrep osv-scanner).
Solo usa la librería estándar de Python.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LINEA_BASE = RAIZ / "scripts" / "verificar" / "linea-base"
SALIDA = RAIZ / ".verificar"
CODIGO = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs")


@dataclass
class Resultado:
    nombre: str
    estado: str  # pasa · no-pasa · falta · aviso
    detalle: str
    nuevos: list[str] = field(default_factory=list)
    conocidos: int = 0


# ---------- utilidades ----------

def correr(cmd: list[str], cwd: Path = RAIZ, tiempo: int = 900, env: dict | None = None) -> subprocess.CompletedProcess:
    entorno = {**os.environ, **(env or {})}
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=tiempo, env=entorno)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"se pasó de {tiempo} s")


def git(*args: str) -> str:
    r = correr(["git", *args])
    return r.stdout.strip() if r.returncode == 0 else ""


def base_de_comparacion() -> str:
    if os.environ.get("VERIFICAR_BASE"):
        return git("rev-parse", os.environ["VERIFICAR_BASE"]) or os.environ["VERIFICAR_BASE"]
    for rama in ("main", "origin/main"):
        mb = git("merge-base", "HEAD", rama)
        if mb:
            return mb
    return ""


def archivos_cambiados(base: str) -> list[str]:
    nombres = set()
    if base:
        nombres.update(git("diff", "--name-only", "--diff-filter=ACMR", base).splitlines())
    nombres.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(n for n in nombres if n and (RAIZ / n).is_file())


def leer_base(nombre: str) -> list[str]:
    p = LINEA_BASE / nombre
    if not p.exists():
        return []
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def escribir_base(nombre: str, lineas: list[str], nota: str) -> None:
    LINEA_BASE.mkdir(parents=True, exist_ok=True)
    cuerpo = f"# {nota}\n# Generado {datetime.now():%Y-%m-%d %H:%M}. Lo que está aquí no bloquea; lo nuevo sí.\n"
    (LINEA_BASE / nombre).write_text(cuerpo + "\n".join(sorted(lineas)) + "\n", encoding="utf-8")


def comparar(actuales: list[str], conocidos: list[str]) -> tuple[list[str], int]:
    """Lo nuevo es lo que aparece más veces que en la línea base (cuenta repetidos)."""
    a, c = Counter(actuales), Counter(conocidos)
    nuevos = sorted((a - c).elements())
    return nuevos, sum((a & c).values())


def python_del_nucleo() -> list[str] | None:
    if os.environ.get("VERIFICAR_PYTHON"):
        return [os.environ["VERIFICAR_PYTHON"]]
    if shutil.which("uv"):
        return ["uv", "run", "--quiet", "--project", str(RAIZ / "nucleo"), "python"]
    return None


def fallos_pytest(salida: str) -> list[str]:
    ids = []
    for linea in salida.splitlines():
        m = re.match(r"^(FAILED|ERROR) (\S+)", linea)
        if m:
            ids.append(m.group(2))
    return ids


# ---------- las revisiones ----------

def secretos(base: str, actualizar: bool) -> Resultado:
    if not shutil.which("gitleaks"):
        return Resultado("Secretos", "falta", "instala gitleaks")
    hallados: list[str] = []
    with tempfile.TemporaryDirectory() as t:
        pasos = [["gitleaks", "git", "--no-banner", "--redact", "-l", "error", "--pre-commit", "-f", "json", "-r", f"{t}/a.json", "."],
                 ["gitleaks", "git", "--no-banner", "--redact", "-l", "error", "--pre-commit", "--staged", "-f", "json", "-r", f"{t}/s.json", "."]]
        if base:
            pasos.append(["gitleaks", "git", "--no-banner", "--redact", "-l", "error", "--log-opts", f"{base}..HEAD", "-f", "json", "-r", f"{t}/b.json", "."])
        for i, cmd in enumerate(pasos):
            r = correr(cmd)
            if r.returncode not in (0, 1):
                return Resultado("Secretos", "no-pasa", f"gitleaks no pudo correr: {(r.stderr or r.stdout).strip()[:160]}")
            reporte = Path(cmd[cmd.index("-r") + 1])
            if reporte.exists() and reporte.stat().st_size:
                hallados += [f"{f['File']}:{f['StartLine']} ({f['RuleID']})" for f in json.loads(reporte.read_text() or "[]")]
        # Lo nuevo que aún no está en git no sale en ningún diff: se revisa archivo por archivo.
        for i, nuevo in enumerate(git("ls-files", "--others", "--exclude-standard").splitlines()):
            r = correr(["gitleaks", "dir", "--no-banner", "--redact", "-l", "error", "-f", "json", "-r", f"{t}/n{i}.json", nuevo])
            reporte = Path(f"{t}/n{i}.json")
            if r.returncode == 1 and reporte.exists():
                hallados += [f"{f['File']}:{f['StartLine']} ({f['RuleID']})" for f in json.loads(reporte.read_text() or "[]")]
    if hallados:
        return Resultado("Secretos", "no-pasa", f"{len(hallados)} posible{'s' if len(hallados) != 1 else ''} secreto{'s' if len(hallados) != 1 else ''} en el cambio", hallados)
    return Resultado("Secretos", "pasa", "0 encontrados")


def tests_nucleo(base: str, actualizar: bool) -> Resultado:
    py = python_del_nucleo()
    if not py:
        return Resultado("Núcleo · tests", "falta", "instala uv o define VERIFICAR_PYTHON")
    r = correr([*py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE"], cwd=RAIZ / "nucleo", tiempo=1200)
    if r.returncode not in (0, 1):
        return Resultado("Núcleo · tests", "no-pasa", f"pytest no terminó (código {r.returncode}): {(r.stderr or r.stdout).strip()[-200:]}")
    fallos = fallos_pytest(r.stdout)
    total = re.search(r"(\d+) passed", r.stdout)
    pasan = total.group(1) if total else "?"
    if actualizar:
        escribir_base("pytest-nucleo.txt", fallos, "Tests del núcleo que ya fallaban")
    nuevos, conocidos = comparar(fallos, leer_base("pytest-nucleo.txt"))
    if nuevos:
        return Resultado("Núcleo · tests", "no-pasa", f"{len(nuevos)} {'falla' if len(nuevos) == 1 else 'fallan'} de nuevo ({pasan} pasan)", nuevos, conocidos)
    extra = f", {conocidos} ya fallaban antes" if conocidos else ""
    return Resultado("Núcleo · tests", "pasa", f"{pasan} pasan{extra}", conocidos=conocidos)


def tipos_nucleo(base: str, actualizar: bool) -> Resultado:
    py = python_del_nucleo()
    if not py:
        return Resultado("Núcleo · tipos", "falta", "instala uv o define VERIFICAR_PYTHON")
    r = correr([*py, "-m", "mypy", "."], cwd=RAIZ / "nucleo", tiempo=900)
    errores = []
    for linea in r.stdout.splitlines():
        m = re.match(r"^(.+?):\d+(?::\d+)?: error: (.+)$", linea)
        if m:
            errores.append(f"{m.group(1)}: {m.group(2)}")
    if r.returncode not in (0, 1) or (r.returncode == 1 and not errores):
        return Resultado("Núcleo · tipos", "no-pasa", f"mypy no terminó: {(r.stderr or r.stdout).strip()[-200:]}")
    if actualizar:
        escribir_base("mypy.txt", errores, "Errores de mypy que ya existían (sin número de línea)")
    nuevos, conocidos = comparar(errores, leer_base("mypy.txt"))
    if nuevos:
        return Resultado("Núcleo · tipos", "no-pasa", f"{len(nuevos)} errores nuevos de tipos", nuevos, conocidos)
    extra = f" ({conocidos} ya existían)" if conocidos else ""
    return Resultado("Núcleo · tipos", "pasa", f"sin errores nuevos{extra}", conocidos=conocidos)


def tests_agentes(base: str, actualizar: bool) -> Resultado:
    py = python_del_nucleo()
    if not py:
        return Resultado("Agentes · tests", "falta", "instala uv o define VERIFICAR_PYTHON")
    fallos, pasan = [], 0
    for prueba in sorted((RAIZ / "agentes").glob("*/test_*.py")):
        r = correr([*py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE", prueba.name], cwd=prueba.parent, tiempo=600)
        if r.returncode not in (0, 1):
            return Resultado("Agentes · tests", "no-pasa", f"{prueba.parent.name}: pytest no terminó (código {r.returncode})")
        fallos += [f"{prueba.parent.name}/{f}" for f in fallos_pytest(r.stdout)]
        m = re.search(r"(\d+) passed", r.stdout)
        pasan += int(m.group(1)) if m else 0
    if actualizar:
        escribir_base("pytest-agentes.txt", fallos, "Tests de agentes que ya fallaban")
    nuevos, conocidos = comparar(fallos, leer_base("pytest-agentes.txt"))
    if nuevos:
        return Resultado("Agentes · tests", "no-pasa", f"{len(nuevos)} {'falla' if len(nuevos) == 1 else 'fallan'} de nuevo ({pasan} pasan)", nuevos, conocidos)
    extra = f", {conocidos} ya fallaban antes" if conocidos else ""
    return Resultado("Agentes · tests", "pasa", f"{pasan} pasan{extra}", conocidos=conocidos)


def _tsc(nombre: str, carpeta: str) -> Resultado:
    tsc = RAIZ / carpeta / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        return Resultado(nombre, "falta", f"corre npm install en {carpeta}")
    r = correr([str(tsc), "--noEmit"], cwd=RAIZ / carpeta, tiempo=600)
    errores = [l for l in r.stdout.splitlines() if ": error TS" in l]
    if r.returncode != 0:
        return Resultado(nombre, "no-pasa", f"{len(errores) or 'varios'} errores de tipos", errores[:20])
    return Resultado(nombre, "pasa", "sin errores")


def tipos_panel(base: str, actualizar: bool) -> Resultado:
    return _tsc("Panel · tipos", "apps/panel")


def tipos_ventanita(base: str, actualizar: bool) -> Resultado:
    return _tsc("Ventanita · tipos", "apps/ventanita")


def tests_ventanita(base: str, actualizar: bool) -> Resultado:
    vitest = RAIZ / "apps/ventanita/node_modules/.bin/vitest"
    if not vitest.exists():
        return Resultado("Ventanita · tests", "falta", "corre npm install en apps/ventanita")
    r = correr([str(vitest), "run"], cwd=RAIZ / "apps/ventanita", tiempo=600)
    texto = r.stdout + r.stderr
    m = re.search(r"Tests\s+(?:\d+ failed \| )?(\d+) passed", texto)
    if r.returncode != 0:
        return Resultado("Ventanita · tests", "no-pasa", "vitest falló", [l.strip() for l in texto.splitlines() if "FAIL" in l][:20])
    return Resultado("Ventanita · tests", "pasa", f"{m.group(1) if m else 'todos'} pasan")


def codigo_peligroso(base: str, actualizar: bool) -> Resultado:
    if not shutil.which("semgrep"):
        return Resultado("Código peligroso", "falta", "instala semgrep")
    objetivos = [f for f in archivos_cambiados(base) if f.endswith(CODIGO)
                 and "/pruebas/" not in f and not Path(f).name.startswith("test_") and ".test." not in f
                 and not f.startswith(("vendor/", "node_modules/"))]
    if not objetivos:
        return Resultado("Código peligroso", "pasa", "sin código nuevo que revisar")
    configs = os.environ.get("VERIFICAR_SEMGREP", "p/python p/typescript p/secrets").split()
    cmd = ["semgrep", "scan", "--metrics", "off", "--severity", "ERROR", "--json", "-q"]
    for c in configs:
        cmd += ["--config", c]
    if base:
        cmd += ["--baseline-commit", base]
    r = correr(cmd + objetivos, tiempo=900)
    try:
        datos = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return Resultado("Código peligroso", "no-pasa", f"semgrep no pudo correr: {r.stderr.strip()[-200:]}")
    bloquean, avisos = [], []
    for h in datos.get("results", []):
        linea = f"{h['path']}:{h['start']['line']} ({h['check_id'].split('.')[-1]})"
        (avisos if ".audit." in h["check_id"] or h["check_id"].endswith("-audit") else bloquean).append(linea)
    if bloquean:
        return Resultado("Código peligroso", "no-pasa", f"{len(bloquean)} hallazgos altos en {len(objetivos)} archivos", bloquean + avisos)
    if avisos:
        return Resultado("Código peligroso", "aviso", f"{len(avisos)} avisos de auditoría para mirar (no bloquean)", avisos)
    return Resultado("Código peligroso", "pasa", f"{len(objetivos)} archivos revisados, nada alto")


def dependencias(base: str, actualizar: bool) -> Resultado:
    if not shutil.which("osv-scanner"):
        return Resultado("Dependencias", "falta", "instala osv-scanner")
    r = correr(["osv-scanner", "scan", "source", "-r", "--format", "json", "--lockfile", "nucleo/uv.lock",
                "--lockfile", "apps/ventanita/package-lock.json"], tiempo=600)
    if r.returncode not in (0, 1):
        motivo = "sin red hacia osv.dev" if "Forbidden" in r.stderr or "dial" in r.stderr else (r.stderr.strip()[-160:] or f"código {r.returncode}")
        return Resultado("Dependencias", "falta", f"osv-scanner no pudo consultar: {motivo}")
    vulns = []
    for res in json.loads(r.stdout or "{}").get("results", []):
        for pq in res.get("packages", []):
            p = pq.get("package", {})
            for v in pq.get("vulnerabilities", []):
                vulns.append(f"{p.get('name')}@{p.get('version')} {v.get('id')}")
    if actualizar:
        escribir_base("osv.txt", vulns, "Dependencias con fallas conocidas que ya estaban")
    nuevos, conocidos = comparar(vulns, leer_base("osv.txt"))
    if nuevos:
        return Resultado("Dependencias", "no-pasa", f"{len(nuevos)} fallas nuevas en dependencias", nuevos, conocidos)
    extra = f" ({conocidos} ya estaban)" if conocidos else ""
    return Resultado("Dependencias", "pasa", f"sin fallas nuevas{extra}", conocidos=conocidos)


REVISIONES = [secretos, tests_nucleo, tipos_nucleo, tests_agentes, tipos_panel, tipos_ventanita,
              tests_ventanita, codigo_peligroso, dependencias]
ICONO = {"pasa": "✓", "no-pasa": "✗", "falta": "?", "aviso": "!"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Verificador de INV3RZA")
    ap.add_argument("--todo", action="store_true", help="no detenerse en el primer fallo")
    ap.add_argument("--actualizar-linea-base", action="store_true", help="guardar lo que falla hoy como línea base")
    ap.add_argument("--solo", nargs="*", help="correr solo estas revisiones (nombres de función)")
    args = ap.parse_args()

    base = base_de_comparacion()
    rama = git("branch", "--show-current") or git("rev-parse", "--short", "HEAD")
    print(f"VERIFICAR · {rama} · {datetime.now():%d-%m %H:%M}" + (f" · contra {base[:7]}" if base else " · sin base"))
    print()
    resultados: list[Resultado] = []
    revisiones = [r for r in REVISIONES if not args.solo or r.__name__ in args.solo]
    seguir = args.todo or args.actualizar_linea_base
    for revision in revisiones:
        res = revision(base, args.actualizar_linea_base)
        resultados.append(res)
        print(f"{ICONO[res.estado]} {res.nombre:<19}{res.detalle}")
        for n in res.nuevos[:8]:
            print(f"    {n}")
        if len(res.nuevos) > 8:
            print(f"    … y {len(res.nuevos) - 8} más")
        if res.estado == "no-pasa" and not seguir:
            if revision is not revisiones[-1]:
                print("· (se detuvo aquí)")
            break

    if any(r.estado == "no-pasa" for r in resultados):
        veredicto, codigo = "NO PASA", 1
    elif any(r.estado == "falta" for r in resultados):
        veredicto, codigo = "INCOMPLETO: falta una herramienta", 2
    else:
        veredicto, codigo = "PASA", 0
    print(f"\n{veredicto}")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "ultimo.json").write_text(json.dumps({"rama": rama, "base": base, "veredicto": veredicto,
        "fecha": datetime.now().isoformat(timespec="seconds"), "revisiones": [asdict(r) for r in resultados]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"## Escáneres ({datetime.now():%d-%m %H:%M}, contra {base[:7] or 'sin base'})", ""]
    md += [f"- {ICONO[r.estado]} **{r.nombre}**: {r.detalle}" + "".join(f"\n    - {n}" for n in r.nuevos[:8]) for r in resultados]
    md += ["", f"**{veredicto}**"]
    (SALIDA / "ultimo.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return codigo


if __name__ == "__main__":
    sys.exit(main())

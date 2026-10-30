#!/usr/bin/env python3
"""Mapa del repo y de la mente, para que Claude no explore con grep lo que ya se sabe.

Idea tomada de Graphify (mapa precalculado + señal antes de explorar), sin su
peso: aquí basta una línea por archivo. Se regenera en la noche o a mano.

  python3 scripts/mapa.py            → docs/MAPA.md (repo) y ~/proyectos/mente/MAPA.md (mente)
  python3 scripts/mapa.py --repo     → solo el repo
  python3 scripts/mapa.py --mente    → solo la mente

Solo stdlib. Si algo falla en un archivo, se salta: el mapa nunca rompe nada.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MENTE = Path(os.environ.get("REMI_MENTE") or Path.home() / "proyectos" / "mente")
EXCLUIR = {".git", ".venv", "node_modules", "__pycache__", "target", ".next", "dist", "build", "out", "cache"}
MAX_SIMBOLOS = 6

_TS = re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?(?:function|const|class|type|interface)\s+([A-Za-z_]\w*)", re.M)
_RS = re.compile(r"^\s*pub\s+(?:async\s+)?(?:fn|struct|enum)\s+([A-Za-z_]\w*)", re.M)


def _simbolos_py(texto: str) -> tuple[str, list[str]]:
    try:
        arbol = ast.parse(texto)
    except SyntaxError:
        return "", []
    doc = (ast.get_docstring(arbol) or "").strip().splitlines()
    primera = doc[0].strip() if doc else ""
    nombres = [n.name for n in arbol.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_")]
    return primera[:90], nombres


def _simbolos(ruta: Path, texto: str) -> tuple[str, list[str]]:
    if ruta.suffix == ".py":
        return _simbolos_py(texto)
    if ruta.suffix in {".ts", ".tsx"}:
        return "", _TS.findall(texto)
    if ruta.suffix == ".rs":
        return "", _RS.findall(texto)
    return "", []


def _archivos(raiz: Path, sufijos: set[str]):
    for carpeta, dirs, archivos in os.walk(raiz):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUIR and not d.startswith("."))
        for nombre in sorted(archivos):
            p = Path(carpeta) / nombre
            if p.suffix in sufijos:
                yield p


def mapa_repo(raiz: Path = RAIZ) -> str:
    lineas = [f"# Mapa del repo Remi · {date.today().isoformat()}", "",
              "Una línea por archivo: ruta · líneas · qué expone. Léelo antes de buscar con grep; "
              "abre solo el archivo que necesites. Se regenera con `python3 scripts/mapa.py`.", ""]
    grupo_actual = None
    total = 0
    for p in _archivos(raiz, {".py", ".ts", ".tsx", ".rs"}):
        rel = p.relative_to(raiz)
        if "pruebas" in rel.parts or "__tests__" in rel.parts or rel.name.startswith("test_"):
            continue
        grupo = rel.parts[0] if len(rel.parts) > 1 else "."
        if len(rel.parts) > 2:
            grupo = "/".join(rel.parts[:2])
        if grupo != grupo_actual:
            lineas += ["", f"## {grupo}", ""]
            grupo_actual = grupo
        try:
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = texto.count("\n") + 1
        doc, simbolos = _simbolos(p, texto)
        extra = ", ".join(simbolos[:MAX_SIMBOLOS]) + (" …" if len(simbolos) > MAX_SIMBOLOS else "")
        partes = [f"`{rel.as_posix()}`", f"{n} l."]
        if doc:
            partes.append(doc)
        if extra:
            partes.append(extra)
        lineas.append("- " + " · ".join(partes))
        total += 1
    pruebas = sum(1 for _ in _archivos(raiz / "nucleo" / "pruebas", {".py"})) if (raiz / "nucleo" / "pruebas").exists() else 0
    lineas += ["", f"{total} archivos de código; {pruebas} archivos de pruebas en `nucleo/pruebas/` (correr: `cd nucleo && .venv/bin/python -m pytest -q`)."]
    return "\n".join(lineas) + "\n"


def _frontmatter(texto: str) -> dict:
    m = re.match(r"---\n(.*?)\n---", texto, re.S)
    if not m:
        return {}
    datos = {}
    for linea in m.group(1).splitlines():
        if ":" in linea:
            k, v = linea.split(":", 1)
            datos[k.strip()] = v.strip().strip('"')
    return datos


def mapa_mente(mente: Path = MENTE) -> str:
    lineas = [f"# Mapa de la mente · {date.today().isoformat()}", "",
              "Qué hay y dónde. Para buscar usa `preguntar` (MCP remi) o el índice; no leas carpetas enteras. "
              "Se regenera con `python3 scripts/mapa.py --mente`.", ""]
    for carpeta in sorted(d for d in mente.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))):
        notas = sorted(p for p in carpeta.rglob("*.md") if not p.name.startswith("_"))
        lineas += ["", f"## {carpeta.name}/ · {len(notas)} notas", ""]
        for p in notas[:60]:
            try:
                fm = _frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            titulo = fm.get("titulo") or p.stem
            datos = [x for x in (fm.get("tipo") or fm.get("fuente"), fm.get("fecha") or fm.get("fecha_ingesta"), fm.get("estatus"), fm.get("frentes") if fm.get("frentes") not in ("[]", "") else None) if x]
            lineas.append(f"- `{p.relative_to(mente).as_posix()}` · {titulo[:70]}" + (f" · {' · '.join(datos)}" if datos else ""))
        if len(notas) > 60:
            lineas.append(f"- … y {len(notas) - 60} más")
    return "\n".join(lineas) + "\n"


def main(argv: list[str]) -> int:
    que = set(argv) or {"--repo", "--mente"}
    if "--repo" in que:
        salida = RAIZ / "docs" / "MAPA.md"
        salida.write_text(mapa_repo(), encoding="utf-8")
        print(f"repo → {salida}")
    if "--mente" in que and MENTE.exists():
        salida = MENTE / "MAPA.md"
        salida.write_text(mapa_mente(), encoding="utf-8")
        print(f"mente → {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""El expediente de un pedido (SOP de la Fábrica, Bloque 1).

Vive en `fabrica/pedidos/<id>/expediente.md`, ignorado en git: el registro
durable es el PR y la traza de `consumo.py`. Frontmatter del SOP (`pedido,
repo, rama, estado, toca, riesgo, vueltas`) más `base`, que la línea necesita
para verificar y abrir el PR, y `creado`, para ordenar. Sin YAML externo:
`clave: valor`, listas `[a, b]`, `vueltas` entero.
"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
RAIZ = Path(os.environ.get("FABRICA_PEDIDOS") or REPO / "fabrica" / "pedidos")

ESTADOS = ("idea", "spec", "aprobado", "construyendo", "revisando", "pr", "cerrado")
RIESGOS = ("bajo", "medio", "alto")
SECCIONES = ("Contexto", "Spec", "Tests", "Construcción", "Escáneres", "Revisión", "Fuera de tarea", "Decisión")
CAMPOS = ("pedido", "repo", "rama", "base", "estado", "toca", "riesgo", "vueltas", "creado")


def _raiz(raiz: Path | None) -> Path:
    return Path(raiz) if raiz is not None else RAIZ


def carpeta(id_: str, raiz: Path | None = None) -> Path:
    return _raiz(raiz) / id_


def _slug(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plano).strip("-")[:24].strip("-") or "pedido"


def _valor(texto: str) -> Any:
    texto = texto.strip()
    if texto.startswith("[") and texto.endswith("]"):
        return [p.strip() for p in texto[1:-1].split(",") if p.strip()]
    if re.fullmatch(r"-?\d+", texto):
        return int(texto)
    return texto


def _texto(valor: Any) -> str:
    if isinstance(valor, list):
        return "[" + ", ".join(str(v) for v in valor) + "]"
    return str(valor)


def _escribir(id_: str, meta: dict[str, Any], secciones: dict[str, str], raiz: Path | None) -> None:
    lineas = ["---", *(f"{c}: {_texto(meta.get(c, ''))}" for c in CAMPOS), "---", ""]
    for nombre in SECCIONES:
        lineas += [f"## {nombre}", "", secciones.get(nombre, "").strip(), ""]
    destino = carpeta(id_, raiz) / "expediente.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".expediente.{os.getpid()}.tmp")
    tmp.write_text("\n".join(lineas), encoding="utf-8")
    os.replace(tmp, destino)


def crear(idea: str, repo: str, base: str, raiz: Path | None = None) -> str:
    ahora = datetime.now(timezone.utc)
    base_id = f"{ahora:%Y%m%d-%H%M}-{_slug(idea)}"
    id_, n = base_id, 1
    while carpeta(id_, raiz).exists():
        n += 1
        id_ = f"{base_id}-{n}"
    carpeta(id_, raiz).mkdir(parents=True)
    meta = {"pedido": id_, "repo": repo, "rama": f"fabrica/pedido-{id_}", "base": base, "estado": "idea",
            "toca": [], "riesgo": "bajo", "vueltas": 0, "creado": ahora.isoformat()}
    _escribir(id_, meta, {"Contexto": idea.strip()}, raiz)
    return id_


ID_VALIDO = re.compile(r"\d{8}-\d{4}-[a-z0-9-]+")


def leer(id_: str, raiz: Path | None = None) -> dict[str, Any]:
    """KeyError si no existe o si el id no tiene la forma de un pedido (nada de `../`)."""
    ruta = carpeta(id_, raiz) / "expediente.md"
    if not ID_VALIDO.fullmatch(id_) or not ruta.is_file():
        raise KeyError(id_)
    texto = ruta.read_text(encoding="utf-8")
    _, cabeza, cuerpo = texto.split("---\n", 2)
    meta = {}
    for linea in cabeza.splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            meta[clave.strip()] = _valor(valor)
    meta["toca"] = meta.get("toca") or []
    secciones: dict[str, str] = {}
    actual = None
    for linea in cuerpo.splitlines():
        if linea.startswith("## ") and linea[3:].strip() in SECCIONES:
            actual = linea[3:].strip()
            secciones[actual] = ""
        elif actual is not None:
            secciones[actual] += linea + "\n"
    return {"meta": meta, "secciones": {n: secciones.get(n, "").strip() for n in SECCIONES}}


def escribir_seccion(id_: str, seccion: str, texto: str, raiz: Path | None = None) -> None:
    if seccion not in SECCIONES:
        raise ValueError(f"sección desconocida: {seccion}")
    datos = leer(id_, raiz)
    datos["secciones"][seccion] = texto
    _escribir(id_, datos["meta"], datos["secciones"], raiz)


def cambiar(id_: str, raiz: Path | None = None, **campos: Any) -> None:
    desconocidos = set(campos) - set(CAMPOS)
    if desconocidos:
        raise ValueError(f"campos desconocidos: {sorted(desconocidos)}")
    if "estado" in campos and campos["estado"] not in ESTADOS:
        raise ValueError(f"estado desconocido: {campos['estado']}")
    if "riesgo" in campos and campos["riesgo"] not in RIESGOS:
        raise ValueError(f"riesgo desconocido: {campos['riesgo']}")
    datos = leer(id_, raiz)
    datos["meta"].update(campos)
    _escribir(id_, datos["meta"], datos["secciones"], raiz)


def cambiar_estado(id_: str, estado: str, raiz: Path | None = None) -> None:
    cambiar(id_, raiz, estado=estado)


def listar(raiz: Path | None = None) -> list[dict[str, Any]]:
    base = _raiz(raiz)
    if not base.is_dir():
        return []
    metas = []
    for hijo in base.iterdir():
        if (hijo / "expediente.md").is_file():
            metas.append(leer(hijo.name, raiz)["meta"])
    return sorted(metas, key=lambda m: str(m.get("creado", "")), reverse=True)

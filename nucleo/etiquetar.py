"""Etiquetar notas de la bóveda desde el teléfono, un toque por nota.

    /etiquetar   manda la siguiente nota con botones de tema

Para medir el modelo contra las reglas hace falta la opinión de Juan Camilo
sin pistas: el mensaje no muestra qué dijo ninguno de los dos. Solo salen
notas de fuente pública (nunca las de Rumbo ni las escritas a mano), y si el
título o el resumen tocan algo privado, va solo el link. Pausar no deja rastro.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

COMANDO = "/etiquetar"
PREFIJO = "et:"
PAUSA = "pausa"
NO_SE = "no_se"
MAX_NOTAS = 30
FUENTES_PUBLICAS = {"instagram", "youtube", "tiktok", "web"}
DOMINIOS = ("negocio", "ai-tools", "contenido", "crecimiento", "decisiones")
MAX_EXTRACTO = 110
_CARPETAS = ("01_raw", "02_procesado", "03_oro")


def _boveda() -> Path | None:
    for candidata in (os.environ.get("REMI_BOVEDA"), "/Volumes/ORGANIC/boveda"):
        if candidata and Path(candidata).is_dir():
            return Path(candidata)
    return None


def _frontmatter(ruta: Path) -> dict[str, Any]:
    hallado = re.match(r"---\n(.*?)\n---\n", ruta.read_text(encoding="utf-8", errors="replace"), re.S)
    if not hallado:
        return {}
    try:
        datos = yaml.safe_load(hallado.group(1))
    except yaml.YAMLError:
        return {}
    return datos if isinstance(datos, dict) else {}


def notas(boveda: Path) -> list[dict[str, Any]]:
    """Orden fijo por hash del id: mezcla los temas y no cambia entre corridas."""
    halladas = []
    for carpeta in _CARPETAS:
        for ruta in (boveda / carpeta).rglob("*.md"):
            datos = _frontmatter(ruta)
            if datos.get("fuente") in FUENTES_PUBLICAS and datos.get("id") and datos.get("url"):
                halladas.append(datos)
    halladas.sort(key=lambda d: hashlib.sha256(str(d["id"]).encode()).hexdigest())
    return halladas[:MAX_NOTAS]


def _ruta_etiquetas(boveda: Path) -> Path:
    return boveda / "_sistema" / "etiquetas.json"


def _leer(boveda: Path) -> dict[str, str]:
    ruta = _ruta_etiquetas(boveda)
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos if isinstance(datos, dict) else {}


def _guardar(boveda: Path, etiquetas: dict[str, str]) -> None:
    ruta = _ruta_etiquetas(boveda)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(etiquetas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _botones(nota_id: str) -> list[list[dict[str, str]]]:
    def boton(texto: str, valor: str) -> dict[str, str]:
        return {"text": texto, "callback_data": f"{PREFIJO}{valor}:{nota_id}"}

    return [
        [boton("Negocio", "negocio"), boton("IA", "ai-tools")],
        [boton("Contenido", "contenido"), boton("Crecimiento", "crecimiento")],
        [boton("Decisiones", "decisiones"), boton("No sé", NO_SE)],
        [boton("Pausar", PAUSA)],
    ]


def _texto(nota: dict[str, Any], hechas: int, total: int) -> str:
    import telegram

    url = str(nota["url"])
    titulo = str(nota.get("titulo") or "")
    extracto = str(nota.get("resumen") or "")[:MAX_EXTRACTO]
    cuerpo = f"{titulo}\n{extracto}".strip()
    if telegram.es_privado(cuerpo):
        cuerpo = "Esta se ve mejor en el link."
    return f"{hechas + 1} de {total}. ¿De qué trata?\n{cuerpo}\n{url}"


def siguiente(boveda: Path) -> tuple[str, list[list[dict[str, str]]] | None]:
    todas = notas(boveda)
    etiquetas = _leer(boveda)
    pendientes = [n for n in todas if str(n["id"]) not in etiquetas]
    if not todas:
        return "Todavía no hay notas para etiquetar.", None
    if not pendientes:
        return medicion(boveda), None
    nota = pendientes[0]
    return _texto(nota, len(todas) - len(pendientes), len(todas)), _botones(str(nota["id"]))


def medicion(boveda: Path) -> str:
    """Solo cuenta lo que tiene etiqueta tuya y respuesta del modelo."""
    etiquetas = _leer(boveda)
    reglas = modelo = comparadas = 0
    for nota in notas(boveda):
        tuya = etiquetas.get(str(nota["id"]))
        if tuya in DOMINIOS and nota.get("dominio_modelo"):
            comparadas += 1
            reglas += nota.get("dominio") == tuya
            modelo += nota.get("dominio_modelo") == tuya
    if not comparadas:
        return "Listo por ahora. Aún no hay notas con respuesta del modelo para comparar."
    return f"Listo. De {comparadas} notas, las reglas coinciden contigo en {reglas} y el modelo en {modelo}."


def manejar_comando(texto: str) -> tuple[str, list[list[dict[str, str]]] | None] | None:
    if texto.strip().split("@")[0].lower() != COMANDO:
        return None
    boveda = _boveda()
    if boveda is None:
        return "No encuentro la bóveda. El disco tiene que estar conectado.", None
    return siguiente(boveda)


def manejar_boton(datos: str) -> tuple[str, list[list[dict[str, str]]] | None] | None:
    """El botón de un mensaje viejo también vale: la etiqueta queda con su nota."""
    if not datos.startswith(PREFIJO):
        return None
    boveda = _boveda()
    if boveda is None:
        return "No encuentro la bóveda. El disco tiene que estar conectado.", None
    valor, _, nota_id = datos[len(PREFIJO):].partition(":")
    if valor == PAUSA:
        return "Quedó guardado. Sigues con /etiquetar cuando quieras.", None
    if valor not in (*DOMINIOS, NO_SE) or nota_id not in {str(n["id"]) for n in notas(boveda)}:
        return None
    etiquetas = _leer(boveda)
    etiquetas[nota_id] = valor
    _guardar(boveda, etiquetas)
    return siguiente(boveda)

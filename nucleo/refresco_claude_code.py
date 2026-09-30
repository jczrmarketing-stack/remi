"""Refresco semanal del oficio Claude Code (Biblia Parte VI, Fase S punto 5).

Domingos a las 5:00 (después de la copia de las 3:00 y la consolidación de
las 4:00, `scripts/refresco-claude-code.sh` + LaunchAgent
`com.remi.refresco-claude-code`): trae el changelog oficial, y Haiku anota
SOLO lo que no esté ya anotado bajo «## Cambios anotados» en
`claude-code.md`, con fecha. La verificación anti-invento es la misma idea
que `estado_libro.py` (`entidades_sospechosas`/`_invento`), pero contra la
fuente correcta: el texto real que se trajo del changelog, no la respuesta
del modelo citándose a sí misma.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

import boveda_git
import estado_libro
import pensar
import sembrar_conocimiento

URL_CHANGELOG = "https://docs.claude.com/en/release-notes/claude-code"
ENCABEZADO = "## Cambios anotados"
TIMEOUT_SEGUNDOS = 15.0

INSTRUCCIONES = (
    "Te paso el texto del changelog oficial de Claude Code y lo que ya está anotado. "
    "Devolvé SOLO las novedades reales que NO estén ya anotadas, una por línea, cada una "
    "empezando con la fecha tal como aparece en el changelog entre corchetes, por ejemplo "
    "[2026-09-15] texto breve. No inventes fechas ni texto que no esté literal en el "
    "changelog que te pasé. Sin markdown, sin numeración. Si no hay nada nuevo, devolvé "
    "exactamente la palabra: NADA."
)


def _ruta_oficio() -> Path:
    return sembrar_conocimiento.carpeta_oficios() / "claude-code.md"


def _ya_anotado(texto_del_oficio: str) -> str:
    if ENCABEZADO not in texto_del_oficio:
        return ""
    return texto_del_oficio.split(ENCABEZADO, 1)[1]


def traer_changelog(url: str = URL_CHANGELOG) -> str | None:
    """El texto real de la página. None si no se pudo traer — nunca rompe
    el refresco: sin fuente, no hay nada que anotar esta semana."""
    try:
        respuesta = httpx.get(url, timeout=TIMEOUT_SEGUNDOS, follow_redirects=True)
        respuesta.raise_for_status()
        return respuesta.text
    except httpx.HTTPError as error:
        print(f"[refresco-claude-code] no pude traer el changelog ({type(error).__name__})", file=sys.stderr)
        return None


def _extraer(changelog: str, ya_anotado: str) -> str | None:
    pedido = (
        f"Changelog:\n{changelog}\n\n---\nYa anotado hasta ahora:\n{ya_anotado.strip() or '(nada todavía)'}"
    )
    try:
        pensado = pensar._una_llamada_claude(pensar.MODOS["rapido"], pedido, INSTRUCCIONES, [])
    except Exception as error:  # noqa: BLE001 — sin Haiku, no se anota nada esta semana
        print(f"[refresco-claude-code] Haiku no contestó ({type(error).__name__})", file=sys.stderr)
        return None
    if pensado is None:
        return None
    return pensado.paso_minimo.strip()


def _lineas_verificadas(salida: str, fuente: str) -> list[str]:
    """Cada línea que el modelo propuso, solo si TODAS sus entidades
    verificables (siglas, números, archivos) aparecen literales en la
    fuente real (el changelog) — no en la salida del modelo. Lo que no
    pasa, se descarta y se loguea; nunca tumba el resto de las líneas
    buenas."""
    aceptadas: list[str] = []
    for linea in (l.strip() for l in salida.splitlines()):
        if not linea:
            continue
        sospechosa = estado_libro._invento(linea, fuente)
        if sospechosa is not None:
            print(f"[refresco-claude-code] rechazada por invento: {sospechosa!r} no está en el changelog — {linea!r}", file=sys.stderr)
            continue
        aceptadas.append(linea)
    return aceptadas


def refrescar(url: str = URL_CHANGELOG, ahora: datetime | None = None) -> int:
    """Cuántas líneas nuevas quedaron anotadas. 0 si no hubo changelog, si
    el modelo no contestó, si dijo NADA, o si todo lo que propuso fue
    rechazado por la verificación anti-invento — en cualquiera de esos
    casos el oficio no se toca."""
    ruta = _ruta_oficio()
    if not ruta.is_file():
        print(f"[refresco-claude-code] no está {ruta}: nada que refrescar", file=sys.stderr)
        return 0

    changelog = traer_changelog(url)
    if not changelog:
        return 0

    original = ruta.read_text()
    ya_anotado = _ya_anotado(original)

    salida = _extraer(changelog, ya_anotado)
    if not salida or salida.strip().upper() == "NADA":
        return 0

    lineas = _lineas_verificadas(salida, changelog)
    if not lineas:
        return 0

    hoy = (ahora or datetime.now(timezone.utc)).date().isoformat()
    boveda_git.snapshot_antes("el oficio Claude Code (refresco semanal del changelog)")
    texto = original if original.endswith("\n") else original + "\n"
    if ENCABEZADO not in texto:
        texto += f"\n{ENCABEZADO}\n"
    elif texto.rstrip().endswith("(vacío)"):
        texto = texto.rsplit("(vacío)", 1)[0].rstrip() + "\n"
    for linea in lineas:
        texto += f"- [{hoy}] {linea}\n" if not linea.startswith("[") else f"- {linea}\n"
    ruta.write_text(texto)
    boveda_git.snapshot_despues(
        f"oficio claude-code: {len(lineas)} novedad(es) del changelog, refresco de {hoy}"
    )
    return len(lineas)


if __name__ == "__main__":
    n = refrescar()
    print(f"[refresco-claude-code] {n} línea(s) nueva(s)", file=sys.stderr)

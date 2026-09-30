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

URL_CHANGELOG = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
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


#  el CHANGELOG real de Claude Code mide ~850 KB (todo el historial) y una
# sola versión reciente puede medir >20 KB (probado en vivo el 1-oct-2026:
# la primera entrada, 2.1.285, mide 21.267 caracteres) — un límite de 8.000
# cortaba ANTES de esa entrada y dejaba al modelo con "el changelog está
# vacío" de verdad, visto en una corrida real. 30.000 deja lugar de sobra
# para la última versión entera, sin acercarse al costo de mandarlo todo.
LIMITE_CARACTERES = 30000


def _recortar(changelog: str, limite: int = LIMITE_CARACTERES) -> str:
    """Solo lo más reciente: los cambios más nuevos van primero, así que
    cortar a un límite de caracteres alcanza para "lo de esta semana"; se
    corta en un límite de sección («## »), no a mitad de una entrada — pero
    solo si eso deja algo real: si la primera sección sola ya pasa el
    límite, un corte crudo (una entrada partida a la mitad) es mejor que
    dejar al modelo con un changelog vacío."""
    if len(changelog) <= limite:
        return changelog
    recorte = changelog[:limite]
    ultimo_encabezado = recorte.rfind("\n## ")
    # Menos de un cuarto del límite aprovechado: el corte por sección
    # dejaría casi nada (el bug real del 1-oct-2026). Mejor lo crudo.
    if ultimo_encabezado > limite // 4:
        return recorte[:ultimo_encabezado]
    return recorte


def traer_changelog(url: str = URL_CHANGELOG) -> str | None:
    """Las entradas más recientes del changelog real (recortado — ver
    `_recortar`). None si no se pudo traer: nunca rompe el refresco, sin
    fuente no hay nada que anotar esta semana."""
    try:
        respuesta = httpx.get(url, timeout=TIMEOUT_SEGUNDOS, follow_redirects=True)
        respuesta.raise_for_status()
        return _recortar(respuesta.text)
    except httpx.HTTPError as error:
        print(f"[refresco-claude-code] no pude traer el changelog ({type(error).__name__})", file=sys.stderr)
        return None


# «rápido» (20 s) es para el chat, con alguien esperando. Este refresco no
# tiene a nadie esperando y el prompt es grande (hasta LIMITE_CARACTERES de
# changelog real): mismo modelo (Haiku), techo propio y más largo — probado
# en vivo el 1-oct-2026, «rápido» cortaba a los 20 s con un prompt de ~7 k
# tokens y nunca llegaba a contestar.
_MODO_REFRESCO = pensar.Modo("refresco-claude-code", "haiku", 120.0, 0, 4000)


def _extraer(changelog: str, ya_anotado: str) -> str | None:
    pedido = (
        f"Changelog:\n{changelog}\n\n---\nYa anotado hasta ahora:\n{ya_anotado.strip() or '(nada todavía)'}"
    )
    try:
        pensado = pensar._una_llamada_claude(_MODO_REFRESCO, pedido, INSTRUCCIONES, [])
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

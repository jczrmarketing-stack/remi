"""PR (PLAN-FINAL.md, Biblia Parte VIII): del encargo a producción. Los
cinco criterios:
1. Paquete base al abrir un proyecto.
2. Revisión del diff con otro modelo al cerrar cada sesión con commits.
3. Tres líneas sin jerga (qué se hizo, por qué, qué se podría romper).
4. Ningún `Entrega` con un hallazgo de seguridad serio abierto.
5. La lista de la verdad antes de cerrar una fase.

Los puntos 2 y 3 necesitan una llamada real a OTRO modelo del que
escribió el código, disparada cuando una sesión de Claude Code cierra
con commits (gancho `SessionEnd`) — mismo BLOQUEADO que el investigador
de `analisis_camino.py` y los estimadores de `estimacion.py`: wirear un
modelo real y un gancho de Claude Code es trabajo de una sesión
dedicada. `Revisor` ya es la interfaz tipada y probada con un doble.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

PLANTILLA_CLAUDE_MD = """# CLAUDE.md — {nombre}

{descripcion}

## Stack

{stack}

## Reglas que no se negocian

- Los contratos viven en `contratos/` — se generan, nunca a mano.
- TypeScript estricto / mypy estricto, según corresponda.
- Un prompt = una tarea = un commit.
- Antes de cada entrega: revisión de seguridad (fase PR).

## Cómo se trabaja en este repo

- Diseño primero, código después.
- Pruebas donde duele.
- Al cerrar un trabajo: anotar la lección.
"""

PLANTILLA_CONTRATOS = """{{
  "$comment": "Contratos de {nombre} — sagrados. Los tipos se generan de aquí.",
  "version": 1
}}
"""


def generar_paquete_base(nombre_proyecto: str, descripcion: str, stack: str) -> dict[str, str]:
    """PR.1: el paquete base — `{ruta: contenido}`. No escribe nada por
    sí solo: quien llama decide dónde (nunca dentro de una app gestionada
    sin que Juan Camilo lo pida — regla dura de este operador, no del
    plan)."""
    return {
        "CLAUDE.md": PLANTILLA_CLAUDE_MD.format(nombre=nombre_proyecto, descripcion=descripcion, stack=stack),
        "contratos/contratos.json": PLANTILLA_CONTRATOS.format(nombre=nombre_proyecto),
    }


Severidad = Literal["serio", "medio", "bajo"]


@dataclass(frozen=True)
class HallazgoSeguridad:
    archivo: str
    severidad: Severidad
    resumen: str


def puede_entregar(hallazgos: list[HallazgoSeguridad]) -> bool:
    """PR.4: un solo hallazgo `serio` abierto basta para bloquear el paso
    «Entrega» del Camino — nunca «lo arreglamos después»."""
    return not any(h.severidad == "serio" for h in hallazgos)


@dataclass(frozen=True)
class HallazgoDiff:
    archivo: str
    gravedad: Literal["grave", "medio", "menor"]
    resumen: str
    encargo_de_arreglo: str


@dataclass(frozen=True)
class RevisionDiff:
    hallazgos: list[HallazgoDiff]  # ordenados por gravedad, más grave primero
    explicacion: list[str]  # PR.3: tres líneas sin jerga — qué, por qué, qué se podría romper


Revisor = Callable[[str], RevisionDiff]
"""Recibe el diff de una sesión cerrada y devuelve la revisión completa
— lo hace un modelo DISTINTO del que escribió el código (quien construye
el `Revisor` real decide cuál; este módulo nunca lo elige)."""


def revisar_sesion(diff: str, revisor: Revisor) -> RevisionDiff:
    """PR.2 + PR.3. `revisor` se inyecta siempre — nunca una llamada real
    de pago en pytest."""
    revision = revisor(diff)
    ordenado = sorted(revision.hallazgos, key=lambda h: {"grave": 0, "medio": 1, "menor": 2}[h.gravedad])
    return RevisionDiff(hallazgos=ordenado, explicacion=revision.explicacion)


def nada_grave_pendiente(revision: RevisionDiff) -> bool:
    """Lo que el Camino necesita para marcar algo hecho (PR.2): la
    revisión del diff no puede tener hallazgos `grave` sin resolver."""
    return not any(h.gravedad == "grave" for h in revision.hallazgos)


@dataclass(frozen=True)
class ListaDeLaVerdad:
    """PR.5: las cuatro preguntas antes de cerrar una fase. Juan Camilo
    las contesta — Remi nunca se las contesta a sí mismo."""
    se_uso_de_verdad: bool
    revision_sin_pendientes_graves: bool
    entiende_que_cambio: bool
    hay_copia_monitoreo_y_reversa: bool

    def fase_puede_cerrar(self) -> bool:
        return all(
            (self.se_uso_de_verdad, self.revision_sin_pendientes_graves, self.entiende_que_cambio, self.hay_copia_monitoreo_y_reversa)
        )

    def primera_pendiente(self) -> str | None:
        """Ley 3: si algo falta, la fase se encoge a ESE paso — nunca una
        lista completa de culpas, solo lo que falta hacer ahora."""
        if not self.se_uso_de_verdad:
            return "usarlo de verdad, no solo pasar las pruebas"
        if not self.revision_sin_pendientes_graves:
            return "cerrar los pendientes graves de la revisión con otro modelo"
        if not self.entiende_que_cambio:
            return "entender qué cambió (pedir la explicación de tres líneas otra vez)"
        if not self.hay_copia_monitoreo_y_reversa:
            return "tener copia, monitoreo y forma de volver atrás"
        return None

"""R5.1 (PLAN-FINAL.md): Hoy ordenado por el Rumbo. Orden: (1) fecha
prometida; (2) lo que cumple la cuenta de la semana o el paso de una
apuesta; (3) empate: más meta estable por hora medida. Una sola
propuesta sube, con una línea de por qué; si ninguna de las tres aplica,
por fecha (ley 4: una locura por pantalla, nunca una lista).

Esto es la regla de ORDEN, pura y probada. Wirearla contra `aldia.py`
para que «Hoy» la use de verdad entre TODOS los proyectos abiertos a la
vez (hoy `calcular_sigue` solo mira el libro activo) es una integración
más profunda, que no se apura sin verla contra la pantalla real — queda
anotada en la bitácora de cierre de R5, no como BLOQUEADO (no necesita
nada externo), sino como decisión de alcance de esta sesión.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PropuestaHoy:
    texto: str
    fecha_prometida: datetime | None
    cumple_cuenta_semana: bool
    cumple_paso_apuesta: bool
    meta_estable_por_hora: float


@dataclass(frozen=True)
class PropuestaElegida:
    texto: str
    por_que: str


def elegir(propuestas: list[PropuestaHoy]) -> PropuestaElegida | None:
    if not propuestas:
        return None

    con_fecha = [p for p in propuestas if p.fecha_prometida is not None]
    if con_fecha:
        elegida = min(con_fecha, key=lambda p: p.fecha_prometida)  # type: ignore[arg-type,return-value]
        fecha = elegida.fecha_prometida
        assert fecha is not None
        return PropuestaElegida(texto=elegida.texto, por_que=f"tiene fecha prometida: {fecha:%d de %b}".lower())

    de_rumbo = [p for p in propuestas if p.cumple_cuenta_semana or p.cumple_paso_apuesta]
    if de_rumbo:
        elegida = max(de_rumbo, key=lambda p: p.meta_estable_por_hora)
        if elegida.cumple_cuenta_semana:
            return PropuestaElegida(texto=elegida.texto, por_que="te falta para la cuenta de esta semana")
        return PropuestaElegida(texto=elegida.texto, por_que="es el paso que sigue de una apuesta activa")

    elegida = max(propuestas, key=lambda p: p.meta_estable_por_hora)
    return PropuestaElegida(texto=elegida.texto, por_que="es lo que más aporta por hora medida")

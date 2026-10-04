"""R1 (forma N, PLAN-FINAL.md): Rumbo — visión, meta, escalera y punto de
partida. Sin IA donde hay reglas: `parsear_vision` es una función pura que
solo extrae números y plazos del texto; nunca decide la meta. La meta real
cambia únicamente con `POST /rumbo/meta {..., confirmada: true}` (regla 2
del mega prompt).

El punto de partida (`origen: medido`) se calcula en vivo sobre sesiones y
entregas reales — no se guarda snapshot, así que no hay fila que archivar
cada vez que cambia (regla 3: nunca se borra una fila; lo medido no es una
nota de Juan Camilo, es un cálculo).
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

import db
import plata
import reloj
import trabajo
from modelos import Apuesta, Escalon, Meta, Pregunta, Propuesta, Vision

BOGOTA = ZoneInfo("America/Bogota")

router = APIRouter(prefix="/rumbo", tags=["rumbo"])

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "rumbo.json"
MINIMO_PROPUESTAS_PROPIAS = 5


def _config() -> dict[str, object]:
    return json.loads(RUTA_CONFIG.read_text())

_NUMEROS_PALABRA = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
}
_PALABRA_NUMERO = "|".join(_NUMEROS_PALABRA)

# "10 a 15 mil", "10.000 a 15.000", "10 mil" — con o sin rango.
_MONTO = re.compile(
    r"(\d[\d.,]*)\s*(mil)?\s*(?:a|-)\s*(\d[\d.,]*)\s*(mil)?|(\d[\d.,]*)\s*(mil)?",
    re.IGNORECASE,
)
_MESES_SEGUIDOS = re.compile(
    rf"(\d+|{_PALABRA_NUMERO})\s+meses?\s+seguidos?",
    re.IGNORECASE,
)


def _numero(texto: str) -> float:
    limpio = texto.replace(".", "").replace(",", ".")
    return float(limpio)


@dataclass(frozen=True)
class PropuestaVision:
    monto_min: float | None
    monto_max: float | None
    meses_seguidos: int | None
    # Lo que acompaña la cifra pero no es un monto ni un plazo — por ahora
    # no se extrae solo (B1/R1 no tiene todavía una lista de límites
    # reconocibles); queda vacío hasta que un patrón real lo pida.
    limites: str | None


def parsear_vision(texto: str) -> PropuestaVision:
    """Nunca lanza ni adivina: lo que no se reconoce queda `None`, y
    Remi lo pregunta en el panel (regla 9) en vez de inventarlo."""
    monto_min: float | None = None
    monto_max: float | None = None
    coincidencia = _MONTO.search(texto)
    if coincidencia is not None:
        if coincidencia.group(1) is not None:
            a = _numero(coincidencia.group(1))
            b = _numero(coincidencia.group(3))
            # "10 a 15 mil": el "mil" al final vale para los dos lados del
            # rango, no solo para el segundo número.
            mil = bool(coincidencia.group(2) or coincidencia.group(4))
            if mil:
                a *= 1000
                b *= 1000
            monto_min, monto_max = min(a, b), max(a, b)
        elif coincidencia.group(5) is not None:
            valor = _numero(coincidencia.group(5))
            if coincidencia.group(6):
                valor *= 1000
            monto_min = monto_max = valor

    meses_seguidos: int | None = None
    coincidencia_meses = _MESES_SEGUIDOS.search(texto)
    if coincidencia_meses is not None:
        crudo = coincidencia_meses.group(1).lower()
        meses_seguidos = _NUMEROS_PALABRA.get(crudo) or int(crudo)

    return PropuestaVision(monto_min=monto_min, monto_max=monto_max, meses_seguidos=meses_seguidos, limites=None)


def calcular_partida_medida(conexion) -> list["ItemPartida"]:
    """Lo medido (nunca lo dicho ni lo preguntado): horas reales de la
    última semana, proyectos entregados (→ dominio por regla fija) y
    concentración en el cliente mayor — todo de sesiones/entregas reales,
    nunca de un estimado."""
    ahora = datetime.now(timezone.utc)
    desde_semana = (ahora - timedelta(days=7)).isoformat()

    fila_horas = conexion.execute(
        "SELECT COALESCE(SUM(real_min), 0) AS minutos FROM sesiones WHERE fin IS NOT NULL AND inicio >= ?",
        (desde_semana,),
    ).fetchone()
    horas_semana = round(fila_horas["minutos"] / 60, 1)

    entregados = conexion.execute(
        "SELECT COUNT(DISTINCT proyecto_id) AS n FROM entregas WHERE estado IN ('entregada', 'pagada')"
    ).fetchone()["n"]
    if entregados >= 5:
        dominio = "cirujano"
    elif entregados >= 1:
        dominio = "sabe"
    else:
        dominio = "aprendiz"

    items = [
        ItemPartida(tipo="recurso", texto="Horas reales por semana", valor=str(horas_semana), origen="medido", dominio=None),
        ItemPartida(
            tipo="habilidad",
            texto="Proyectos entregados",
            valor=str(entregados),
            origen="medido",
            dominio=dominio,
        ),
    ]

    filas_cliente = conexion.execute(
        "SELECT cliente, COALESCE(SUM(monto), 0) AS total FROM entregas WHERE estado = 'pagada' GROUP BY cliente"
    ).fetchall()
    total_pagado = sum(fila["total"] for fila in filas_cliente)
    if total_pagado > 0:
        mayor = max(filas_cliente, key=lambda f: f["total"])
        pct = round(100 * mayor["total"] / total_pagado, 1)
        items.append(
            ItemPartida(
                tipo="preferencia",
                texto=f"Concentración en {mayor['cliente']}",
                valor=f"{pct}%",
                origen="medido",
                dominio=None,
            )
        )
    return items


class ItemPartida(BaseModel):
    tipo: str
    texto: str
    valor: str
    origen: str
    dominio: str | None


class PropuestaVisionVista(BaseModel):
    monto_min: float | None
    monto_max: float | None
    meses_seguidos: int | None
    limites: str | None


class CuerpoVision(BaseModel):
    texto: str


class CuerpoMeta(BaseModel):
    monto_min: float | None = None
    monto_max: float | None = None
    meses_seguidos: int | None = None
    limites: str | None = None
    confirmada: bool = False


class MetaVista(BaseModel):
    monto_min: float | None
    monto_max: float | None
    meses_seguidos: int | None
    limites: str | None


class EscalonVista(BaseModel):
    n: int
    texto: str
    criterio: str
    estado: str


class VistaRumbo(BaseModel):
    vision: str | None
    meta: MetaVista | None
    escalera: list[EscalonVista]
    partida: list[ItemPartida]


def _voz_de_propuesta(propuesta: PropuestaVision) -> str:
    if propuesta.monto_min is None or propuesta.monto_max is None:
        return "No encontré un monto ahí. Cuéntamelo con una cifra y te armo la propuesta."
    if propuesta.monto_min == propuesta.monto_max:
        cifra = f"{int(propuesta.monto_min):,}".replace(",", ".")
    else:
        cifra = f"{int(propuesta.monto_min):,}".replace(",", ".") + f" a {int(propuesta.monto_max):,}".replace(",", ".")
    plazo = f", {propuesta.meses_seguidos} meses seguidos" if propuesta.meses_seguidos else ""
    return f"Entendí: {cifra} al mes{plazo}. Confírmamela y la dejo como meta."


@router.post("/vision")
def contar_vision(cuerpo: CuerpoVision) -> dict:
    conexion = db.conectar()
    try:
        propuesta = parsear_vision(cuerpo.texto)
        db.crear_vision(conexion, Vision(id=uuid4(), texto=cuerpo.texto, creada_en=datetime.now(timezone.utc)))
        return {
            "propuesta": PropuestaVisionVista(
                monto_min=propuesta.monto_min,
                monto_max=propuesta.monto_max,
                meses_seguidos=propuesta.meses_seguidos,
                limites=propuesta.limites,
            ).model_dump(),
            "voz": _voz_de_propuesta(propuesta),
        }
    finally:
        conexion.close()


@router.post("/meta")
def fijar_meta(cuerpo: CuerpoMeta) -> MetaVista | None:
    conexion = db.conectar()
    try:
        if cuerpo.confirmada:
            db.crear_meta(
                conexion,
                Meta(
                    id=uuid4(),
                    monto_min=cuerpo.monto_min,
                    monto_max=cuerpo.monto_max,
                    meses_seguidos=cuerpo.meses_seguidos,
                    limites=cuerpo.limites,
                    confirmada=True,
                    creada_en=datetime.now(timezone.utc),
                ),
            )
        vigente = db.meta_vigente(conexion)
        if vigente is None:
            return None
        return MetaVista(
            monto_min=vigente.monto_min,
            monto_max=vigente.monto_max,
            meses_seguidos=vigente.meses_seguidos,
            limites=vigente.limites,
        )
    finally:
        conexion.close()


@router.get("", response_model=VistaRumbo)
def ver_rumbo() -> VistaRumbo:
    conexion = db.conectar()
    try:
        vision = db.ultima_vision(conexion)
        meta = db.meta_vigente(conexion)
        escalera = db.listar_escalera(conexion)
        partida = calcular_partida_medida(conexion)
        return VistaRumbo(
            vision=vision.texto if vision else None,
            meta=(
                MetaVista(monto_min=meta.monto_min, monto_max=meta.monto_max, meses_seguidos=meta.meses_seguidos, limites=meta.limites)
                if meta
                else None
            ),
            escalera=[EscalonVista(n=e.n, texto=e.texto, criterio=e.criterio, estado=e.estado) for e in escalera],
            partida=partida,
        )
    finally:
        conexion.close()


# --- R2 (forma R): cuenta hacia atrás ---------------------------------

_VERBO_PROPUESTA = re.compile(r"\b(?:mand[eé]|envi[eé]|pas[eé])\b.*\bpropuesta\b", re.IGNORECASE)
_CLIENTE_PROPUESTA = re.compile(r"\ba\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]*)", re.UNICODE)
_MONTO_PROPUESTA = re.compile(r"\bpor\s+\$?\s*(\d[\d.,]*)", re.IGNORECASE)


@dataclass(frozen=True)
class PropuestaParseada:
    cliente: str
    monto: float


def parsear_propuesta(texto: str) -> PropuestaParseada | None:
    """«le mandé la propuesta a X por 1.500». Función pura, sin IA; si no
    se reconoce cliente Y monto, devuelve `None` — nunca adivina."""
    if not _VERBO_PROPUESTA.search(texto):
        return None
    coincidencia_cliente = _CLIENTE_PROPUESTA.search(texto)
    coincidencia_monto = _MONTO_PROPUESTA.search(texto)
    if coincidencia_cliente is None or coincidencia_monto is None:
        return None
    monto = _numero(coincidencia_monto.group(1))
    return PropuestaParseada(cliente=coincidencia_cliente.group(1), monto=monto)


class CuerpoPropuesta(BaseModel):
    cliente: str
    monto: float


@router.post("/propuestas", status_code=201)
def registrar_propuesta(cuerpo: CuerpoPropuesta) -> dict:
    conexion = db.conectar()
    try:
        propuesta = Propuesta(id=uuid4(), cliente=cuerpo.cliente, monto=cuerpo.monto, fecha=datetime.now(timezone.utc), estado="pendiente")
        db.crear_propuesta(conexion, propuesta)
        return {"id": str(propuesta.id)}
    finally:
        conexion.close()


class CuentaCierre(BaseModel):
    p: float
    base_n: int
    origen: str


class CaminoHoras(BaseModel):
    camino: str
    pct: float


class VistaCuenta(BaseModel):
    meta_mes: float | None
    ticket: float | None
    necesarias: float | None
    tienes: float
    cierre: CuentaCierre
    propuestas_semana: int
    hechas_semana: int
    horas_semana: list[CaminoHoras]


def _lunes(momento: datetime) -> datetime:
    local = momento.astimezone(BOGOTA)
    cero = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return (cero - timedelta(days=cero.weekday())).astimezone(timezone.utc)


@router.get("/cuenta", response_model=VistaCuenta)
def ver_cuenta() -> VistaCuenta:
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        meta = db.meta_vigente(conexion)
        meta_mes = (meta.monto_min + meta.monto_max) / 2 if meta and meta.monto_min is not None and meta.monto_max is not None else None

        propuestas = db.listar_propuestas(conexion)
        total = len(propuestas)
        cerradas = sum(1 for p in propuestas if p.estado == "cerrada")
        if total >= MINIMO_PROPUESTAS_PROPIAS:
            p_cierre, base_n, origen = cerradas / total, total, "propia"
        else:
            p_cierre, base_n, origen = float(_config()["tasa_cierre_general"]), total, "general"  # type: ignore[arg-type]

        montos = [p.monto for p in propuestas]
        ticket = sum(montos) / len(montos) if montos else None
        necesarias = (meta_mes / ticket) if (meta_mes is not None and ticket) else None

        lunes = _lunes(ahora)
        propuestas_semana = sum(1 for p in propuestas if p.fecha >= lunes)
        hechas_semana = sum(1 for p in propuestas if p.estado == "cerrada" and p.fecha >= lunes)

        apuestas = db.listar_apuestas(conexion)
        horas_semana: list[CaminoHoras] = []
        if apuestas:
            minutos_por_camino = {a.camino: trabajo.minutos_entre_rango(a.camino, lunes, ahora) for a in apuestas}
            total_minutos = sum(minutos_por_camino.values())
            if total_minutos > 0:
                horas_semana = [
                    CaminoHoras(camino=camino, pct=round(100 * minutos / total_minutos, 1))
                    for camino, minutos in minutos_por_camino.items()
                    if minutos > 0
                ]

        return VistaCuenta(
            meta_mes=meta_mes,
            ticket=ticket,
            necesarias=necesarias,
            tienes=plata.cobrado_mes(conexion, ahora),
            cierre=CuentaCierre(p=round(p_cierre, 4), base_n=base_n, origen=origen),
            propuestas_semana=propuestas_semana,
            hechas_semana=hechas_semana,
            horas_semana=horas_semana,
        )
    finally:
        conexion.close()


# --- R2 (forma O): apuestas --------------------------------------------

DIAS_PREGUNTA_SIGUE_O_PAUSA = 14
DIAS_PREGUNTA_LA_VOLVERIAS_A_HACER = 60


class CuerpoApuesta(BaseModel):
    camino: str
    inicio: datetime
    fin: datetime
    tope_horas: float
    tope_plata: float


class ApuestaProgreso(BaseModel):
    hecho: float
    meta: float


class ApuestaVista(BaseModel):
    id: str
    camino: str
    inicio: datetime
    fin: datetime
    tope_horas: float
    tope_plata: float
    gastado_horas: float
    gastado_plata: float
    senal_sigue: bool
    senal_pausa: bool
    progreso: ApuestaProgreso
    resultado: str | None


def _gastado_plata(conexion: sqlite3.Connection, camino: str, desde: datetime, hasta: datetime) -> float:
    return sum(g.monto for g in db.gastos_de_tema(conexion, camino) if desde <= g.fecha <= hasta)


def _a_vista(conexion: sqlite3.Connection, apuesta: Apuesta, ahora: datetime) -> ApuestaVista:
    gastado_horas = round(trabajo.minutos_entre_rango(apuesta.camino, apuesta.inicio, min(ahora, apuesta.fin)) / 60, 1)
    gastado_plata = _gastado_plata(conexion, apuesta.camino, apuesta.inicio, min(ahora, apuesta.fin))
    # Señal de pausa: se pasó de cualquiera de los dos topes. Señal de
    # sigue: va dentro de los dos, a mitad de camino en tiempo o menos.
    senal_pausa = gastado_horas > apuesta.tope_horas or gastado_plata > apuesta.tope_plata
    duracion_total = (apuesta.fin - apuesta.inicio).total_seconds()
    transcurrido = (min(ahora, apuesta.fin) - apuesta.inicio).total_seconds()
    pct_tiempo = transcurrido / duracion_total if duracion_total > 0 else 1.0
    senal_sigue = not senal_pausa and pct_tiempo <= 0.5
    return ApuestaVista(
        id=str(apuesta.id),
        camino=apuesta.camino,
        inicio=apuesta.inicio,
        fin=apuesta.fin,
        tope_horas=apuesta.tope_horas,
        tope_plata=apuesta.tope_plata,
        gastado_horas=gastado_horas,
        gastado_plata=gastado_plata,
        senal_sigue=senal_sigue,
        senal_pausa=senal_pausa,
        progreso=ApuestaProgreso(hecho=round(pct_tiempo, 2), meta=1.0),
        resultado=apuesta.resultado,
    )


@router.post("/apuestas", status_code=201)
def crear_apuesta(cuerpo: CuerpoApuesta) -> dict:
    conexion = db.conectar()
    try:
        apuesta = Apuesta(
            id=uuid4(), camino=cuerpo.camino, inicio=cuerpo.inicio, fin=cuerpo.fin,
            tope_horas=cuerpo.tope_horas, tope_plata=cuerpo.tope_plata, resultado=None,
        )
        db.crear_apuesta(conexion, apuesta)
        return {"id": str(apuesta.id)}
    finally:
        conexion.close()


@router.get("/apuestas", response_model=list[ApuestaVista])
def ver_apuestas() -> list[ApuestaVista]:
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        revisar_apuestas_vencidas(conexion, ahora)
        return [_a_vista(conexion, a, ahora) for a in db.listar_apuestas(conexion)]
    finally:
        conexion.close()


class CuerpoCerrarApuesta(BaseModel):
    resultado: str
    metrica_nueva: str | None = None


@router.post("/apuestas/{apuesta_id}/cerrar")
def cerrar_apuesta_endpoint(apuesta_id: str, cuerpo: CuerpoCerrarApuesta) -> dict:
    conexion = db.conectar()
    try:
        db.cerrar_apuesta(conexion, apuesta_id, cuerpo.resultado)
        return {"id": apuesta_id, "resultado": cuerpo.resultado}
    finally:
        conexion.close()


def revisar_apuestas_vencidas(conexion: sqlite3.Connection, ahora: datetime) -> None:
    """Al día 14: una Pregunta de tres salidas (sigue/pausa/extender). A
    los 60 días: «¿la volverías a hacer?». Cada una se pregunta una sola
    vez por apuesta — deduplicada por `campo` (ley 3: no se repite)."""
    for apuesta in db.listar_apuestas(conexion):
        dias = (ahora - apuesta.inicio).days
        if dias >= DIAS_PREGUNTA_SIGUE_O_PAUSA:
            campo = f"apuesta_dia14::{apuesta.id}"
            if db.pregunta_de_tema_campo(conexion, "_rumbo", campo) is None:
                db.crear_pregunta(
                    conexion,
                    Pregunta(
                        id=uuid4(), tema="_rumbo", campo=campo,
                        voz=f"La apuesta de {apuesta.camino} lleva 14 días: ¿sigue, pausa, o la extiendes con una métrica más estrecha?",
                        estado="pendiente", creada_en=ahora, disponible_desde=ahora,
                    ),
                )
        if dias >= DIAS_PREGUNTA_LA_VOLVERIAS_A_HACER:
            campo = f"apuesta_dia60::{apuesta.id}"
            if db.pregunta_de_tema_campo(conexion, "_rumbo", campo) is None:
                db.crear_pregunta(
                    conexion,
                    Pregunta(
                        id=uuid4(), tema="_rumbo", campo=campo,
                        voz=f"La apuesta de {apuesta.camino} cumple 60 días: ¿la volverías a hacer?",
                        estado="pendiente", creada_en=ahora, disponible_desde=ahora,
                    ),
                )


# --- R5.2 (forma S): latido -------------------------------------------


@router.get("/latido", response_model=list[reloj.LatidoVista])
def ver_latido() -> list[reloj.LatidoVista]:
    conexion = db.conectar()
    try:
        latidos = reloj.calcular_latido(conexion, datetime.now(timezone.utc))
        return [reloj.LatidoVista(pieza=l.pieza, ultimo_dato=l.ultimo_dato, callado_dias=l.callado_dias) for l in latidos]
    finally:
        conexion.close()


# --- R5.3: poda mensual --------------------------------------------------

DIAS_PODA = 30


def piezas_sin_uso(conexion: sqlite3.Connection, ahora: datetime, dias: int = DIAS_PODA) -> list[str]:
    """Qué partes del Rumbo no sumaron ninguna fila en los últimos
    `dias` — candidatas a que Remi proponga quitarlas. Nunca decide
    sola: solo las nombra, la `Pregunta` la hace quien llama."""
    desde = (ahora - timedelta(days=dias)).isoformat()
    consultas = {
        "apuestas": "SELECT COUNT(*) AS n FROM apuesta WHERE inicio >= ?",
        "caminos": "SELECT COUNT(*) AS n FROM analisis_camino WHERE creada_en >= ?",
        "pronosticos": "SELECT COUNT(*) AS n FROM pronostico WHERE creada_en >= ?",
        "propuestas": "SELECT COUNT(*) AS n FROM propuesta WHERE fecha >= ?",
    }
    sin_uso = []
    for pieza, sql in consultas.items():
        n = conexion.execute(sql, (desde,)).fetchone()["n"]
        if n == 0:
            sin_uso.append(pieza)
    return sin_uso


def proponer_poda(conexion: sqlite3.Connection, ahora: datetime) -> Pregunta | None:
    """Una `Pregunta` al mes (deduplicada por año-mes, ley 3) si hay
    alguna pieza sin uso. None si todas se usaron, o si ya se preguntó
    este mes."""
    sin_uso = piezas_sin_uso(conexion, ahora)
    if not sin_uso:
        return None
    campo = f"poda::{ahora:%Y-%m}"
    existente = db.pregunta_de_tema_campo(conexion, "_rumbo", campo)
    if existente is not None:
        return None
    lista = ", ".join(sin_uso)
    pregunta = Pregunta(
        id=uuid4(), tema="_rumbo", campo=campo,
        voz=f"No usaste {lista} en 30 días. ¿Las quito del Rumbo?",
        estado="pendiente", creada_en=ahora, disponible_desde=ahora,
    )
    db.crear_pregunta(conexion, pregunta)
    return pregunta


@router.get("/poda")
def ver_poda() -> dict:
    conexion = db.conectar()
    try:
        ahora = datetime.now(timezone.utc)
        pregunta = proponer_poda(conexion, ahora)
        return {"pregunta": pregunta.voz if pregunta else None}
    finally:
        conexion.close()

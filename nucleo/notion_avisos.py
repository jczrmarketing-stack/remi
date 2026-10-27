"""Puente Notion → Ventanita: los avisos de «Remi · CRM de vida».

Grok Bot (Remi) escribe en la base compartida filas con Tipo = Aviso y una
fecha en «Avisar el». Cada 5 minutos este módulo trae las que ya vencieron y
no están Hecha ni Soltada, las guarda en SQLite y la ventanita las pregunta
por `/notion/avisos/pendiente`. «Listo» pasa Estado a Hecha en Notion.

Decisión de Juan Camilo (15-oct-2026): esta base es la fuente compartida de
los avisos, así que acá Notion se lee, aunque el resto del espejo siga de ida
(`NOTION_VUELTA`). Lo único que se escribe de vuelta es Estado = Hecha.

Leyes:
- 3 · Sin cadena de culpa: «Ahora no» solo corre la hora 2 h; no deja
  contador ni marca de fallo (se guardan las salidas, nunca las respuestas).
  Si un aviso vuelve a salir, sale encogido: su paso mínimo, no lo mismo.
- 4 · Presión invertida: nada se marca urgente; la prioridad de Notion ni
  se lee.
- Presupuesto: máximo 5 salidas al día y 90 min entre ellas, y no de noche
  (la misma `noche` de avisos.py). Salvo Frente = Fiverr con «24h» en
  Notas: esas van fuera del presupuesto y a cualquier hora.

Solo se tocan los campos de la base de Notion; este módulo no lee ninguna
otra tabla de Remi (los espejos no leen nada más). Cuenta solo sus propias
salidas: los presupuestos de nudges y de avisos de reloj siguen siendo suyos.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import avisos
import db
import notion

BOGOTA = ZoneInfo("America/Bogota")

# La data source «Remi · CRM de vida». No es un secreto; se puede cambiar
# con NOTION_CRM_FUENTE_ID en nucleo/.env.
FUENTE_POR_DEFECTO = "df451f3c-49e4-435d-b75b-1cfdca18d9fe"
SEGUNDOS_ENTRE_SONDEOS = 5 * 60
MAXIMO_POR_DIA = 5
MINUTOS_ENTRE_AVISOS = 90
HORAS_AHORA_NO = 2

ESTADO_HECHA = {"Estado": {"status": {"name": "Hecha"}}}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS avisos_notion (
    pagina_id TEXT PRIMARY KEY,
    que TEXT NOT NULL,
    paso_minimo TEXT NOT NULL,
    exenta INTEGER NOT NULL DEFAULT 0,       -- Fiverr + «24h»: fuera del presupuesto
    avisar_el TEXT NOT NULL,                 -- cuándo venció (UTC)
    mostrar_desde TEXT NOT NULL,             -- «Ahora no» lo corre +2 h (UTC)
    mostrado_en TEXT,                        -- no nulo = está en pantalla sin responder
    respondida INTEGER NOT NULL DEFAULT 0,   -- «Listo»
    hecha_pendiente INTEGER NOT NULL DEFAULT 0  -- «Listo» sin escribir aún en Notion
);

CREATE TABLE IF NOT EXISTS avisos_notion_salidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pagina_id TEXT NOT NULL,
    salio_en TEXT NOT NULL,
    exenta INTEGER NOT NULL DEFAULT 0
);
"""


def _preparar(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA)


def fuente_id() -> str:
    return notion._ajuste("NOTION_CRM_FUENTE_ID") or FUENTE_POR_DEFECTO


# — Leer lo que trae Notion —


def _fecha_de(propiedad: dict[str, Any] | None) -> datetime | None:
    """«Avisar el» como instante. Solo día = el comienzo de ese día en Bogotá;
    con hora pero sin zona, la zona de la propiedad o Bogotá."""
    if not propiedad or not propiedad.get("date"):
        return None
    valor = propiedad["date"].get("start")
    if not valor:
        return None
    try:
        momento = datetime.fromisoformat(valor)
    except ValueError:
        return None
    if momento.tzinfo is None:
        nombre = propiedad["date"].get("time_zone")
        try:
            zona = ZoneInfo(nombre) if nombre else BOGOTA
        except Exception:
            zona = BOGOTA
        momento = momento.replace(tzinfo=zona)
    return momento.astimezone(timezone.utc)


def _es_exenta(frente: str | None, notas: str) -> bool:
    return frente == "Fiverr" and "24h" in notas.lower()


def _a_utc(texto: str) -> datetime:
    momento = datetime.fromisoformat(texto)
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def _filtro(ahora: datetime) -> dict[str, Any]:
    # Cota gruesa (mañana, Bogotá): Notion compara fechas, no instantes. Lo
    # fino —que ya sea la hora— se decide acá, con el instante real.
    manana = (ahora.astimezone(BOGOTA).date() + timedelta(days=1)).isoformat()
    return {
        "and": [
            {"property": "Tipo", "select": {"equals": "Aviso"}},
            {"property": "Estado", "status": {"does_not_equal": "Hecha"}},
            {"property": "Estado", "status": {"does_not_equal": "Soltada"}},
            {"property": "Avisar el", "date": {"on_or_before": manana}},
        ]
    }


# — El sondeo —


def _escribir_hecha(conexion: sqlite3.Connection, cliente: notion.Notion | None, pagina_id: str) -> None:
    """Estado → Hecha en Notion. Si no se puede (sin red, sin token), queda
    `hecha_pendiente` y el próximo sondeo lo reintenta; el aviso no vuelve a
    salir mientras tanto porque ya está respondido acá."""
    pendiente = 1
    if cliente is not None:
        try:
            cliente.actualizar_pagina(pagina_id, ESTADO_HECHA, version=notion.VERSION_FUENTES)
            pendiente = 0
        except httpx.HTTPStatusError as error:
            # 400/404: la fila ya no existe o no admite el cambio; reintentar no sirve.
            pendiente = 0 if error.response.status_code in (400, 404) else 1
        except httpx.HTTPError:
            pendiente = 1
    conexion.execute("UPDATE avisos_notion SET hecha_pendiente = ? WHERE pagina_id = ?", (pendiente, pagina_id))
    conexion.commit()


def sondear(conexion: sqlite3.Connection, cliente: notion.Notion, ahora: datetime) -> int:
    """Trae de Notion las filas vencidas y las deja en SQLite. Devuelve cuántas
    quedaron vencidas y abiertas. Levanta httpx.HTTPError si Notion no contesta;
    el hilo lo cuenta una vez y sigue."""
    _preparar(conexion)
    for fila in conexion.execute("SELECT pagina_id FROM avisos_notion WHERE hecha_pendiente = 1").fetchall():
        _escribir_hecha(conexion, cliente, fila["pagina_id"])

    vistas: set[str] = set()
    for pagina in cliente.consultar_fuente(fuente_id(), _filtro(ahora)):
        propiedades = pagina.get("properties", {})
        vence = _fecha_de(propiedades.get("Avisar el"))
        que = notion.leer_titulo(propiedades.get("Qué")).strip()
        if vence is None or vence > ahora or not que:
            continue
        paso = notion.leer_texto(propiedades.get("Paso mínimo")).strip()
        exenta = int(_es_exenta(notion.leer_seleccion(propiedades.get("Frente")), notion.leer_texto(propiedades.get("Notas"))))
        pagina_id = pagina["id"]
        vistas.add(pagina_id)
        if conexion.execute("SELECT 1 FROM avisos_notion WHERE pagina_id = ?", (pagina_id,)).fetchone() is None:
            conexion.execute(
                "INSERT INTO avisos_notion (pagina_id, que, paso_minimo, exenta, avisar_el, mostrar_desde) VALUES (?, ?, ?, ?, ?, ?)",
                (pagina_id, que, paso, exenta, vence.isoformat(), vence.isoformat()),
            )
        else:
            conexion.execute(
                "UPDATE avisos_notion SET que = ?, paso_minimo = ?, exenta = ?, avisar_el = ? WHERE pagina_id = ?",
                (que, paso, exenta, vence.isoformat(), pagina_id),
            )

    # Lo que en Notion ya está Hecho/Soltado, o dejó de estar vencido, deja de
    # existir acá (salvo un «Listo» que aún no se pudo escribir allá).
    for fila in conexion.execute("SELECT pagina_id, hecha_pendiente FROM avisos_notion").fetchall():
        if fila["pagina_id"] not in vistas and not fila["hecha_pendiente"]:
            conexion.execute("DELETE FROM avisos_notion WHERE pagina_id = ?", (fila["pagina_id"],))
    conexion.commit()
    return len(vistas)


# — Qué le toca a la ventanita —


@dataclass(frozen=True)
class Salida:
    id: str
    que: str
    paso_minimo: str
    encogido: bool


def _en_noche(ahora: datetime) -> bool:
    hora = ahora.astimezone(BOGOTA).hour
    inicio, fin = avisos.leer_config().noche
    if inicio > fin:  # 23 a 7 cruza medianoche
        return hora >= inicio or hora < fin
    return inicio <= hora < fin


def _presupuesto_ok(conexion: sqlite3.Connection, ahora: datetime) -> bool:
    if _en_noche(ahora):
        return False
    filas = conexion.execute(
        "SELECT salio_en FROM avisos_notion_salidas WHERE exenta = 0 ORDER BY salio_en DESC"
    ).fetchall()
    if not filas:
        return True
    hoy = ahora.astimezone(BOGOTA).date()
    de_hoy = sum(1 for f in filas if _a_utc(f["salio_en"]).astimezone(BOGOTA).date() == hoy)
    if de_hoy >= MAXIMO_POR_DIA:
        return False
    return ahora - _a_utc(filas[0]["salio_en"]) >= timedelta(minutes=MINUTOS_ENTRE_AVISOS)


def _salida(conexion: sqlite3.Connection, fila: sqlite3.Row) -> Salida:
    # Encogido = ya salió antes: la segunda vez va el paso mínimo, no lo mismo (ley 3).
    veces = conexion.execute(
        "SELECT COUNT(*) FROM avisos_notion_salidas WHERE pagina_id = ?", (fila["pagina_id"],)
    ).fetchone()[0]
    return Salida(id=fila["pagina_id"], que=fila["que"], paso_minimo=fila["paso_minimo"], encogido=veces > 1)


def pendiente(conexion: sqlite3.Connection, ahora: datetime) -> Salida | None:
    """El aviso que la ventanita debe mostrar ahora, o None. Si ya hay uno en
    pantalla sin responder, ese mismo (no es una salida nueva). Si no, saca uno
    solo si el presupuesto lo permite."""
    _preparar(conexion)
    ya = conexion.execute(
        "SELECT * FROM avisos_notion WHERE mostrado_en IS NOT NULL AND respondida = 0 ORDER BY mostrado_en LIMIT 1"
    ).fetchone()
    if ya is not None:
        return _salida(conexion, ya)

    candidatas = [
        f
        for f in conexion.execute("SELECT * FROM avisos_notion WHERE respondida = 0 AND mostrado_en IS NULL").fetchall()
        if _a_utc(f["mostrar_desde"]) <= ahora
    ]
    for fila in sorted(candidatas, key=lambda f: (-f["exenta"], f["avisar_el"])):
        if not fila["exenta"] and not _presupuesto_ok(conexion, ahora):
            continue
        marca = ahora.astimezone(timezone.utc).isoformat()
        conexion.execute("UPDATE avisos_notion SET mostrado_en = ? WHERE pagina_id = ?", (marca, fila["pagina_id"]))
        conexion.execute(
            "INSERT INTO avisos_notion_salidas (pagina_id, salio_en, exenta) VALUES (?, ?, ?)",
            (fila["pagina_id"], marca, fila["exenta"]),
        )
        conexion.commit()
        return _salida(conexion, fila)
    return None


def responder(
    conexion: sqlite3.Connection,
    pagina_id: str,
    respuesta: Literal["listo", "ahora_no"],
    ahora: datetime,
    cliente: notion.Notion | None,
) -> bool:
    """«Listo»: queda respondido y Estado pasa a Hecha en Notion. «Ahora no»:
    vuelve en 2 h, sin dejar rastro de que se pospuso. False si no existe."""
    _preparar(conexion)
    if conexion.execute("SELECT 1 FROM avisos_notion WHERE pagina_id = ?", (pagina_id,)).fetchone() is None:
        return False
    if respuesta == "listo":
        conexion.execute(
            "UPDATE avisos_notion SET respondida = 1, mostrado_en = NULL WHERE pagina_id = ?", (pagina_id,)
        )
        conexion.commit()
        _escribir_hecha(conexion, cliente, pagina_id)
    else:
        vuelve = (ahora + timedelta(hours=HORAS_AHORA_NO)).astimezone(timezone.utc).isoformat()
        conexion.execute(
            "UPDATE avisos_notion SET mostrado_en = NULL, mostrar_desde = ? WHERE pagina_id = ?", (vuelve, pagina_id)
        )
        conexion.commit()
    return True


# — El hilo —


def _ciclo(detener: threading.Event) -> None:
    ultimo_error = ""
    while not detener.is_set():
        tok = notion.token()
        if tok:
            conexion = db.conectar()
            try:
                sondear(conexion, notion.Notion(tok), datetime.now(timezone.utc))
                ultimo_error = ""
            except Exception as error:  # el sondeo nunca tumba el hilo
                mensaje = f"{type(error).__name__}: {error}"
                if mensaje != ultimo_error:  # una vez por falla distinta, no cada 5 min
                    print(f"[notion_avisos] no pude sondear ({mensaje})", file=sys.stderr, flush=True)
                    ultimo_error = mensaje
            finally:
                conexion.close()
        detener.wait(SEGUNDOS_ENTRE_SONDEOS)


_evento_detener: threading.Event | None = None


def arrancar_hilo() -> None:
    """Se llama desde el startup de servidor.py. REMI_NOTION_AVISOS=0 lo apaga
    (mismo patrón que REMI_TELEGRAM). Arranca aunque no haya token todavía: cada
    vuelta lo vuelve a mirar, así que guardarlo desde el panel basta."""
    global _evento_detener
    if os.environ.get("REMI_NOTION_AVISOS", "1") == "0" or _evento_detener is not None:
        return
    if notion.token() is None:
        print("[notion_avisos] sin NOTION_TOKEN: espero a que aparezca", file=sys.stderr, flush=True)
    _evento_detener = threading.Event()
    threading.Thread(target=_ciclo, args=(_evento_detener,), daemon=True, name="notion-avisos").start()


# — La puerta HTTP que lee la ventanita —

router = APIRouter(prefix="/notion/avisos", tags=["notion"])


class AvisoNotionVista(BaseModel):
    id: str
    que: str
    paso_minimo: str
    encogido: bool


class RespuestaAvisoNotion(BaseModel):
    respuesta: Literal["listo", "ahora_no"]


@router.get("/pendiente", response_model=AvisoNotionVista | None)
def aviso_pendiente() -> AvisoNotionVista | None:
    conexion = db.conectar()
    try:
        salida = pendiente(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()
    if salida is None:
        return None
    return AvisoNotionVista(id=salida.id, que=salida.que, paso_minimo=salida.paso_minimo, encogido=salida.encogido)


@router.post("/{pagina_id}/respuesta")
def responder_aviso(pagina_id: str, cuerpo: RespuestaAvisoNotion) -> dict[str, bool]:
    tok = notion.token()
    cliente = notion.Notion(tok) if tok else None
    conexion = db.conectar()
    try:
        if not responder(conexion, pagina_id, cuerpo.respuesta, datetime.now(timezone.utc), cliente):
            raise HTTPException(status_code=404, detail="no tengo ese aviso")
    finally:
        conexion.close()
    return {"ok": True}

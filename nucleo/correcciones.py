"""Aprender de las correcciones (Biblia Parte VI): Remi propone, nunca guarda solo.

Ley 3 en código: cero cadena de culpa. No confirmar no es un fallo, es
simplemente que la propuesta se descarta en silencio — nunca se repite ni
se insiste. La regla que se propone siempre sale de palabras que Juan
Camilo usó, nunca de una interpretación libre del modelo (por eso este
módulo no llama a ningún modelo: o cita lo que Remi dijo, o cita
literalmente lo que Juan Camilo escribió después de «acordate:»).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime

import boveda_git
import db
import sembrar_conocimiento

_PATRON_CORRECCION_LIBRE = re.compile(
    r"^(?:no asi no|yo no diria (?:eso|asi))\b"
)
_PATRON_ACORDATE = re.compile(r"^acordate:?\s+(.+)$", re.DOTALL | re.IGNORECASE)
_PATRON_SI = re.compile(r"^(?:si|sisi|dale|guardala|guardalo|anotalo|anotala|confirmo)\b")


def _normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.strip().lower())
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9:]+", " ", sin_tildes).strip()


def es_correccion(texto: str) -> bool:
    norm = _normalizar(texto)
    return bool(_PATRON_CORRECCION_LIBRE.match(norm) or norm.startswith("acordate"))


def es_confirmacion(texto: str) -> bool:
    return bool(_PATRON_SI.match(_normalizar(texto)))


def _contenido_acordate(texto: str) -> str | None:
    coincidencia = _PATRON_ACORDATE.match(texto.strip())
    return coincidencia.group(1).strip() if coincidencia else None


def _fichas_oficios() -> list[sembrar_conocimiento.Ficha]:
    carpeta = sembrar_conocimiento.carpeta_oficios()
    if not carpeta.is_dir():
        return []
    fichas = []
    for ruta in sorted(carpeta.glob("*.md")):
        ficha = sembrar_conocimiento.leer_ficha(ruta)
        if ficha is not None:
            fichas.append(ficha)
    return fichas


_OFICIO_POR_DEFECTO = "mi-voz"


def oficio_destino(texto: str) -> str:
    """El oficio cuyas `claves` más se repiten en `texto`. Sin ningún
    matcheo, «mi-voz»: la mayoría de correcciones sueltas («así no», «no
    diría eso») son de tono, no de un tema puntual."""
    palabras = set(_normalizar(texto).split())
    if not palabras:
        return _OFICIO_POR_DEFECTO
    mejor = _OFICIO_POR_DEFECTO
    mejor_puntaje = 0
    for ficha in _fichas_oficios():
        claves = [c.strip() for c in (ficha.claves or "").strip("[]").split(",") if c.strip()]
        puntaje = sum(
            1
            for clave in claves
            if any(palabra and palabra in _normalizar(clave) for palabra in palabras)
        )
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor = ficha.tema.removeprefix("oficio-")
    return mejor


def proponer_regla(texto_correccion: str, texto_anterior: str | None) -> tuple[str, str] | None:
    """(oficio, regla) citando SIEMPRE palabras reales: lo que Juan Camilo
    escribió después de «acordate:», o lo que Remi dijo y él rechazó. None
    si no hay nada seguro que citar (p. ej. «así no» sin ningún turno de
    Remi antes: no hay qué decir que «no se diga»)."""
    contenido = _contenido_acordate(texto_correccion)
    if contenido:
        return oficio_destino(contenido), contenido
    if texto_anterior and texto_anterior.strip():
        cita = texto_anterior.strip()
        return oficio_destino(cita), f"No decir: «{cita}»."
    return None


def proponer(texto: str, ahora: datetime) -> tuple[str, str] | None:
    """Si `texto` es una corrección, arma y deja pendiente (oficio, regla)
    en la conversación vigente (o abre una si hace falta), lista para que
    Remi la pregunte. None si no es una corrección, o si no hay manera
    segura de proponer sin inventar."""
    if not es_correccion(texto):
        return None
    conexion = db.conectar()
    try:
        vigente = db.conversacion_vigente(conexion, ahora)
        anterior = None
        if vigente is not None:
            turnos = db.turnos_de(conexion, vigente.id)
            anterior = next((t.texto for t in reversed(turnos) if t.rol == "remi"), None)
        propuesta = proponer_regla(texto, anterior)
        if propuesta is None:
            return None
        oficio, regla = propuesta
        conversacion_id = vigente.id if vigente is not None else db.guardar_turno(conexion, "juan", texto, ahora)
        db.proponer_correccion(conexion, conversacion_id, oficio, regla, ahora)
    finally:
        conexion.close()
    return oficio, regla


def revisar_confirmacion(texto: str, ahora: datetime) -> tuple[str, str] | None:
    """Si había una propuesta pendiente en la conversación vigente: la
    borra siempre (pendiente vive un solo turno más), y si `texto` la
    confirma, aplica la regla y devuelve (oficio, regla). None en
    cualquier otro caso — sin pendiente, o sin confirmación."""
    conexion = db.conectar()
    try:
        vigente = db.conversacion_vigente(conexion, ahora)
        if vigente is None:
            return None
        pendiente = db.propuesta_pendiente(conexion, vigente.id)
        if pendiente is None:
            return None
        db.borrar_propuesta(conexion, vigente.id)
    finally:
        conexion.close()

    if not es_confirmacion(texto):
        return None
    aplicar_regla(pendiente.oficio, pendiente.regla)
    return pendiente.oficio, pendiente.regla


ENCABEZADO_APRENDIDO = "## Aprendido de Juan Camilo"


def aplicar_regla(oficio: str, regla: str) -> None:
    """Agrega la línea al oficio, con el commit automático de la bóveda
    (snapshot antes y después — boveda_git.py)."""
    ruta = sembrar_conocimiento.carpeta_oficios() / f"{oficio}.md"
    boveda_git.snapshot_antes(f"aprender una regla en el oficio {oficio}")
    texto = ruta.read_text()
    if not texto.endswith("\n"):
        texto += "\n"
    if ENCABEZADO_APRENDIDO not in texto:
        texto += f"\n{ENCABEZADO_APRENDIDO}\n"
    texto += f"- {regla}\n"
    ruta.write_text(texto)
    boveda_git.snapshot_despues(f"oficio {oficio}: regla nueva de una corrección de Juan Camilo")

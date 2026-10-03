"""Precarga del proyecto activo (ARQUITECTURA-CEREBRO §4).

Antes de cada respuesta, el nivel 2 (el Estado) del proyecto activo entra al
contexto sin que el modelo tenga que llamar a `leer`: por eso cuando
preguntas por lo que estás haciendo, ya está — no hay que ir a buscarlo.

Proyecto activo, en este orden:
1. **Bloque abierto**: la sesión de trabajo abierta más reciente ya guarda,
   en `app_contexto`, el tema del proyecto activo al abrirse esa tarea
   (servidor.py, `POST /mensaje`).
2. **App en primer plano** (NSWorkspace): todavía no existe esa señal en el
   núcleo — es Fase F · 13, sin construir. Cuando exista, entra acá, entre
   el bloque abierto y el último tocado.
3. **El último libro tocado** (`trabajo_eventos`): lo mismo que usa
   `trabajo._libro_reciente()` para «¿dónde quedé?».

`estado_libro` se importa adentro de la función, no arriba del archivo: así
se evita el ciclo pensar → precarga → estado_libro → pensar.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

import db
import libros

ENCABEZADO = (
    "\n\nEsto es lo que estás haciendo ahora mismo (precargado, nivel 2 — "
    "ARQUITECTURA-CEREBRO §4; no hizo falta pedirlo con `leer`):\n"
)


def _tema_de_bloque_abierto() -> str | None:
    conexion = db.conectar()
    try:
        sesion_id = db.sesion_abierta_mas_reciente(conexion)
        if sesion_id is None:
            return None
        fila = conexion.execute(
            "SELECT app_contexto FROM sesiones WHERE id = ?", (str(sesion_id),)
        ).fetchone()
        tema = fila["app_contexto"] if fila else None
        return str(tema) if tema else None
    finally:
        conexion.close()


def _ultimo_tocado() -> str | None:
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT tema FROM trabajo_eventos WHERE tema IS NOT NULL ORDER BY fecha DESC LIMIT 1"
        ).fetchone()
        return str(fila["tema"]) if fila else None
    finally:
        conexion.close()


def proyecto_activo() -> tuple[str, str] | None:
    """(tema, razón) del proyecto activo, o None si no hay ninguna señal."""
    tema = _tema_de_bloque_abierto()
    if tema:
        return tema, "bloque_abierto"
    tema = _ultimo_tocado()
    if tema:
        return tema, "ultimo_tocado"
    return None


def _libro_de(tema: str) -> libros.Libro | None:
    return next((libro for libro in libros.listar() if libro.tema == tema), None)


def resumen_nivel2(tema: str) -> str | None:
    """El Estado del libro (Quedaste/Decisiones/Próximo paso), o su resumen
    si todavía no tiene Estado. None si no hay libro con ese tema."""
    import estado_libro  # import diferido: evita el ciclo con pensar.py

    libro = _libro_de(tema)
    if libro is None:
        return None
    estado = estado_libro.leer_estado(libro.archivo)
    if estado.strip():
        # De cuándo es (tarea 3 del 2-oct): el Estado puede ser de hace días.
        dia = datetime.fromtimestamp(libro.archivo.stat().st_mtime).date()
        return f"{libro.titulo} (Estado del {libros.fecha_corta(dia)}):\n{estado.strip()}"
    return f"{libro.titulo}: {libro.resumen}"


def bloque() -> tuple[str, str] | None:
    """(texto a sumar a las instrucciones, "<tema> razon=<razón>" para el
    log), o None si no hay nada que precargar."""
    activo = proyecto_activo()
    if activo is None:
        return None
    tema, razon = activo
    resumen = resumen_nivel2(tema)
    if resumen is None:
        return None
    return f"{ENCABEZADO}{resumen}\n", f"{tema} razon={razon}"


# — Los documentos de referencia (la Biblia de Remi), cuando la frase los nombra —
#
# Ni Haiku ni Sonnet bajaban la Biblia con `leer` aunque estuviera en el
# índice: el carácter ya trae un resumen de las seis leyes, contestaban con
# ese y decían que la habían leído (2-oct). Regla, sin IA: si la frase nombra
# un documento de referencia por una de sus claves, entra la sección que
# coincide con lo que se pregunta, literal, y siempre dónde está el resto.

ENCABEZADO_REFERENCIA = "\n\nDe {titulo} (`referencia/{archivo}` en la bóveda), lo que toca a esta pregunta, literal:\n"
PIE_REFERENCIA = "\nEl documento entero está en `referencia/{archivo}`: bájalo con `leer`{id} si hace falta más.\n"
MAXIMO_SECCION = 1800
_INICIO_SECCION = re.compile(r"^(LEY \d+ · .+|#{1,3} .+|PARTE [IVXL]+)$")
_SIN_PESO = {
    "que", "dice", "tu", "tus", "de", "del", "la", "el", "los", "las", "un", "una", "y", "o", "en", "es",
    "esta", "esto", "eso", "sobre", "como", "cual", "me", "mi", "lo", "le", "se", "por", "para", "con",
}


def _normal(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def _fichas(texto: str) -> set[str]:
    """Palabras con peso; los números van con dos cifras («ley 3» = «LEY 03»)."""
    palabras = re.findall(r"[a-z0-9ñ]+", _normal(texto))
    return {p.zfill(2) if p.isdigit() else p for p in palabras if p not in _SIN_PESO and len(p) > 1 or p.isdigit()}


def _secciones(cuerpo: str) -> list[tuple[str, str]]:
    """[(encabezado, texto)] partiendo en «LEY NN · …», «## …» y «PARTE …»."""
    secciones: list[tuple[str, list[str]]] = []
    for linea in cuerpo.splitlines():
        if _INICIO_SECCION.match(linea.strip()):
            secciones.append((linea.strip(), [linea]))
        elif secciones:
            secciones[-1][1].append(linea)
    return [(encabezado, "\n".join(lineas).strip()) for encabezado, lineas in secciones]


def _id_en_la_mente(tema: str, titulo: str) -> str:
    try:
        conexion = db.conectar()
        try:
            for memoria in db.memorias_por_tema(conexion, tema):
                if memoria.titulo == titulo:
                    return f" (id {str(memoria.id)[:8]})"
        finally:
            conexion.close()
    except Exception:  # noqa: BLE001 — sin base, el pie va sin id
        pass
    return ""


def de_referencia(frase: str) -> str | None:
    """El texto a sumar al contexto, o None si la frase no nombra ningún
    documento de referencia."""
    import sembrar_conocimiento  # import diferido, como estado_libro

    carpeta = sembrar_conocimiento.carpeta_referencia()
    if not carpeta.is_dir():
        return None
    fichas_frase = _fichas(frase)
    for ruta in sorted(carpeta.glob("*.md")):
        if libros.fuera_del_estante(ruta):
            continue
        ficha = sembrar_conocimiento.leer_ficha(ruta)
        if ficha is None:
            continue
        # Lo nombra por su primera clave («biblia»), no por cualquiera: «remi»
        # o «fases» también son claves y aparecen en casi toda frase.
        primera = re.findall(r"[a-z0-9ñ]+", _normal(ficha.claves or ""))[:1]
        if not primera or primera[0] not in fichas_frase:
            continue
        claves = _fichas(ficha.claves or "")
        preguntadas = fichas_frase - claves
        mejor: tuple[int, str] | None = None
        for encabezado, texto in _secciones(ficha.cuerpo):
            en_encabezado = preguntadas & _fichas(encabezado)
            if not en_encabezado:
                continue
            puntaje = 3 * len(en_encabezado) + len(preguntadas & _fichas(texto))
            if mejor is None or puntaje > mejor[0]:
                mejor = (puntaje, texto)
        partes = []
        if mejor is not None:
            partes.append(ENCABEZADO_REFERENCIA.format(titulo=ficha.titulo, archivo=ruta.name) + mejor[1][:MAXIMO_SECCION])
        partes.append(PIE_REFERENCIA.format(archivo=ruta.name, id=_id_en_la_mente(ficha.tema, ficha.titulo)))
        return "".join(partes)
    return None


# — Ambigüedad: preguntar, no adivinar (2-oct) —
#
# El caso real: a las 23:36 entraron commits en malik-gestion desde otra
# sesión de Claude Code; Juan Camilo preguntó en la ventanita «¿esta completo
# cada paso de la biblia?» y la precarga, por «lo último tocado», le dio
# Malik — contestó de Malik. Regla sin IA: si la frase no tiene tema propio,
# nombra algo que existe en más de un libro, no hay un bloque abierto en la
# ventanita y lo último tocado es un commit o una sesión de hace menos de
# MINUTOS_RECIENTE, no se decide sola: se dan los dos candidatos.

MINUTOS_RECIENTE = 15
COMPARTIDOS = {
    "biblia", "plan", "encargo", "panel", "ventanita", "bitacora", "camino", "fase", "fases",
    "contrato", "prompt", "estado", "mockup", "pantalla", "lienzo", "bot", "repo",
}
LINEA_DE_DUDA = "\n\nNo sé si habla de {x} o de {y}: pregunta cuál en una frase antes de contestar.\n"
# En un encargo la duda no se convierte en pregunta (F2.2b y la revisión del
# 3-oct): el encargo sale igual, con el proyecto marcado.
LINEA_DE_DUDA_ENCARGO = (
    "\n\nNo sé si es de {x} o de {y}: arma el encargo igual y marca el proyecto como "
    "«(a confirmar: {x} o {y})»; la pregunta va en la línea FALTA.\n"
)


def tema_dudoso(frase: str, ahora: datetime) -> tuple[str, str] | None:
    """(lo último tocado, el anterior distinto) si hay que preguntar; si no, None."""
    import temas  # diferido, como estado_libro

    if temas.tema_de_texto(frase) is not None:
        return None
    if not (_fichas(frase) & COMPARTIDOS):
        return None
    if _tema_de_bloque_abierto():
        return None
    conexion = db.conectar()
    try:
        filas = conexion.execute(
            "SELECT tema, fecha FROM trabajo_eventos WHERE tema IS NOT NULL ORDER BY fecha DESC LIMIT 200"
        ).fetchall()
    finally:
        conexion.close()
    if not filas:
        return None
    ultimo = filas[0]
    if ahora - datetime.fromisoformat(ultimo["fecha"]) > timedelta(minutes=MINUTOS_RECIENTE):
        return None
    otro = next((fila["tema"] for fila in filas if fila["tema"] != ultimo["tema"]), None)
    if otro is None:
        return None
    return str(ultimo["tema"]), str(otro)


def linea_de_duda(candidatos: tuple[str, str], encargo: bool = False) -> str:
    def titulo(tema: str) -> str:
        libro = _libro_de(tema)
        return libro.titulo if libro is not None else tema

    plantilla = LINEA_DE_DUDA_ENCARGO if encargo else LINEA_DE_DUDA
    return plantilla.format(x=titulo(candidatos[0]), y=titulo(candidatos[1]))

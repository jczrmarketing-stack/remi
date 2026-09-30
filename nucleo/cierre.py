"""Al cerrar Claude Code, un episodio y el Estado del libro.

El transcript se lee en esta máquina: al núcleo solo le llega la ruta.
Ollama resume; si no está, Haiku; si ninguno contesta, el episodio sale
igual, corto, con un primer paso de cinco minutos.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import db
import episodios
import estado_libro
import libros
import pensar
from modelos import Memoria

BOGOTA = ZoneInfo("America/Bogota")
ORDEN = ("Qué se hizo", "Decisiones", "Pendientes", "Primer paso de mañana")
INSTRUCCIONES = (
    "Te paso el final de una sesión de trabajo. Devolvé SOLO estas secciones, "
    "en español, sin exclamaciones y sin reproche:\n"
    "## Qué se hizo\n"
    "(dos o tres frases)\n"
    "## Decisiones\n"
    "(lo que quedó decidido, o «ninguna nueva»)\n"
    "## Pendientes\n"
    "(lo que sigue abierto)\n"
    "## Primer paso de mañana\n"
    "(una sola acción de cinco minutos)\n"
)


def guardar(ruta: str, datos: dict[str, object], ahora: datetime) -> Path | None:
    """Escribe el episodio y, si hay libro, su Estado. Devuelve la nota, o
    None si la sesión no tuvo charla: abrir y cerrar Claude (o un `claude -p`
    de un script) no deja un episodio vacío ni pisa el Estado del libro con
    «La sesión cerró» (ARQUITECTURA §6: lo trivial no deja episodio; visto el
    30/09 al revisar 3d)."""
    libro = libros.por_ruta(ruta)
    tema = libro.tema if libro else (episodios.slug(Path(ruta).name) or "sesion")
    titulo_libro = libro.titulo if libro else (Path(ruta).name or "sesión")
    ruta_transcript = str(datos.get("transcript_path") or "")
    charla = leer_charla(ruta_transcript)
    if not charla.strip():
        motivo = "sin transcript_path" if not ruta_transcript else "transcript sin turnos legibles"
        print(
            f"[cierre] sesión sin charla en {tema} ({motivo}, ruta={ruta_transcript or '—'}): no deja episodio",
            file=sys.stderr,
        )
        return None
    secciones = redactar(f"Proyecto: {titulo_libro}\n\n{charla}") if charla.strip() else None
    por = "modelo" if secciones else "plano"
    if secciones is None:
        secciones = plano(charla, titulo_libro)
    cuerpo = _render(secciones)
    local = ahora.astimezone(BOGOTA)
    titulo = episodios._recortar(episodios._una_linea(secciones["Qué se hizo"]), 80) or f"Sesión {tema}"
    resumen = episodios._recortar(
        episodios._una_linea(secciones["Primer paso de mañana"]), 240
    ) or "Retomar el hilo, cinco minutos."
    carpeta = episodios.carpeta_episodios()
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = episodios._ruta_libre(carpeta, f"{local:%Y-%m-%d}-{episodios.slug(titulo)}")
    destino.write_text(
        f'---\ntitulo: "{episodios._una_linea(titulo)}"\ntema: {tema}\n'
        f'resumen: "{episodios._una_linea(resumen)}"\n---\n\n{cuerpo}'
    )
    _memoria(titulo, resumen, tema, ahora, cuerpo, por)
    if libro is not None:
        estado_libro.escribir_estado(libro.archivo, _a_estado(secciones))
        _cursor(libro.tema, ahora)
    print(f"[cierre] {destino.name} · tema={tema} · {por}", file=sys.stderr)
    return destino


def redactar(pedido: str) -> dict[str, str] | None:
    """Las cuatro secciones, o None si no hubo respuesta usable."""
    modelo = pensar._ajuste("REMI_OLLAMA_MODELO", pensar.OLLAMA_MODELO_POR_DEFECTO)
    try:
        datos = pensar._llamar_ollama(modelo, INSTRUCCIONES, pedido[-8000:])
        pensado = pensar._leer_respuesta_venice(datos, modelo, 0, proveedor="ollama")
        if pensado:
            secciones = secciones_de(pensado.paso_minimo)
            if secciones:
                return secciones
    except Exception as error:  # noqa: BLE001 — Ollama caído cae a Haiku
        print(f"[cierre] Ollama no está ({type(error).__name__}): pruebo con Haiku", file=sys.stderr)
    try:
        pensado = pensar._una_llamada_claude(
            pensar.MODOS["rapido"], pedido[-8000:], INSTRUCCIONES, []
        )
    except Exception as error:  # noqa: BLE001 — sin modelo queda el episodio plano
        print(f"[cierre] Haiku no contestó ({type(error).__name__})", file=sys.stderr)
        return None
    if pensado is None:
        return None
    return secciones_de(pensado.paso_minimo)


def secciones_de(texto: str) -> dict[str, str] | None:
    actual: str | None = None
    buf: dict[str, list[str]] = {nombre: [] for nombre in ORDEN}
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("## "):
            nombre = limpia[3:].strip()
            actual = nombre if nombre in buf else None
            continue
        if actual is not None:
            buf[actual].append(linea)
    resultado = {nombre: "\n".join(lineas).strip() for nombre, lineas in buf.items()}
    if not resultado["Qué se hizo"] or not resultado["Primer paso de mañana"]:
        return None
    if not resultado["Decisiones"]:
        resultado["Decisiones"] = "ninguna nueva"
    if not resultado["Pendientes"]:
        resultado["Pendientes"] = "ninguno anotado"
    return resultado


def plano(charla: str, titulo: str) -> dict[str, str]:
    hecho = ""
    for linea in reversed(charla.splitlines()):
        if linea.startswith("Juan:"):
            hecho = " ".join(linea[5:].split())[:180]
            break
    return {
        "Qué se hizo": hecho or "La sesión cerró.",
        "Decisiones": "ninguna anotada",
        "Pendientes": f"seguir en {titulo}",
        "Primer paso de mañana": "retomar el hilo, cinco minutos",
    }


def leer_charla(ruta: str) -> str:
    """El final del transcript, en texto. Vacío si no está o no se puede leer."""
    if not ruta:
        return ""
    path = Path(ruta)
    try:
        if not path.is_file():
            return ""
        tamano = path.stat().st_size
        with path.open("rb") as archivo:
            if tamano > 1_500_000:
                archivo.seek(tamano - 1_500_000)
                archivo.readline()
            datos = archivo.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    trozos: list[str] = []
    for linea in datos.splitlines():
        try:
            obj = json.loads(linea)
        except json.JSONDecodeError:
            continue
        tipo = obj.get("type")
        if tipo not in {"user", "assistant"}:
            continue
        mensaje = obj.get("message")
        if not isinstance(mensaje, dict):
            continue
        texto = _texto_de(mensaje.get("content"))
        if not texto:
            continue
        if len(texto) > 1500:
            texto = texto[:1499].rsplit(" ", 1)[0] + "…"
        quien = "Juan" if tipo == "user" else "Claude"
        trozos.append(f"{quien}: {texto}")
    return "\n\n".join(trozos[-40:])[-12000:]


def _texto_de(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    partes: list[str] = []
    for bloque in content:
        if isinstance(bloque, str):
            partes.append(bloque.strip())
        elif isinstance(bloque, dict) and bloque.get("type") == "text":
            partes.append(str(bloque.get("text") or "").strip())
    return "\n".join(parte for parte in partes if parte)


def _render(secciones: dict[str, str]) -> str:
    return "".join(f"## {nombre}\n\n{secciones[nombre].strip()}\n\n" for nombre in ORDEN)


def _a_estado(secciones: dict[str, str]) -> str:
    quedaste = " ".join(secciones["Qué se hizo"].split())[:180] or "la sesión cerró"
    decisiones = " ".join(secciones["Decisiones"].split())[:180] or "ninguna nueva"
    paso = " ".join(secciones["Primer paso de mañana"].split())[:180] or "retomar el hilo, cinco minutos"
    return f"Quedaste: {quedaste}\nDecisiones: {decisiones}\nPróximo paso: {paso}"


def _memoria(titulo: str, resumen: str, tema: str, ahora: datetime, cuerpo: str, por: str) -> None:
    try:
        memoria = Memoria(
            id=uuid4(),
            titulo=titulo,
            resumen=resumen,
            tema=tema,
            fecha=ahora,
            cuerpo=cuerpo,
            fuente="conversacion",
            claves=None,
            nivel=2,
        )
    except Exception as error:  # noqa: BLE001 — un título raro no deja la sesión sin episodio
        print(f"[cierre] la memoria no entró ({type(error).__name__})", file=sys.stderr)
        return
    conexion = db.conectar()
    try:
        db.guardar_memoria(conexion, memoria)
    finally:
        conexion.close()


def _cursor(tema: str, ahora: datetime) -> None:
    """El cierre cuenta como la actualización de la ventana de 10 min."""
    conexion = db.conectar()
    try:
        conexion.execute(
            """
            INSERT INTO trabajo_estado_en (tema, fecha) VALUES (?, ?)
            ON CONFLICT(tema) DO UPDATE SET fecha = excluded.fecha
            """,
            (tema, ahora.isoformat()),
        )
        conexion.commit()
    finally:
        conexion.close()

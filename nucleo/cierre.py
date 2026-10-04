"""Al cerrar Claude Code, un episodio y el Estado del libro.

El transcript se lee en esta máquina: al núcleo solo le llega la ruta.
Ollama resume; si no está, Haiku; si ninguno contesta, el episodio sale
igual, corto, con un primer paso de cinco minutos.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import boveda_git
import db
import episodios
import estado_libro
import experiencia
import libros
import pensar
from modelos import Memoria

BOGOTA = ZoneInfo("America/Bogota")
ORDEN = ("Qué se hizo", "Decisiones", "Pendientes", "Primer paso de mañana")
INSTRUCCIONES = (
    "Te paso el final de una sesión de trabajo. Devuelve SOLO estas secciones, "
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

# — El libro de errores → T8: lecciones en remi-mente/experiencia/ —
# Si el transcript de la sesión dice, tal cual, que un problema se resolvió
# (o un commit de la sesión empieza con fix/arregl/corrig), queda una
# lección (`experiencia.Leccion`, clase «error») con sus cinco secciones.
PATRON_ERROR = re.compile(r"la causa era|se arregl[oó]|fallaba porque", re.IGNORECASE)
INSTRUCCIONES_ERROR = (
    "Te paso el final de una sesión donde se resolvió un problema técnico. Saca SOLO estas "
    "cinco secciones, con datos que estén literalmente en la charla — si alguna no aparece "
    "con claridad, escribe «sin dato» en esa sección en vez de inventar. La excepción es "
    "«Lo que creímos»: si NO hubo una pista falsa, dejala completamente vacía (ni «sin dato» "
    "ni nada) — no toda sesión se fue por el lado equivocado:\n"
    "## Síntoma\n(qué fallaba, tal como se ve)\n"
    "## Lo que creímos\n(la pista falsa que se siguió antes de la causa real; vacía si no hubo)\n"
    "## Causa real\n(la causa real, tal como se explica)\n"
    "## Cura\n(qué se hizo para arreglarlo)\n"
    "## Cómo verlo antes\n(qué mirar la próxima vez para no perder tiempo con esto)\n"
)


def hay_problema_resuelto(charla: str) -> bool:
    return bool(PATRON_ERROR.search(charla))


def hay_evidencia_de_arreglo(charla: str, mensajes_de_commits: list[str]) -> bool:
    """T8.2: la frase de siempre, o un commit de la sesión que empieza con
    fix/arregl/corrig — dos señales, no solo la charla."""
    return hay_problema_resuelto(charla) or any(
        experiencia.commit_es_arreglo(mensaje) for mensaje in mensajes_de_commits
    )


def redactar_error(charla: str, titulo_libro: str) -> dict[str, str] | None:
    """Las cinco secciones del error, o None si no se pudo sacar nada real."""
    pedido = f"Proyecto: {titulo_libro}\n\n{charla}"[-8000:]
    try:
        pensado = pensar._una_llamada_claude(pensar.MODOS["rapido"], pedido, INSTRUCCIONES_ERROR, [])
    except Exception as error:  # noqa: BLE001 — sin Haiku, no hay lección esta vez
        print(f"[cierre] error: Haiku no contestó ({type(error).__name__})", file=sys.stderr)
        return None
    if pensado is None:
        return None
    return secciones_error_de(pensado.paso_minimo)


def secciones_error_de(texto: str) -> dict[str, str] | None:
    nombres = experiencia.SECCIONES_ERROR
    actual: str | None = None
    buf: dict[str, list[str]] = {nombre: [] for nombre in nombres}
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("## "):
            nombre = limpia[3:].strip()
            actual = nombre if nombre in buf else None
            continue
        if actual is not None:
            buf[actual].append(linea)
    resultado = {nombre: "\n".join(lineas).strip() for nombre, lineas in buf.items()}
    for nombre in nombres:
        if nombre != "Lo que creímos" and not resultado[nombre]:
            resultado[nombre] = "sin dato"
    obligatorias = [n for n in nombres if n != "Lo que creímos"]
    if all(resultado[nombre].lower() == "sin dato" for nombre in obligatorias):
        return None  # no sacó nada real: mejor ninguna lección que una vacía
    return resultado


def escribir_episodio_error(
    tema: str, titulo_libro: str, secciones: dict[str, str], ahora_local: datetime, donde: str = ""
) -> Path:
    sintoma = episodios._una_linea(secciones["Síntoma"])
    leccion = experiencia.Leccion(
        titulo=episodios._recortar(f"Error en {titulo_libro}: {sintoma}", 80),
        tema=tema,
        resumen=episodios._recortar(episodios._una_linea(secciones["Causa real"]), 240),
        clase="error",
        donde=donde or tema,
        secciones=secciones,
        fuente="claude-code",
    )
    destino, _es_nueva = experiencia.escribir(leccion, datetime.now(timezone.utc))
    return destino


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
    titulo = episodios._recortar(_primera_frase(secciones["Qué se hizo"]), 80) or f"Sesión {tema}"
    resumen = episodios._recortar(
        _primera_frase(secciones["Primer paso de mañana"]), 240
    ) or "Retomar el hilo, cinco minutos."
    mensajes_commits = _mensajes_de_commits_de_la_sesion(tema, datos, ahora)
    # T8.4: la nota sin IA — a las 48 h, noche.py revisa si hubo que
    # arreglarla (ver `experiencia.revisar_resultados_pendientes`).
    resultado = experiencia.resultado_de_sesion(
        hubo_commits=bool(mensajes_commits), pruebas="sin-correr", fix_en_48h=False
    )
    carpeta = episodios.carpeta_episodios()
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = episodios._ruta_libre(carpeta, f"{local:%Y-%m-%d}-{episodios.slug(titulo)}")
    boveda_git.snapshot_antes(f"escribir el episodio {destino.name}")
    destino.write_text(
        f'---\ntitulo: "{episodios._una_linea(titulo)}"\ntema: {tema}\n'
        f'resumen: "{episodios._una_linea(resumen)}"\nresultado: {resultado}\n---\n\n{cuerpo}'
    )
    if libro is not None:
        estado_libro.escribir_estado(libro.archivo, _a_estado(secciones))
    boveda_git.snapshot_despues(
        _mensaje_del_cierre(destino, f"al cerrar sesión en {tema}")
        + (f"; Estado de {libro.archivo.name} actualizado" if libro is not None else "")
    )
    _memoria(titulo, resumen, tema, ahora, cuerpo, por)
    if libro is not None:
        _cursor(libro.tema, ahora)
    print(f"[cierre] {destino.name} · tema={tema} · {por}", file=sys.stderr)
    if hay_evidencia_de_arreglo(charla, mensajes_commits):
        secciones_error = redactar_error(charla, titulo_libro)
        if secciones_error is not None:
            error_destino = escribir_episodio_error(tema, titulo_libro, secciones_error, local, donde=ruta)
            print(f"[cierre] {error_destino.name} · lección (experiencia/)", file=sys.stderr)
    return destino


def _mensajes_de_commits_de_la_sesion(tema: str, datos: dict[str, object], ahora: datetime) -> list[str]:
    """Los commits de este tema desde que arrancó esta sesión de Claude
    Code hasta que cerró — para `hay_evidencia_de_arreglo` (T8.2)."""
    sesion = str(datos.get("session_id") or "").strip()
    if not sesion:
        return []
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT inicio FROM trabajo_claude WHERE session_id = ?", (sesion,)
        ).fetchone()
        if fila is None:
            return []
        filas = conexion.execute(
            "SELECT mensaje FROM trabajo_commits WHERE tema = ? AND fecha >= ? AND fecha <= ?",
            (tema, fila["inicio"], ahora.isoformat()),
        ).fetchall()
        return [f["mensaje"] for f in filas]
    finally:
        conexion.close()


def redactar(pedido: str) -> dict[str, str] | None:
    """Las cuatro secciones, o None si no hubo respuesta usable. Va por la
    trastienda de `config/motores.json` (groq → openrouter → ollama, por
    defecto): esto es tarea de fondo, nunca la charla."""
    pensado = pensar.pensar_con_trastienda(
        pedido[-8000:], INSTRUCCIONES, aceptar=lambda p: secciones_de(p.paso_minimo) is not None
    )
    return secciones_de(pensado.paso_minimo) if pensado else None


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


_FIN_DE_FRASE = re.compile(r"[.!?](?:\s|$)")


def _primera_frase(texto: str) -> str:
    """La primera frase completa de una sección, en una sola línea.

    El modelo a veces contesta más de una frase, o deja una segunda opción
    suelta («estudio: o freno:») sin puntuar como frase — tomar solo la
    primera evita que esa cola entre al título o al resumen. Sin un punto
    claro, devuelve el texto entero (una sección corta de una sola frase no
    tiene por qué llevar punto final)."""
    una_linea = episodios._una_linea(texto)
    encontrado = _FIN_DE_FRASE.search(una_linea)
    if encontrado is None:
        return una_linea
    return una_linea[: encontrado.end()].strip()


def _render(secciones: dict[str, str]) -> str:
    return "".join(f"## {nombre}\n\n{secciones[nombre].strip()}\n\n" for nombre in ORDEN)


def _a_estado(secciones: dict[str, str]) -> str:
    quedaste = episodios._recortar(_primera_frase(secciones["Qué se hizo"]), 180) or "la sesión cerró"
    decisiones = episodios._recortar(_primera_frase(secciones["Decisiones"]), 180) or "ninguna nueva"
    paso = episodios._recortar(_primera_frase(secciones["Primer paso de mañana"]), 180) or "retomar el hilo, cinco minutos"
    return f"Quedaste: {quedaste}\nDecisiones: {decisiones}\nPróximo paso: {paso}"


def _mensaje_del_cierre(destino: Path, cuando: str) -> str:
    """F3.5: el commit de la bóveda nombra el episodio solo si quedó dentro
    de ESA bóveda. Con REMI_BOVEDA y REMI_CONOCIMIENTO en carpetas distintas
    (lo que pasaba en la suite), el episodio caía afuera y el commit lo
    nombraba igual — en `git log` parecía escrito y no estaba en disco."""
    raiz = boveda_git.raiz()
    try:
        adentro = destino.exists() and raiz in destino.resolve().parents
    except OSError:
        adentro = False
    if adentro:
        return f"bóveda: episodio {destino.name} {cuando}"
    return f"bóveda: {cuando} (el episodio quedó fuera de esta bóveda: {destino.parent})"


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
            tipo=None,
        )
    except Exception as error:  # noqa: BLE001 — un título raro no deja la sesión sin episodio
        print(f"[cierre] la memoria no entró ({type(error).__name__})", file=sys.stderr)
        return
    conexion = db.conectar()
    try:
        db.guardar_memoria(conexion, memoria)
    finally:
        conexion.close()


# — T9.5: lo que se habla con Remi también queda —


def _conversacion_sustancial(turnos: list[db.Turno]) -> bool:
    """Mismo criterio que ofrecer guardar una charla larga (ARQUITECTURA
    §6, episodios.LARGO_MINIMO): trivial no deja episodio."""
    return sum(len(t.texto) for t in turnos) >= episodios.LARGO_MINIMO


def _escribir_episodio_de_conversacion(conversacion_id: str, turnos: list[db.Turno], ahora: datetime) -> Path:
    import temas

    charla = "\n".join(f"{'Juan' if t.rol == 'juan' else 'Remi'}: {t.texto}" for t in turnos)
    texto_de_juan = "\n".join(t.texto for t in turnos if t.rol == "juan")
    tema = temas.tema_de_texto(texto_de_juan)
    libro = next((l for l in libros.listar() if l.tema == tema), None) if tema else None
    titulo_libro = libro.titulo if libro else "una charla"

    secciones = redactar(f"Conversación con Remi, sobre {titulo_libro}.\n\n{charla}")
    por = "modelo" if secciones else "plano"
    if secciones is None:
        secciones = plano(charla, titulo_libro)
    cuerpo = _render(secciones)
    local = ahora.astimezone(BOGOTA)
    titulo = episodios._recortar(_primera_frase(secciones["Qué se hizo"]), 80) or "Conversación con Remi"
    resumen = episodios._recortar(
        _primera_frase(secciones["Primer paso de mañana"]), 240
    ) or "Retomar el hilo, cinco minutos."

    carpeta = episodios.carpeta_episodios()
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = episodios._ruta_libre(carpeta, f"{local:%Y-%m-%d}-charla-{episodios.slug(titulo)}")
    boveda_git.snapshot_antes(f"escribir el episodio de la conversación {destino.name}")
    destino.write_text(
        f'---\ntitulo: "{episodios._una_linea(titulo)}"\ntema: {tema or "charla"}\n'
        f'resumen: "{episodios._una_linea(resumen)}"\nfuente: conversacion\n---\n\n{cuerpo}'
    )
    if libro is not None:
        estado_libro.escribir_estado(libro.archivo, _a_estado(secciones))
    boveda_git.snapshot_despues(
        _mensaje_del_cierre(destino, "al cerrar una conversación")
        + (f"; Estado de {libro.archivo.name} actualizado" if libro is not None else "")
    )
    _memoria(titulo, resumen, tema or "charla", ahora, cuerpo, por)

    conexion = db.conectar()
    try:
        db.poner_titulo(conexion, conversacion_id, titulo)
        if tema:
            db.poner_tema(conexion, conversacion_id, tema)
    finally:
        conexion.close()
    return destino


def cerrar_conversaciones_inactivas(ahora: datetime) -> int:
    """T9.5: una conversación de la ventanita o Telegram, 60 min sin
    turnos, con sustancia, deja su episodio (y el Estado de su proyecto,
    si lo nombró) — igual que una sesión de Claude Code, nunca a mitad de
    un turno. Corre en la consolidación de la noche. Devuelve cuántos
    episodios dejó."""
    conexion = db.conectar()
    try:
        ids = db.conversaciones_para_cerrar(conexion, ahora)
        turnos_por_id = {id_: db.turnos_de(conexion, id_) for id_ in ids}
    finally:
        conexion.close()

    cerradas = 0
    for conversacion_id, turnos in turnos_por_id.items():
        # F3.5: se marca pase lo que pase. Si escribir el episodio falla a la
        # mitad (el Estado ya escrito, el archivo no), la próxima corrida la
        # volvía a cerrar — otro Estado, otra paráfrasis, otro commit.
        try:
            if _conversacion_sustancial(turnos):
                _escribir_episodio_de_conversacion(conversacion_id, turnos, ahora)
                cerradas += 1
        except Exception as error:  # noqa: BLE001 — una conversación rota no frena las demás
            print(
                f"[cierre] la conversación {conversacion_id} no dejó episodio ({type(error).__name__}: {error})",
                file=sys.stderr,
            )
        finally:
            conexion = db.conectar()
            try:
                db.marcar_episodio_hecho(conexion, conversacion_id)
            finally:
                conexion.close()
    return cerradas


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

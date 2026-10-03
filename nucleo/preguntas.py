"""T3 (fase Q, Biblia v3.8): Remi pregunta lo que le falta — nunca un
humano, nunca un chat, nunca un modelo. Seis detectores, sin IA, sobre el
estado real de los libros; un escritor por campo, cada uno con su commit
en la bóveda (boveda_git) cuando toca un archivo.

Una pregunta por `(tema, campo)`: si ya existe (en cualquier estado), no
se duplica. Respondida no vuelve. `despues` no vuelve hasta el día
siguiente y no deja ningún contador (ley 3).
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import boveda_git
import clasificar
import db
import entregas
import iniciativa
import libros
from modelos import Pregunta

# «En el aire» (T3.5, el patrón de correcciones.py): un singleton, no por
# conversación — la ventanita es de una sola persona y la mayoría de los
# mensajes ni siquiera abren una conversación (solo lo hace pensar.py).
ESQUEMA_EN_EL_AIRE = """
CREATE TABLE IF NOT EXISTS pregunta_en_el_aire (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    pregunta_id TEXT NOT NULL
);
"""


def _preparar_en_el_aire(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA_EN_EL_AIRE)


def marcar_en_el_aire(conexion: sqlite3.Connection, pregunta_id: UUID) -> None:
    _preparar_en_el_aire(conexion)
    conexion.execute(
        "INSERT INTO pregunta_en_el_aire (id, pregunta_id) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET pregunta_id = excluded.pregunta_id",
        (str(pregunta_id),),
    )
    conexion.commit()


def en_el_aire(conexion: sqlite3.Connection) -> Pregunta | None:
    _preparar_en_el_aire(conexion)
    fila = conexion.execute("SELECT pregunta_id FROM pregunta_en_el_aire WHERE id = 1").fetchone()
    return db.leer_pregunta(conexion, UUID(fila["pregunta_id"])) if fila else None


def borrar_en_el_aire(conexion: sqlite3.Connection) -> None:
    _preparar_en_el_aire(conexion)
    conexion.execute("DELETE FROM pregunta_en_el_aire WHERE id = 1")
    conexion.commit()


def es_arranque_cierre_o_pregunta(texto: str) -> bool:
    if "?" in texto or "¿" in texto:
        return True
    return clasificar.clasificar(texto) in ("hoy", "hecha", "pregunta")


def preguntar_en_voz(conexion: sqlite3.Connection, tema: str | None, ahora: datetime) -> Pregunta | None:
    """Al abrir un bloque de ese proyecto: si hay algo pendiente y el
    presupuesto de silencio de `iniciativa.py` lo permite, la deja «en el
    aire» (una sola) y gasta un cupo del día — sin crear un Nudge nuevo,
    `iniciativa_nudges` solo registra el gasto."""
    if tema is None:
        return None
    sincronizar(conexion, ahora)
    pendientes = db.listar_preguntas_pendientes(conexion, ahora, tema, limite=1)
    iniciativa._preparar(conexion)
    if not pendientes or not iniciativa._presupuesto_ok(conexion, ahora):
        return None
    pregunta = pendientes[0]
    iniciativa.registrar(conexion, uuid4(), "ritual", ahora)
    marcar_en_el_aire(conexion, pregunta.id)
    return pregunta


# — T3.6: por Telegram, una vez al día como mucho —

ESQUEMA_TELEGRAM_DIA = """
CREATE TABLE IF NOT EXISTS pregunta_telegram_dia (
    dia TEXT PRIMARY KEY
);
"""


def avisar_por_telegram_si_toca(conexion: sqlite3.Connection, ahora: datetime) -> Pregunta | None:
    """La misma pregunta puede salir por el bot — una vez al día como
    mucho (`noche.py` la llama en su corrida de las 4:00). La respuesta
    llega por el mismo chat: `telegram._procesar_texto` ya pasa cualquier
    texto por `/mensaje`, que reconoce la pregunta «en el aire»."""
    import telegram

    sincronizar(conexion, ahora)
    conexion.executescript(ESQUEMA_TELEGRAM_DIA)
    dia = ahora.date().isoformat()
    ya_hoy = conexion.execute(
        "SELECT 1 FROM pregunta_telegram_dia WHERE dia = ?", (dia,)
    ).fetchone()
    if ya_hoy is not None:
        return None
    pendientes = db.listar_preguntas_pendientes(conexion, ahora, None, limite=1)
    if not pendientes:
        return None
    pregunta = pendientes[0]
    telegram.avisar(telegram.AvisoSaliente(texto=pregunta.voz, urgente=False))
    marcar_en_el_aire(conexion, pregunta.id)
    conexion.execute("INSERT INTO pregunta_telegram_dia (dia) VALUES (?)", (dia,))
    conexion.commit()
    return pregunta


MAXIMO_VISIBLES = 3
HORAS_DESPUES = 24


@dataclass(frozen=True)
class Detectada:
    tema: str
    campo: str
    voz: str


def _detectar_tipo(libro: libros.Libro) -> list[Detectada]:
    if libro.tipo is None:
        return [Detectada(libro.tema, "tipo", f"¿{libro.titulo} es de un cliente o es tuyo?")]
    return []


def _detectar_cliente(libro: libros.Libro) -> list[Detectada]:
    if libro.tipo == "cliente" and not libro.cliente:
        return [Detectada(libro.tema, "cliente", f"¿Cómo se llama el cliente de {libro.titulo}?")]
    return []


def _detectar_listo_cuando(libro: libros.Libro) -> list[Detectada]:
    return [
        Detectada(
            libro.tema, f"fase.{n}.listo_cuando",
            f"¿Cuándo está lista la {fase.nombre} de {libro.titulo}?",
        )
        for n, fase in enumerate(libro.fases, start=1)
        if not fase.listo_cuando
    ]


def _detectar_cobrado(libro: libros.Libro, conexion: sqlite3.Connection) -> list[Detectada]:
    """Una fase `pagando` sin ningún cobro del proyecto todavía."""
    proyecto_id = entregas._proyecto_id_de_tema(libro.tema)
    total = entregas.total_pagado_proyecto(conexion, proyecto_id)
    if total > 0:
        return []
    return [
        Detectada(
            libro.tema, f"fase.{n}.cobrado",
            f"¿Cuánto pagó {libro.cliente or libro.titulo} de la {fase.nombre} de {libro.titulo}?",
        )
        for n, fase in enumerate(libro.fases, start=1)
        if fase.estado.strip().lower() == "pagando"
    ]


def _detectar_ruta(libro: libros.Libro) -> list[Detectada]:
    if not libro.rutas:
        return [Detectada(libro.tema, "ruta", f"¿En qué carpeta vive {libro.titulo}?")]
    return []


# F3.3 (plan de cierre): las tres formas que hay en la bóveda —
# «(Completar: para quién es…)», «(Completar con mensajes reales.)» y
# «Piso de precio por fase: (completar; ejemplo real: …)». Sin distinguir
# mayúsculas; lo que sigue a «completar» (dos puntos, punto y coma o «con»)
# es el pedido, salvo que la línea tenga una etiqueta antes del paréntesis:
# ahí la etiqueta ES el pedido («¿Piso de precio por fase de Clientes…?»).
_PATRON_COMPLETAR = re.compile(r"\(completar\b\s*(?::|;|con\b)?\s*(.*?)\)", re.IGNORECASE)


def _pedido_de_completar(linea: str) -> str | None:
    """Qué hay que completar en esta línea, o None si no es una línea
    «(Completar …)»."""
    coincidencia = _PATRON_COMPLETAR.search(linea)
    if coincidencia is None:
        return None
    etiqueta = linea[: coincidencia.start()].strip().lstrip("-*").strip().rstrip(":").strip()
    if etiqueta:
        return etiqueta
    return coincidencia.group(1).strip().rstrip(".")


def _tema_del_archivo(contenido: str) -> str | None:
    if not contenido.startswith("---"):
        return None
    partes = contenido.split("---", 2)
    if len(partes) < 3:
        return None
    tema = libros._frontmatter(partes[1]).get("tema")
    return tema if isinstance(tema, str) and tema else None


def _carpetas_completar() -> list[Path]:
    base = libros.carpeta().parent
    return [libros.carpeta(), base / "areas", base / "oficios"]


def _detectar_completar() -> list[Detectada]:
    """Cada línea «(Completar: …)» de proyectos/, áreas/ u oficios/ — son
    todos libros del mismo estante (Biblia Parte VI). `completar.N` usa el
    número de línea del archivo completo, igual que lo edita el escritor."""
    resultado: list[Detectada] = []
    for carpeta in _carpetas_completar():
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.glob("*.md")):
            texto = ruta.read_text()
            if not texto.startswith("---"):
                continue
            partes = texto.split("---", 2)
            if len(partes) < 3:
                continue
            campos = libros._frontmatter(partes[1])
            tema = campos.get("tema")
            titulo = campos.get("titulo") or tema
            if not isinstance(tema, str) or not tema:
                continue
            for n, linea in enumerate(texto.splitlines(), start=1):
                pedido = _pedido_de_completar(linea)
                if pedido:
                    resultado.append(Detectada(tema, f"completar.{n}", f"¿{pedido} de {titulo}?"))
    return resultado


def detectar(conexion: sqlite3.Connection) -> list[Detectada]:
    """Todos los huecos de todos los libros de proyectos, más las líneas
    «(Completar: …)» de proyectos/áreas/oficios."""
    resultado: list[Detectada] = []
    for libro in libros.listar():
        resultado += _detectar_tipo(libro)
        resultado += _detectar_cliente(libro)
        resultado += _detectar_listo_cuando(libro)
        resultado += _detectar_cobrado(libro, conexion)
        resultado += _detectar_ruta(libro)
    resultado += _detectar_completar()
    return resultado


def sincronizar(conexion: sqlite3.Connection, ahora: datetime) -> int:
    """Crea una fila `pendiente` por cada hueco detectado que todavía no
    tiene pregunta (en ningún estado) para ese `(tema, campo)`. Nunca
    duplica, nunca borra. Devuelve cuántas creó."""
    creadas = 0
    for detectada in detectar(conexion):
        if db.pregunta_de_tema_campo(conexion, detectada.tema, detectada.campo) is not None:
            continue
        db.crear_pregunta(
            conexion,
            Pregunta(
                id=uuid4(), tema=detectada.tema, campo=detectada.campo, voz=detectada.voz,
                estado="pendiente", creada_en=ahora, disponible_desde=ahora,
            ),
        )
        creadas += 1
    return creadas


# — Escritores: uno por campo, cada uno agrega, nunca borra —


def _dividir_frontmatter(archivo: Path) -> tuple[str, list[str], str]:
    """(antes, líneas del frontmatter, después) — reconstruir con
    `"---".join([antes, "\\n".join(lineas) + "\\n", después])`."""
    texto = archivo.read_text()
    partes = texto.split("---", 2)
    return partes[0], partes[1].splitlines(), partes[2]


def _escribir_escalar(archivo: Path, clave: str, valor: str) -> None:
    antes, lineas, despues = _dividir_frontmatter(archivo)
    patron = re.compile(rf"^{re.escape(clave)}:.*$")
    for i, linea in enumerate(lineas):
        if patron.match(linea):
            lineas[i] = f"{clave}: {valor}"
            break
    else:
        lineas.append(f"{clave}: {valor}")
    archivo.write_text("---".join([antes, "\n".join(lineas) + "\n", despues]))


def _agregar_item_lista(archivo: Path, clave: str, valor: str) -> None:
    """Solo agrega: si `clave:` ya tiene items, el nuevo va al final;
    nunca toca los que ya había."""
    antes, lineas, despues = _dividir_frontmatter(archivo)
    inicio = next((i for i, l in enumerate(lineas) if l.rstrip() == f"{clave}:" or l.startswith(f"{clave}:")), None)
    if inicio is None:
        lineas.append(f"{clave}:")
        lineas.append(f"  - {valor}")
    else:
        fin = inicio + 1
        while fin < len(lineas) and lineas[fin].lstrip().startswith("- "):
            fin += 1
        lineas.insert(fin, f"  - {valor}")
    archivo.write_text("---".join([antes, "\n".join(lineas) + "\n", despues]))


def _indices_de_fases(lineas: list[str], inicio: int) -> list[int]:
    return [i for i in range(inicio + 1, len(lineas)) if re.match(r"^\s*-\s*nombre:", lineas[i])]


def _escribir_campo_fase(archivo: Path, n: int, campo: str, valor: str) -> bool:
    antes, lineas, despues = _dividir_frontmatter(archivo)
    inicio = next((i for i, l in enumerate(lineas) if l.rstrip() == "fases:" or l.startswith("fases:")), None)
    if inicio is None:
        return False
    indices = _indices_de_fases(lineas, inicio)
    if n < 1 or n > len(indices):
        return False
    inicio_fase = indices[n - 1]
    fin_fase = indices[n] if n < len(indices) else len(lineas)
    for i in range(inicio_fase, min(fin_fase, len(lineas))):
        if lineas[i].strip() and not lineas[i].startswith((" ", "\t", "-")):
            fin_fase = i
            break
    patron = re.compile(rf"^(\s*){re.escape(campo)}:.*$")
    for i in range(inicio_fase, fin_fase):
        coincidencia = patron.match(lineas[i])
        if coincidencia:
            lineas[i] = f"{coincidencia.group(1)}{campo}: {valor}"
            archivo.write_text("---".join([antes, "\n".join(lineas) + "\n", despues]))
            return True
    return False


_PATRON_SI_CLIENTE = re.compile(r"\bcliente\b", re.IGNORECASE)
_PATRON_SI_PROPIO = re.compile(r"\b(propio|mio|m[ií]o|tuyo)\b", re.IGNORECASE)
_PATRON_MONTO_RESPUESTA = re.compile(r"(\d[\d.,]*)")


def _monto_de(texto: str) -> float | None:
    coincidencia = _PATRON_MONTO_RESPUESTA.search(texto)
    if coincidencia is None:
        return None
    try:
        return float(coincidencia.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def responder(conexion: sqlite3.Connection, pregunta: Pregunta, texto: str) -> bool:
    """Aplica la respuesta al campo que le falta a `pregunta.tema`. False
    si el texto no se entiende — no guarda nada."""
    libro = next((l for l in libros.listar() if l.tema == pregunta.tema), None)

    if pregunta.campo.startswith("regla."):
        # T9.1: de lección a regla. Un «sí» la aplica con commit
        # (correcciones.aplicar_regla); cualquier otra cosa se entiende
        # como «no» — se descarta en silencio, sin insistir (ley 3).
        import correcciones
        import experiencia

        propuesta = experiencia.leer_propuesta_regla(conexion, pregunta.campo)
        if propuesta is None:
            return False
        if not correcciones.es_confirmacion(texto):
            return True
        oficio, regla = propuesta
        correcciones.aplicar_regla(oficio, regla)
        return True

    if pregunta.campo == "tipo":
        if libro is None:
            return False
        if _PATRON_SI_CLIENTE.search(texto):
            valor = "cliente"
        elif _PATRON_SI_PROPIO.search(texto):
            valor = "propio"
        else:
            return False
        boveda_git.snapshot_antes(f"responder tipo de {libro.archivo.name}")
        _escribir_escalar(libro.archivo, "tipo", valor)
        boveda_git.snapshot_despues(f"{libro.archivo.stem}: tipo {valor}, respondido")
        return True

    if pregunta.campo == "cliente":
        if libro is None or not texto.strip():
            return False
        nombre = texto.strip()
        boveda_git.snapshot_antes(f"responder cliente de {libro.archivo.name}")
        _escribir_escalar(libro.archivo, "cliente", nombre)
        boveda_git.snapshot_despues(f"{libro.archivo.stem}: cliente {nombre}, respondido")
        return True

    if pregunta.campo == "ruta":
        if libro is None or not texto.strip():
            return False
        ruta = str(Path(texto.strip()).expanduser())
        boveda_git.snapshot_antes(f"responder ruta de {libro.archivo.name}")
        _agregar_item_lista(libro.archivo, "ruta", ruta)
        boveda_git.snapshot_despues(f"{libro.archivo.stem}: ruta agregada, respondido")
        return True

    if pregunta.campo.startswith("fase.") and pregunta.campo.endswith(".listo_cuando"):
        if libro is None or not texto.strip():
            return False
        n = int(pregunta.campo.split(".")[1])
        boveda_git.snapshot_antes(f"responder listo_cuando de la fase {n} de {libro.archivo.name}")
        escrito = _escribir_campo_fase(libro.archivo, n, "listo_cuando", texto.strip())
        if not escrito:
            return False
        boveda_git.snapshot_despues(f"{libro.archivo.stem}: listo_cuando de la fase {n}, respondido")
        return True

    if pregunta.campo.startswith("fase.") and pregunta.campo.endswith(".cobrado"):
        if libro is None:
            return False
        monto = _monto_de(texto)
        if monto is None:
            return False
        proyecto_id = entregas._proyecto_id_de_tema(pregunta.tema)
        ya_pagado = entregas.total_pagado_proyecto(conexion, proyecto_id)
        diferencia = monto - ya_pagado
        if diferencia <= 0:
            return True
        from modelos import Entrega

        entregas.crear_entrega(
            conexion,
            Entrega(
                id=uuid4(), cliente=libro.cliente or libro.titulo, proyecto_id=proyecto_id,
                fecha=datetime.now(timezone.utc), monto=diferencia, estado="pagada",
                linea=None, compartible=True,
            ),
        )
        return True

    if pregunta.campo.startswith("completar."):
        if not texto.strip():
            return False
        n = int(pregunta.campo.split(".")[1])
        # El archivo es el del tema de la pregunta: dos libros pueden tener
        # un «(Completar …)» en la misma línea N (areas/aprender.md y
        # areas/salud.md lo tienen en la 6), y antes se escribía en el
        # primero que apareciera.
        for carpeta in _carpetas_completar():
            for archivo_md in sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []:
                contenido = archivo_md.read_text()
                if _tema_del_archivo(contenido) != pregunta.tema:
                    continue
                lineas_archivo = contenido.splitlines()
                if not (1 <= n <= len(lineas_archivo)):
                    continue
                linea = lineas_archivo[n - 1]
                coincidencia = _PATRON_COMPLETAR.search(linea)
                if coincidencia is None:
                    continue
                boveda_git.snapshot_antes(f"responder completar.{n} de {archivo_md.name}")
                etiqueta = linea[: coincidencia.start()].rstrip()
                if etiqueta.strip().lstrip("-*").strip():
                    # «- Piso de precio por fase: (completar; …)» → la etiqueta
                    # se queda y el paréntesis se cambia por la respuesta.
                    lineas_archivo[n - 1] = f"{etiqueta} {texto.strip()}"
                else:
                    indentacion = re.match(r"^(\s*)", linea).group(1)  # type: ignore[union-attr]
                    lineas_archivo[n - 1] = f"{indentacion}- {texto.strip()}"
                archivo_md.write_text("\n".join(lineas_archivo) + "\n")
                boveda_git.snapshot_despues(f"{archivo_md.stem}: completar.{n}, respondido")
                return True
        return False

    return False

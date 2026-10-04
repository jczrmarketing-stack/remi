"""La sección «## Camino» de un libro de proyecto: hitos «- [ ] …» / «- [x] …».

Se lee siempre; se escribe solo para marcar un hito [x] — y solo cuando ya
existe una tarea con ese mismo texto en estado `hecha`. Nunca se escribe un
hito nuevo ni se reordena nada: eso es cosa de quien edita el libro a mano.

El chequeo es reactivo (se hace al leer, no al cerrar una tarea): así no
hace falta tocar las rutas que ya cierran tareas en servidor.py (/mensaje,
POST /tarea/{id}/estado), que no son de esta tarea.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import libros

TITULO = "## Camino"


@dataclass(frozen=True)
class Hito:
    texto: str
    hecho: bool


# — Plantillas del SOP (1-oct) —
#
# Fuente: oficios/proyectos-sop.md en remi-mente (§A «Proyecto propio,
# desde cero» = 7 pasos; §B «Proyecto de cliente nuevo» = 10 pasos; «Lo que
# Remi hace en cada paso» = los cuatro grupos de los que sale `paso_remi`).
# A mano, no leído del SOP en caliente: la bóveda es datos de Juan Camilo,
# no código — si el SOP cambia, esto se actualiza acá, a propósito, no con
# un parser que puede alucinar formato.
#
# (texto del hito, qué hace Remi en ese paso, el detalle — la línea del SOP
# que explica ese paso). Para los pasos 1–3 de A, el SOP no tiene un «Remi
# hace» explícito (ese bloque habla sobre todo de cliente): el texto de
# «Remi hace» de esos tres es una extensión razonable de la ley 2 (memoria
# externa) y la ley 6 (enfriamiento), no una cita literal — el `detalle`
# de todos los pasos, y el «Remi hace» de los demás, sí son del SOP
# (oficios/proyectos-sop.md, §A y §B), a mano, no leído en caliente.
# B3.1: `cierra_con` — con qué evidencia se marca [x] sin que nadie lo
# toque a mano: "encargo" (una sesión de Claude Code nacida de un encargo
# de ese hito, con commits y pruebas en verde), "mensaje" (Juan Camilo
# dice que lo mandó), "cobro" (un cobro del proyecto), "pregunta"
# (Remi pregunta y el sí lo confirma en el panel — para lo que no deja
# huella de código ni de plata). A mano, como el resto de esta tabla: cada
# hito, su evidencia, decidido por lo que ese paso puede dejar probado.
PASOS_PROPIO: tuple[tuple[str, str, str, str], ...] = (
    (
        "Bandeja 48 h",
        "Cuenta las 48 h del enfriamiento y avisa cuando toca la revisión en frío.",
        "La idea entra a la Bandeja y enfría 48 h (Ley 06). Sin excepción.",
        "pregunta",
    ),
    (
        "Revisión en frío",
        "Trae el filtro — loco + útil + estratégico — para decidir sin culpa.",
        "Revisión en frío con el filtro loco + útil + estratégico. Si falta uno, se suelta sin culpa.",
        "pregunta",
    ),
    (
        "Biblia corta",
        "Ayuda a armar la Biblia corta de una página.",
        "Biblia corta (una página): problema, para quién, qué NO es, stack, fases con «listo cuando».",
        "encargo",
    ),
    (
        "Mockups A/B/C",
        "Escribe los encargos y lleva el camino.",
        "Diseño primero: mockups A/B/C → aprobación → código.",
        "encargo",
    ),
    (
        "Encargos a Claude Code",
        "Escribe los encargos y lleva el camino.",
        "Encargos de una tarea a Claude Code, por la puerta de Remi.",
        "encargo",
    ),
    (
        "Actualizar libro y camino",
        "Escribe los encargos y lleva el camino.",
        "Cada fase cerrada actualiza el libro del proyecto y su camino (hitos).",
        "encargo",
    ),
    (
        "Prioridad por plata",
        "Escribe los encargos y lleva el camino.",
        "Prioridad frente a clientes: lo que trae plata pronto va primero.",
        "pregunta",
    ),
)

PASOS_CLIENTE: tuple[tuple[str, str, str, str], ...] = (
    (
        "Intake",
        "Arma la lectura y las preguntas.",
        "Qué pide, qué necesita de verdad, plata en juego, urgencia, riesgo. Remi lo lee con "
        "teoría de juegos: qué gana cada uno, qué pasa si no.",
        "pregunta",
    ),
    (
        "Descubrimiento (5 preguntas)",
        "Arma la lectura y las preguntas.",
        "Máximo 5 preguntas al cliente, las que cambian la propuesta.",
        "pregunta",
    ),
    (
        "Propuesta por fases",
        "Escribe el borrador en la voz de Juan Camilo.",
        "Cada fase con alcance, monto y «listo cuando». Fase 1 pequeña y cobrable.",
        "encargo",
    ),
    (
        "Contrato",
        "Escribe el borrador en la voz de Juan Camilo.",
        "Corto, amable, que protege a Omniway (ley de Wyoming). El cliente lo revisa con IA: "
        "escribirlo para que eso salga bien.",
        "encargo",
    ),
    (
        "Pago antes de arrancar",
        "Recuerda fechas y promesas; avisa el día antes.",
        "En cuotas, con tolerancia de días. El trabajo empieza cuando el pago está completo.",
        "cobro",
    ),
    (
        "Entregas medidas",
        "Escribe los encargos y lleva el camino.",
        "Cada fase se cierra con una demo y el «listo cuando» cumplido.",
        "encargo",
    ),
    (
        "Cobro y cierre",
        "Recuerda fechas y promesas; avisa el día antes.",
        "Factura, comprobante, libro actualizado, siguiente fase propuesta.",
        "cobro",
    ),
    (
        "Producción",
        "Escribe los encargos y lleva el camino.",
        "La lista del oficio «producción» completa antes de entregar.",
        "encargo",
    ),
    (
        "Entrega y capacitación",
        "Escribe los encargos y lleva el camino.",
        "Demo, cuentas a nombre del cliente, runbook.",
        "mensaje",
    ),
    (
        "Mensualidad",
        "Recuerda fechas y promesas; avisa el día antes.",
        "Se propone en la entrega (oficio «mantenimiento»). Es el objetivo del ciclo.",
        "mensaje",
    ),
)


def plantilla_de(tipo: str) -> tuple[tuple[str, str, str, str], ...] | None:
    """Los (hito, paso_remi, detalle, cierra_con) del tipo pedido. None si
    el tipo no es «propio» ni «cliente» — nunca una plantilla inventada."""
    if tipo == "propio":
        return PASOS_PROPIO
    if tipo == "cliente":
        return PASOS_CLIENTE
    return None


def bloque_camino_de(tipo: str) -> str:
    """El texto de «## Camino» entero, un hito por paso, en el orden del
    SOP — listo para agregar al final de un libro (sembrar_camino.py)."""
    pasos = plantilla_de(tipo)
    if pasos is None:
        raise ValueError(f"tipo desconocido: {tipo!r}")
    lineas = [TITULO, ""]
    lineas += [f"- [ ] {texto}" for texto, _, _, _ in pasos]
    return "\n".join(lineas) + "\n"


def paso_remi_de(tipo: str | None, texto_hito: str) -> str:
    """Qué hace Remi en este paso, según el SOP. Si no se sabe el tipo (el
    frontmatter no lo dice), prueba las dos plantillas — los textos de
    hito no se repiten entre ellas, así que no hay ambigüedad real."""
    plantillas = (PASOS_CLIENTE, PASOS_PROPIO) if tipo != "propio" else (PASOS_PROPIO, PASOS_CLIENTE)
    for plantilla in plantillas:
        for texto, paso_remi, _detalle, _cierra_con in plantilla:
            if texto == texto_hito:
                return paso_remi
    return ""


def detalle_de(tipo: str | None, texto_hito: str) -> str:
    """Forma A (T2): la línea del SOP que explica este paso. `""` si el
    hito no es del SOP (uno escrito a mano, fuera de las plantillas)."""
    plantillas = (PASOS_CLIENTE, PASOS_PROPIO) if tipo != "propio" else (PASOS_PROPIO, PASOS_CLIENTE)
    for plantilla in plantillas:
        for texto, _paso_remi, detalle, _cierra_con in plantilla:
            if texto == texto_hito:
                return detalle
    return ""


def cierra_con_de(tipo: str | None, texto_hito: str) -> str | None:
    """B3.1: con qué evidencia se cierra este hito — "encargo" | "mensaje"
    | "cobro" | "pregunta". None si el hito no es del SOP (uno escrito a
    mano): sin evidencia esperada, nunca se cierra solo."""
    plantillas = (PASOS_CLIENTE, PASOS_PROPIO) if tipo != "propio" else (PASOS_PROPIO, PASOS_CLIENTE)
    for plantilla in plantillas:
        for texto, _paso_remi, _detalle, cierra_con in plantilla:
            if texto == texto_hito:
                return cierra_con
    return None


def marcar_por_indice(archivo: Path, indice: int, hecho: bool) -> None:
    """Edita SOLO la línea del hito en esa posición (0-indexed, en el
    orden en que aparecen en ## Camino): «- [ ]» <-> «- [x]». El resto del
    libro queda intacto. A diferencia de `marcar_hitos_cumplidos` (que solo
    marca [x] y solo si hay una tarea `hecha` con ese texto), esto es la
    acción directa de POST /libros/{tema}/camino/{n}: cualquiera de los dos
    sentidos, por posición."""
    original = archivo.read_text()
    lineas = original.splitlines()
    inicio = _indice(lineas)
    if inicio is None:
        raise ValueError("el libro no tiene ## Camino")
    fin = _fin(lineas, inicio)
    vistos = -1
    for i in range(inicio + 1, fin):
        limpia = lineas[i].strip()
        if limpia.startswith("- [x]") or limpia.startswith("- [X]") or limpia.startswith("- [ ]"):
            vistos += 1
            if vistos == indice:
                texto_hito = limpia[5:].strip()
                sangria = lineas[i][: len(lineas[i]) - len(lineas[i].lstrip())]
                marca = "x" if hecho else " "
                lineas[i] = f"{sangria}- [{marca}] {texto_hito}"
                archivo.write_text("\n".join(lineas) + ("\n" if original.endswith("\n") else ""))
                return
    raise IndexError(f"no hay un hito en la posición {indice}")


def _cuerpo(texto: str) -> str:
    if not texto.startswith("---"):
        return texto
    partes = texto.split("---", 2)
    return partes[2] if len(partes) >= 3 else texto


def _indice(lineas: list[str]) -> int | None:
    for i, linea in enumerate(lineas):
        if linea.strip() == TITULO:
            return i
    return None


def _fin(lineas: list[str], inicio: int) -> int:
    for j in range(inicio + 1, len(lineas)):
        if lineas[j].startswith("## "):
            return j
    return len(lineas)


def _parsear(cuerpo: str) -> list[Hito]:
    lineas = cuerpo.splitlines()
    inicio = _indice(lineas)
    if inicio is None:
        return []
    fin = _fin(lineas, inicio)
    hitos: list[Hito] = []
    for linea in lineas[inicio + 1 : fin]:
        limpia = linea.strip()
        if limpia.startswith("- [x]") or limpia.startswith("- [X]"):
            hitos.append(Hito(texto=limpia[5:].strip(), hecho=True))
        elif limpia.startswith("- [ ]"):
            hitos.append(Hito(texto=limpia[5:].strip(), hecho=False))
    return hitos


def leer_hitos(archivo: Path) -> list[Hito]:
    """Los hitos del libro, en el orden en que están escritos."""
    return _parsear(_cuerpo(archivo.read_text()))


def siguiente_abierto(hitos: list[Hito]) -> Hito | None:
    return next((h for h in hitos if not h.hecho), None)


def _marcar(archivo: Path, texto_hito: str) -> None:
    """Pasa «- [ ] texto» a «- [x] texto» dentro de ## Camino. El resto del
    libro queda intacto: solo se toca esa línea."""
    original = archivo.read_text()
    lineas = original.splitlines()
    inicio = _indice(lineas)
    if inicio is None:
        return
    fin = _fin(lineas, inicio)
    for i in range(inicio + 1, fin):
        limpia = lineas[i].strip()
        if limpia.startswith("- [ ]") and limpia[5:].strip() == texto_hito:
            sangria = lineas[i][: len(lineas[i]) - len(lineas[i].lstrip())]
            lineas[i] = f"{sangria}- [x] {texto_hito}"
            break
    else:
        return
    archivo.write_text("\n".join(lineas) + ("\n" if original.endswith("\n") else ""))


def marcar_hitos_cumplidos(conexion: sqlite3.Connection, libro: libros.Libro) -> list[Hito]:
    """Revisa cada hito abierto contra `tareas`: si hay una tarea `hecha`
    con el mismo título Y una sesión con `app_contexto` igual al tema de
    este libro, la marca [x] en el archivo. Devuelve los hitos ya
    actualizados (para que quien llame no tenga que releer el archivo).

    Solo el título no alcanza: los hitos del SOP («Intake», «Contrato»…)
    se repiten palabra por palabra entre libros, y antes de este chequeo
    terminar «Intake» en un proyecto marcaba «Intake» en todos los demás."""
    hitos = leer_hitos(libro.archivo)
    cambiaron = False
    actualizados: list[Hito] = []
    for hito in hitos:
        if hito.hecho:
            actualizados.append(hito)
            continue
        fila = conexion.execute(
            "SELECT 1 FROM tareas t JOIN sesiones s ON s.tarea_id = t.id "
            "WHERE t.titulo = ? AND t.estado = 'hecha' AND s.app_contexto = ? LIMIT 1",
            (hito.texto, libro.tema),
        ).fetchone()
        if fila is not None:
            _marcar(libro.archivo, hito.texto)
            actualizados.append(Hito(texto=hito.texto, hecho=True))
            cambiaron = True
        else:
            actualizados.append(hito)
    return leer_hitos(libro.archivo) if cambiaron else actualizados


def cerrar_primer_hito_con(conexion: sqlite3.Connection, tema: str, categoria: str) -> int | None:
    """B3.1: SOLO el hito que sigue ahora mismo en el camino de `tema`
    (el primero sin marcar) — nunca uno de más adelante, aunque también
    sea de esa `categoria` ("mensaje" o "cobro"). Un libro con dos hitos
    "mensaje" (Entrega y capacitación, Mensualidad) nunca confunde cuál es
    cuál: si el que sigue ahora no es de esta categoría, no cierra nada —
    no hay evidencia de que haya llegado hasta ahí. Devuelve su posición
    (1-indexed), o None si no hay libro o el que sigue no cierra así."""
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        return None
    hitos = marcar_hitos_cumplidos(conexion, libro)
    siguiente = siguiente_abierto(hitos)
    if siguiente is None or cierra_con_de(libro.tipo, siguiente.texto) != categoria:
        return None
    indice = next(i for i, h in enumerate(hitos) if h is siguiente)
    marcar_por_indice(libro.archivo, indice, True)
    return indice + 1


def hitos_de_tema(conexion: sqlite3.Connection, tema: str) -> tuple[list[Hito], Hito | None] | None:
    """(hitos, siguiente abierto) del libro de ese tema. None si no hay
    libro con ese tema."""
    libro = next((l for l in libros.listar() if l.tema == tema), None)
    if libro is None:
        return None
    hitos = marcar_hitos_cumplidos(conexion, libro)
    return hitos, siguiente_abierto(hitos)

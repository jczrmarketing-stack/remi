"""La sección «Estado» de un libro de proyecto.

El resto del libro no se toca. Haiku la escribe, con el carácter de Remi
(conocimiento/caracter.md); si no contesta, Ollama de respaldo; si ninguno
contesta, queda un estado plano sacado del commit, para que el libro igual
cambie. (Antes era al revés —Ollama primero— y sonaba robótico: encargo del
30-sep.)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pensar

TITULO = "## Estado"
INSTRUCCIONES = (
    "Te paso el estado anterior de un proyecto y los commits nuevos. "
    "No inventes datos, decisiones ni pasos que no estén en el estado anterior o en los "
    "commits: si no hay commits nuevos, mantén el mismo contenido del estado anterior y "
    "como mucho mejora el tono, sin agregar hechos. "
    "Devuelve SOLO tres líneas, sin markdown y sin nada antes ni después:\n"
    "Quedaste: (dónde quedó el trabajo, una frase)\n"
    "Decisiones: (lo que se decidió, o «ninguna nueva»)\n"
    "Próximo paso: (una sola acción de cinco minutos)\n"
    "En español, de tú, sin exclamaciones y sin reproche."
)


def leer_estado(archivo: Path) -> str:
    """Lo que hay bajo ## Estado, sin el título. Vacío si la sección no está."""
    cuerpo = _cuerpo(archivo.read_text())
    lineas = cuerpo.splitlines()
    inicio = _indice(lineas)
    if inicio is None:
        return ""
    fin = _fin(lineas, inicio)
    return "\n".join(lineas[inicio + 1 : fin]).strip()


def escribir_estado(archivo: Path, texto: str) -> None:
    """Crea o reemplaza ## Estado. El frontmatter y el resto siguen igual."""
    original = archivo.read_text()
    bloque = f"{TITULO}\n\n{texto.strip()}\n"
    if not original.startswith("---"):
        base = original.rstrip()
        archivo.write_text((base + "\n\n" if base else "") + bloque)
        return
    partes = original.split("---", 2)
    if len(partes) < 3:
        archivo.write_text(original.rstrip() + "\n\n" + bloque)
        return
    nuevo_cuerpo = _reemplazar(partes[2], bloque.strip("\n"))
    archivo.write_text(f"---{partes[1]}---{nuevo_cuerpo}")


def sin_evidencia_nueva(pedido: str) -> bool:
    """True si el pedido no trae ningún commit nuevo bajo «Commits nuevos:».

    Sin esto, un llamado suelto a `redactar()` (como el del incidente del
    30-sep) puede terminar inventando un Estado con la bandeja vacía. Ninguna
    rutina llama al modelo si esto da True — ni Haiku ni Ollama.
    """
    lineas = pedido.splitlines()
    try:
        indice = lineas.index("Commits nuevos:")
    except ValueError:
        return True
    resto = [linea for linea in lineas[indice + 1 :] if linea.strip()]
    return not resto


PATRON_SIGLA = re.compile(r"\b[A-Z][A-Z0-9]{1,9}\b")
PATRON_NUMERO = re.compile(r"\b\d{2,}\b")
PATRON_ARCHIVO = re.compile(r"\b[\w-]+\.[a-zA-Z]{1,4}\b")


def entidades_sospechosas(texto: str) -> list[str]:
    """Siglas, números de dos o más cifras y nombres de archivo: lo único que
    se puede verificar mecánicamente contra la fuente, sin otro modelo. No
    detecta una paráfrasis inventada de una frase entera — para eso no hay
    verificación mecánica posible —, pero sí el tipo exacto de invento del
    incidente del 30-sep (siglas y decisiones con nombre propio que no
    estaban en ninguna fuente: «N8N», «WAL», «Opción B»)."""
    vistas: set[str] = set()
    resultado: list[str] = []
    for patron in (PATRON_SIGLA, PATRON_NUMERO, PATRON_ARCHIVO):
        for coincidencia in patron.finditer(texto):
            token = coincidencia.group(0)
            if token not in vistas:
                vistas.add(token)
                resultado.append(token)
    return resultado


def _invento(texto: str, fuente: str) -> str | None:
    """La primera entidad verificable de `texto` que no aparece, literal, en
    `fuente`. None si todas aparecen (o no hay ninguna que verificar)."""
    for entidad in entidades_sospechosas(texto):
        if entidad not in fuente:
            return entidad
    return None


def redactar(pedido: str) -> str | None:
    """Tres líneas, o None si no hubo respuesta usable.

    None también, sin llamar a ningún modelo, si `pedido` no trae commits
    nuevos (ver `sin_evidencia_nueva`): sin evidencia, el libro no se toca.

    Y None si lo que contestó el modelo trae una entidad verificable (sigla,
    número, nombre de archivo) que no está, literal, en `pedido`: la
    instrucción anti-invento es un pedido al modelo, no una garantía — el
    incidente del 30-sep lo probó dos veces con evidencia real de por medio
    (`docs/BITACORA.md`). Esto es la verificación mecánica que faltaba, y se
    aplica igual a cada motor de la trastienda (`config/motores.json`): uno
    rechazado por invento cae al siguiente, igual que uno que no contestó.
    """
    if sin_evidencia_nueva(pedido):
        return None
    instrucciones_con_caracter = f"{pensar.caracter()}\n\n{INSTRUCCIONES}"

    def aceptar(pensado: pensar.Pensado) -> bool:
        limpio = normalizar(pensado.paso_minimo)
        if limpio is None:
            return False
        sospechosa = _invento(limpio, pedido)
        if sospechosa is not None:
            print(
                f"[estado] rechazado por invento ({pensado.motor_usado}): {sospechosa!r} no está en la fuente",
                file=sys.stderr,
            )
            return False
        return True

    pensado = pensar.pensar_con_trastienda(pedido, instrucciones_con_caracter, aceptar=aceptar)
    return normalizar(pensado.paso_minimo) if pensado else None


def normalizar(texto: str) -> str | None:
    """Deja las tres líneas pedidas, en orden. None si falta alguna."""
    quedaste = decisiones = proximo = ""
    for linea in texto.splitlines():
        limpia = linea.strip().lstrip("-").strip()
        baja = limpia.lower()
        if baja.startswith("quedaste:"):
            quedaste = _frase("Quedaste", limpia.split(":", 1)[1])
        elif baja.startswith("decisiones:"):
            decisiones = _frase("Decisiones", limpia.split(":", 1)[1])
        elif baja.startswith("próximo paso:") or baja.startswith("proximo paso:"):
            proximo = _frase("Próximo paso", limpia.split(":", 1)[1])
    if not (quedaste and decisiones and proximo):
        return None
    return f"{quedaste}\n{decisiones}\n{proximo}"


def plano(commits: list[dict[str, object]]) -> str:
    """Cuando no hay modelo: el libro igual dice dónde quedó."""
    ultimo: dict[str, object] = commits[-1] if commits else {}
    mensaje = str(ultimo.get("mensaje") or "").strip() or "un commit sin mensaje"
    rama = str(ultimo.get("rama") or "").strip()
    donde = f"Quedaste en «{mensaje}»"
    if rama:
        donde += f", rama {rama}"
    return (
        f"{donde}.\n"
        "Decisiones: ninguna anotada.\n"
        "Próximo paso: retomar desde ese commit, cinco minutos."
    )


def pedido(titulo: str, anterior: str, commits: list[dict[str, object]]) -> str:
    lineas = [f"Proyecto: {titulo}", ""]
    if anterior.strip():
        lineas.append("Estado anterior:")
        lineas.append(anterior.strip())
        lineas.append("")
    lineas.append("Commits nuevos:")
    for commit in commits[-12:]:
        mensaje = str(commit.get("mensaje") or "").strip() or "(sin mensaje)"
        rama = str(commit.get("rama") or "").strip()
        archivos = commit.get("archivos") or []
        if not isinstance(archivos, list):
            archivos = []
        nombres = ", ".join(str(a) for a in archivos[:12])
        lineas.append(f"- {mensaje}" + (f" ({rama})" if rama else "") + (f" · {nombres}" if nombres else ""))
    return "\n".join(lineas)[:4000]


def _frase(etiqueta: str, resto: str) -> str:
    texto = " ".join(resto.split()).strip()
    return f"{etiqueta}: {texto}" if texto else ""


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


def _reemplazar(cuerpo: str, bloque: str) -> str:
    lineas = cuerpo.splitlines()
    inicio = _indice(lineas)
    nuevas = bloque.splitlines()
    if inicio is None:
        base = cuerpo.rstrip()
        return (("\n" + base + "\n\n") if base else "\n") + bloque + "\n"
    fin = _fin(lineas, inicio)
    armado = lineas[:inicio] + nuevas
    if fin < len(lineas):
        if armado and armado[-1] != "":
            armado.append("")
        armado.extend(lineas[fin:])
    return "\n".join(armado).rstrip() + "\n"

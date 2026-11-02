"""Una sola manera de preguntarle a la mente, para el MCP (`preguntar`) y para Telegram (`/p`).

Sin modelo: busca en el índice, muestra estatus, confianza, el estado de caducidad de las afirmaciones
(B2) y, si hay, videos del catálogo que aún no se leen (B4).
"""
from __future__ import annotations

import re

import afirmaciones_puente
import catalogo_puente
import indexar
import metricas
import vida

MAXIMO_TELEGRAM = 3500          # el tope de Telegram es 4096; se deja margen


def _caducidad(id_nota: str) -> str:
    e = afirmaciones_puente.estado_de(id_nota)
    return f"\n{e}" if e else ""


def responder(q: str, origen: str = "mcp", maximo: int | None = None) -> str:
    conexion = indexar.conectar()
    try:
        # Una nota de hace un minuto ya tiene que salir; el resto de vectores los hace la noche.
        indexar.actualizar(conexion, tope_vectores=5)
        hallazgos = indexar.buscar(conexion, q)
    finally:
        conexion.close()
    # Umbral honesto: lo que no comparte ni un término con la consulta queda marcado como
    # «relacionado» (vino solo por vector) y se limita a 2.
    terminos = vida._terminos(q)
    todos_exactos = [h for h in hallazgos if any(t in vida._slug(f"{h.titulo} {h.resumen}", 400) for t in terminos)]
    exactos = todos_exactos[:maximo] if maximo else todos_exactos
    # «Relacionado» es lo que NO fue exacto; los exactos que se recortan por espacio no pasan a ser parecidos.
    parecidos = [h for h in hallazgos if h not in todos_exactos][:2]
    texto = "\n".join(
        f"[{h.id}] {h.tipo} · {h.fecha} · estatus: {h.estatus} · confianza: {h.confianza}\n{h.titulo}: {h.resumen}{_caducidad(h.id)}"
        for h in exactos
    )
    if parecidos:
        texto += ("\n" if texto else "") + "Relacionado, no exacto:\n" + "\n".join(f"[{h.id}] {h.tipo} · {h.titulo}" for h in parecidos)
    videos = catalogo_puente.aviso(q)
    if videos:
        texto += ("\n\n" if texto else "") + videos
    metricas.registrar_consulta(origen, "-", q, [h.id for h in exactos + parecidos], len(texto))
    if not texto:
        return f"No hay nada sobre «{q}» en la mente."
    return texto


_COMANDO = re.compile(r"^/(?:p|preguntar)(?:@\w+)?(?:\s+(.*))?$", re.I | re.S)


def manejar_comando(texto: str) -> str | None:
    """`/p <pregunta>` por Telegram. None si el mensaje no es ese comando. Nunca levanta: un fallo se dice."""
    m = _COMANDO.match(texto.strip())
    if m is None:
        return None
    q = (m.group(1) or "").strip()
    if not q:
        return "Escribe la pregunta después: /p cómo ahorrar tokens en Claude Code"
    try:
        r = responder(q, origen="telegram", maximo=3)
    except Exception:  # noqa: BLE001 — preguntar desde el celular no puede tumbar el bot
        return "No pude buscar ahora mismo. Intenta en un momento."
    return r if len(r) <= MAXIMO_TELEGRAM else r[:MAXIMO_TELEGRAM].rsplit("\n", 1)[0] + "\n…(recortado)"

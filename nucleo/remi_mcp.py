"""El cerebro vivo de Remi, como servidor MCP global (stdio).

Cualquier sesión de Claude lo abre y sabe en qué está Juan Camilo sin que él
se lo cuente de nuevo. Ocho herramientas, ninguna llama a un modelo de pago:

- estado_vivo  — su vida hoy en ≤ ~1.500 tokens, con la edad del dato.
- preguntar    — busca en el índice: resumen, fecha, estatus y confianza, sin el cuerpo.
- leer         — el cuerpo de una nota, por el id que dio `preguntar`.
- anotar       — deja algo en la bandeja o abre un supuesto.
- supuestos    — lo que se dio por cierto y ya toca revisar.
- contradice   — B2: ¿este dato choca con algo vigente en la mente?
- anotar_leccion, buscar_lecciones — T8: la experiencia de los arreglos (absorbidas del MCP `memoria`, F1.4c).

Los archivos viven en ~/proyectos/mente (git, legibles
desde Obsidian). Nada sale del Mac.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

import afirmaciones_puente
import indexar
import memoria_mcp
import metricas
import vida

servidor = MCPServer(
    "remi",
    instructions=(
        "Remi es el contexto vivo de Juan Camilo (negocio y vida). Al empezar una sesión que dependa de "
        "su situación, llama `estado_vivo` una vez. Antes de preguntarle algo que ya debería saberse, usa "
        "`preguntar`. Cuando él decida algo, o aparezca un dato que cambie su situación, usa `anotar`. "
        "Si `estado_vivo` trae supuestos por revisar, confírmalos con él en una sola pregunta corta."
    ),
)


@servidor.tool(description="La vida y el negocio de Juan Camilo hoy, en pocas líneas, con la edad del dato. Llámala al empezar.")
def estado_vivo() -> str:
    return vida.construir_estado()


@servidor.tool(description="Busca en la mente de Remi (sin gastar modelo): devuelve resumen, fecha, estatus y confianza. Úsala antes de preguntarle algo a Juan Camilo; el cuerpo se pide con `leer`.")
def preguntar(q: str) -> str:
    conexion = indexar.conectar()
    try:
        # Una nota de hace un minuto ya tiene que salir; el resto de vectores los hace la noche.
        indexar.actualizar(conexion, tope_vectores=5)
        hallazgos = indexar.buscar(conexion, q)
    finally:
        conexion.close()
    # Umbral honesto: lo que no comparte ni un término con la consulta queda marcado como
    # «relacionado» (vino solo por vector) y se limita a 2. F1.5 pone reordenador y número.
    terminos = vida._terminos(q)
    exactos = [h for h in hallazgos if any(t in vida._slug(f"{h.titulo} {h.resumen}", 400) for t in terminos)]
    parecidos = [h for h in hallazgos if h not in exactos][:2]
    def _caducidad(id_nota: str) -> str:   # B2: lo que ya venció se ve en la misma ficha
        e = afirmaciones_puente.estado_de(id_nota)
        return f"\n{e}" if e else ""

    texto = "\n".join(
        f"[{h.id}] {h.tipo} · {h.fecha} · estatus: {h.estatus} · confianza: {h.confianza}\n{h.titulo}: {h.resumen}{_caducidad(h.id)}"
        for h in exactos
    )
    if parecidos:
        texto += ("\n" if texto else "") + "Relacionado, no exacto:\n" + "\n".join(f"[{h.id}] {h.tipo} · {h.titulo}" for h in parecidos)
    metricas.registrar_consulta("mcp", "-", q, [h.id for h in exactos + parecidos], len(texto))
    if not texto:
        return f"No hay nada sobre «{q}» en la mente."
    return texto


@servidor.tool(description="El cuerpo completo de una nota, con el id entre corchetes que dio `preguntar`. Solo si el resumen no basta.")
def leer(id: str) -> str:
    conexion = indexar.conectar()
    try:
        cuerpo = indexar.leer(conexion, id)
    finally:
        conexion.close()
    return cuerpo if cuerpo is not None else f"No hay ninguna nota con id «{id}»."


@servidor.tool(description=(
    "Devuelve a la mente lo que se decidió, aprendió o investigó. tipo: decision | investigacion (exige URL en texto o en `fuentes`) | "
    "leccion | resultado | hipotesis (sin fuente) | hecho_sobre_mi (queda por confirmar y se le pregunta a Juan Camilo) | "
    "supuesto (se revisa solo) | idea | hecho | pendiente (bandeja). Al cerrar una sesión larga: 5 líneas máximo."
))
def anotar(texto: str, tipo: str = "hecho", revisar_en_dias: int = 14, fuentes: str = "") -> str:
    return vida.anotar(texto, tipo, revisar_en_dias, fuentes)


@servidor.tool(description="B2: ¿esto que acabas de leer choca con algo que la mente tiene vigente (precio, versión, cifra de mercado)? Devuelve las afirmaciones que dicen otra cosa, con nota y fecha. Úsala antes de dar por cierto un dato que cambia con el tiempo.")
def contradice(texto: str) -> str:
    return afirmaciones_puente.contradice(texto)


@servidor.tool(description="Supuestos abiertos que ya toca confirmar o dar por rotos.")
def supuestos() -> str:
    v = vida._supuestos_vencidos(vida._hoy())
    return "\n".join(v) if v else "No hay supuestos por revisar hoy."


@servidor.tool(description=memoria_mcp.anotar_leccion.__doc__ or (
    "T8: al cerrar un trabajo, por cada problema resuelto o acierto que valga la pena repetir — anota una lección, con evidencia, "
    "no un resumen de la charla. `clase` es «error» o «acierto»; `secciones` lleva las que pide cada clase: error — Síntoma, "
    "Lo que creímos (vacía si no hubo pista falsa), Causa real, Cura, Cómo verlo antes; acierto — Qué funcionó, Evidencia, "
    "Cuándo usarlo. `donde` es el repo y el archivo. Si ya hay una lección del mismo tema con el mismo síntoma, esto no crea "
    "otra: le suma una vuelta más."
))
def anotar_leccion(titulo: str, tema: str, resumen: str, clase: str, donde: str, secciones: dict[str, str]) -> str:
    return memoria_mcp.anotar_leccion(titulo, tema, resumen, clase, donde, secciones)


@servidor.tool(description=(
    "T8: antes de proponer un arreglo nuevo, busca si esto ya pasó. Texto exacto (un código de error, un nombre, un monto) y "
    "parecido, sobre libros, oficios, episodios y lecciones. `tema` filtra, por ejemplo «malik»."
))
def buscar_lecciones(q: str, tema: str = "") -> str:
    return memoria_mcp.buscar_lecciones(q, tema)


if __name__ == "__main__":
    servidor.run()

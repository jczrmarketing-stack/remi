"""El cerebro vivo de Remi, como servidor MCP global (stdio).

Cualquier sesión de Claude lo abre y sabe en qué está Juan Camilo sin que él
se lo cuente de nuevo. Cuatro herramientas, ninguna llama a un modelo de pago:

- estado_vivo  — su vida hoy en ≤ ~1.500 tokens, con la edad del dato.
- preguntar    — busca en mente/ y en la bóveda (texto, sin tokens).
- anotar       — deja algo en la bandeja o abre un supuesto.
- supuestos    — lo que se dio por cierto y ya toca revisar.

Solo stdlib + mcp. Los archivos viven en ~/proyectos/mente (git, legibles
desde Obsidian). Nada sale del Mac.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

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


@servidor.tool(description="Busca en el conocimiento de Remi y en la bóveda (sin gastar modelo). Úsala antes de preguntarle algo a Juan Camilo.")
def preguntar(q: str) -> str:
    hallazgos = vida.buscar(q)
    if not hallazgos:
        return f"No hay nada sobre «{q}» en el conocimiento ni en la bóveda."
    return "\n".join(f"{ruta}: {frag}" for ruta, frag in hallazgos)


@servidor.tool(description="Deja algo anotado. tipo: decision | idea | hecho | supuesto | pendiente. Un supuesto se vuelve a revisar solo.")
def anotar(texto: str, tipo: str = "hecho", revisar_en_dias: int = 14) -> str:
    return vida.agregar(texto, tipo, revisar_en_dias)


@servidor.tool(description="Supuestos abiertos que ya toca confirmar o dar por rotos.")
def supuestos() -> str:
    v = vida._supuestos_vencidos(vida._hoy())
    return "\n".join(v) if v else "No hay supuestos por revisar hoy."


if __name__ == "__main__":
    servidor.run()

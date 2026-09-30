"""Fase 4 · espejo de Notion: proyectos y entregas, ida y vuelta.

Solo campos de OPERACIÓN viajan de Notion hacia Remi — «próxima acción» y el
estado de una entrega. La prosa del libro (Quedaste/Decisiones) y los
episodios nunca vuelven: eso sale solo de la máquina (Biblia Parte IV,
ARQUITECTURA-CEREBRO §7 y §12).

Sin evidencia de cambio en Notion, no se toca nada. Si cambió en los dos
lados, gana el más reciente y queda anotado en `remi-mente/bitacora.md` (vía
`boveda_git`, con su commit antes y después).

`sincronizar()` es lo único que llama `scripts/instalar.sh` (LaunchAgent
`com.remi.notion`, cada 15 min) y la ruta `POST /notion/sincronizar`. Sin
`NOTION_TOKEN` o `NOTION_PAGINA_ID`, se salta entero — nunca tumba el núcleo.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import boveda_git
import db
import entregas
import estado_libro
import libros
import notion

ESTADOS_ENTREGA = ("camino", "entregada", "pagada")

ESQUEMA_PROYECTOS: dict[str, Any] = {
    "Título": {"title": {}},
    "Id": {"rich_text": {}},
    "Estado": {"rich_text": {}},
    "Próxima acción": {"rich_text": {}},
    "Entrega": {"date": {}},
    "Monto": {"number": {}},
    "Estado de entrega": {"select": {"options": [{"name": e} for e in ESTADOS_ENTREGA]}},
}

ESQUEMA_ENTREGAS: dict[str, Any] = {
    "Cliente": {"title": {}},
    "Id": {"rich_text": {}},
    "Proyecto": {"rich_text": {}},
    "Fecha": {"date": {}},
    "Monto": {"number": {}},
    "Estado": {"select": {"options": [{"name": e} for e in ESTADOS_ENTREGA]}},
}


def _id_de_proyecto(tema: str) -> UUID:
    """Mismo esquema determinístico que `entregas._proyecto_id_de_tema`: así
    el `proyecto_id` de una Entrega y el «Id» del libro en Notion coinciden
    sin necesitar una tabla de mapeo nueva."""
    return uuid5(NAMESPACE_URL, f"remi:proyecto:{tema or 'sin-proyecto'}")


def _ruta_cache() -> Path:
    return libros.carpeta().parent / ".notion-estado.json"


def _cache_leer() -> dict[str, Any]:
    ruta = _ruta_cache()
    if not ruta.exists():
        return {"proyectos": {}, "entregas": {}}
    try:
        datos = json.loads(ruta.read_text())
    except (json.JSONDecodeError, OSError):
        return {"proyectos": {}, "entregas": {}}
    datos.setdefault("proyectos", {})
    datos.setdefault("entregas", {})
    return datos


def _cache_guardar(datos: dict[str, Any]) -> None:
    _ruta_cache().write_text(json.dumps(datos, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def _proxima_accion_de(estado_texto: str) -> str:
    """La última frase, sin la etiqueta «Próximo paso:»."""
    for linea in estado_texto.splitlines():
        if linea.strip().lower().startswith(("próximo paso:", "proximo paso:")):
            return linea.split(":", 1)[1].strip()
    return ""


def _con_proxima_accion(estado_texto: str, nueva: str) -> str:
    """Reemplaza solo la línea «Próximo paso:»; Quedaste/Decisiones intactos."""
    lineas = estado_texto.splitlines() or ["Quedaste: sin datos.", "Decisiones: ninguna nueva."]
    reemplazada = False
    resultado = []
    for linea in lineas:
        if linea.strip().lower().startswith(("próximo paso:", "proximo paso:")):
            resultado.append(f"Próximo paso: {nueva}")
            reemplazada = True
        else:
            resultado.append(linea)
    if not reemplazada:
        resultado.append(f"Próximo paso: {nueva}")
    return "\n".join(resultado)


def _anotar_conflicto(linea: str) -> None:
    raiz = boveda_git.raiz()
    archivo = raiz / "bitacora.md"
    boveda_git.snapshot_antes("la bitácora, antes de anotar un conflicto de Notion")
    encabezado = "# Bitácora\n\n" if not archivo.exists() else ""
    marca = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with archivo.open("a") as f:
        if encabezado:
            f.write(encabezado)
        f.write(f"- {marca} · {linea}\n")
    boveda_git.snapshot_despues(f"bitácora: conflicto de Notion — {linea}")


@dataclass
class ResumenSync:
    saltado: bool = False
    motivo: str | None = None
    proyectos_creados: int = 0
    proyectos_actualizados: int = 0
    entregas_creadas: int = 0
    entregas_actualizadas: int = 0
    conflictos: int = 0


def _mas_reciente_es_notion(archivo_local: Path, ultima_edicion_notion: str | None) -> bool:
    if not ultima_edicion_notion:
        return False
    try:
        mtime_local = datetime.fromtimestamp(archivo_local.stat().st_mtime, tz=timezone.utc)
        editado_notion = datetime.fromisoformat(ultima_edicion_notion.replace("Z", "+00:00"))
    except (OSError, ValueError):
        return False
    return editado_notion > mtime_local


def _propiedades_proyecto(
    titulo: str, id_libro: str, estado_texto: str, proxima_accion: str, entrega: Any
) -> dict[str, Any]:
    propiedades = {
        "Título": notion.prop_titulo(titulo),
        "Id": notion.prop_texto(id_libro),
        "Estado": notion.prop_texto(estado_texto or "(sin Estado todavía)"),
        "Próxima acción": notion.prop_texto(proxima_accion),
    }
    if entrega is not None:
        propiedades["Entrega"] = notion.prop_fecha(entrega.fecha.date())
        propiedades["Monto"] = notion.prop_numero(entrega.monto)
        propiedades["Estado de entrega"] = notion.prop_seleccion(entrega.estado)
    return propiedades


def _propiedades_entrega(entrega: Any, id_proyecto: str) -> dict[str, Any]:
    return {
        "Cliente": notion.prop_titulo(entrega.cliente),
        "Id": notion.prop_texto(str(entrega.id)),
        "Proyecto": notion.prop_texto(id_proyecto),
        "Fecha": notion.prop_fecha(entrega.fecha.date()),
        "Monto": notion.prop_numero(entrega.monto),
        "Estado": notion.prop_seleccion(entrega.estado),
    }


def _por_id(cliente: notion.Notion, base_id: str) -> dict[str, str]:
    """`{Id -> pagina_id}` de lo que ya hay en la base. Reconcilia si se
    perdió `.notion-estado.json`: sin esto, un cache vacío crearía una
    página duplicada por cada libro o entrega que ya tenía la suya."""
    return {
        notion.leer_texto(pagina["properties"].get("Id")): pagina["id"]
        for pagina in cliente.consultar_base(base_id)
        if notion.leer_texto(pagina["properties"].get("Id"))
    }


def _sincronizar_proyecto(
    cliente: notion.Notion,
    base_id: str,
    libro: libros.Libro,
    conexion: Any,
    cache: dict[str, Any],
    existentes: dict[str, str],
    resumen: ResumenSync,
) -> None:
    id_libro = str(_id_de_proyecto(libro.tema))
    estado_texto = estado_libro.leer_estado(libro.archivo)
    proxima_local = _proxima_accion_de(estado_texto)
    entrega = entregas.entrega_del_proyecto(conexion, _id_de_proyecto(libro.tema))

    previo = cache["proyectos"].get(id_libro)
    if previo is None or not previo.get("pagina_id"):
        pagina_id = existentes.get(id_libro)
        if pagina_id is None:
            pagina_id = cliente.crear_pagina(
                base_id, _propiedades_proyecto(libro.titulo, id_libro, estado_texto, proxima_local, entrega)
            )
            resumen.proyectos_creados += 1
        cache["proyectos"][id_libro] = {
            "pagina_id": pagina_id,
            "proxima_accion": proxima_local,
            "estado_entrega": entrega.estado if entrega else None,
        }
        return

    pagina_id = previo["pagina_id"]
    pagina = cliente.obtener_pagina(pagina_id)
    proxima_remota = notion.leer_texto(pagina["properties"].get("Próxima acción"))
    cambio_local = proxima_local != previo.get("proxima_accion")
    cambio_remoto = proxima_remota != previo.get("proxima_accion")

    proxima_final = proxima_local
    if cambio_remoto and proxima_remota != proxima_local:
        if cambio_local:
            notion_gana = _mas_reciente_es_notion(libro.archivo, pagina.get("last_edited_time"))
            resumen.conflictos += 1
            _anotar_conflicto(
                f"«Próxima acción» de «{libro.titulo}»: cambió en los dos lados, "
                f"ganó {'Notion' if notion_gana else 'Remi'}."
            )
            proxima_final = proxima_remota if notion_gana else proxima_local
        else:
            proxima_final = proxima_remota
        if proxima_final == proxima_remota:
            boveda_git.snapshot_antes(f"la Próxima acción de {libro.archivo.name} (vino de Notion)")
            estado_libro.escribir_estado(libro.archivo, _con_proxima_accion(estado_texto, proxima_remota))
            boveda_git.snapshot_despues(
                f"bóveda: Próxima acción de {libro.archivo.name} actualizada desde Notion"
            )
            estado_texto = estado_libro.leer_estado(libro.archivo)

    estado_entrega_final: str | None = entrega.estado if entrega else None
    if entrega is not None:
        estado_entrega_remoto = notion.leer_seleccion(pagina["properties"].get("Estado de entrega"))
        if (
            estado_entrega_remoto in ESTADOS_ENTREGA
            and estado_entrega_remoto != entrega.estado
            and estado_entrega_remoto != previo.get("estado_entrega")
        ):
            entregas.actualizar_estado_entrega(conexion, entrega.id, estado_entrega_remoto)
            estado_entrega_final = estado_entrega_remoto

    cliente.actualizar_pagina(
        pagina_id, _propiedades_proyecto(libro.titulo, id_libro, estado_texto, proxima_final, entrega)
    )
    cache["proyectos"][id_libro] = {
        "pagina_id": pagina_id,
        "proxima_accion": proxima_final,
        "estado_entrega": estado_entrega_final,
    }
    resumen.proyectos_actualizados += 1


def _sincronizar_entrega(
    cliente: notion.Notion,
    base_id: str,
    entrega: Any,
    conexion: Any,
    cache: dict[str, Any],
    existentes: dict[str, str],
    resumen: ResumenSync,
) -> None:
    clave = str(entrega.id)
    id_proyecto = str(entrega.proyecto_id)
    previo = cache["entregas"].get(clave)

    if previo is None or not previo.get("pagina_id"):
        pagina_id = existentes.get(clave)
        if pagina_id is None:
            pagina_id = cliente.crear_pagina(base_id, _propiedades_entrega(entrega, id_proyecto))
            resumen.entregas_creadas += 1
        cache["entregas"][clave] = {"pagina_id": pagina_id, "estado": entrega.estado}
        return

    pagina_id = previo["pagina_id"]
    pagina = cliente.obtener_pagina(pagina_id)
    estado_remoto = notion.leer_seleccion(pagina["properties"].get("Estado"))
    estado_final = entrega.estado

    if estado_remoto in ESTADOS_ENTREGA and estado_remoto != entrega.estado:
        cambio_local = entrega.estado != previo.get("estado")
        if cambio_local and estado_remoto != previo.get("estado"):
            # Sin marca de tiempo local para una Entrega (el contrato no la
            # trae): gana Notion, y queda anotado igual que un conflicto de
            # proyecto — nunca se pisa en silencio.
            resumen.conflictos += 1
            _anotar_conflicto(
                f"Estado de la entrega de «{entrega.cliente}»: cambió en los dos lados, ganó Notion "
                f"(sin dato de tiempo local para decidir)."
            )
        entregas.actualizar_estado_entrega(conexion, entrega.id, estado_remoto)
        estado_final = estado_remoto

    cliente.actualizar_pagina(pagina_id, _propiedades_entrega(entrega, id_proyecto))
    if estado_final != entrega.estado:
        entrega = entregas.leer_entrega(conexion, entrega.id) or entrega
    cache["entregas"][clave] = {"pagina_id": pagina_id, "estado": estado_final}
    resumen.entregas_actualizadas += 1


def sincronizar(cliente: notion.Notion | None = None) -> ResumenSync:
    llave = notion.token()
    raiz = notion.pagina_id()
    if not llave or not raiz:
        motivo = "sin NOTION_TOKEN" if not llave else "sin NOTION_PAGINA_ID"
        print(f"[notion] {motivo} en nucleo/.env: sync salteado, el núcleo sigue andando", file=sys.stderr)
        return ResumenSync(saltado=True, motivo=motivo)

    cliente = cliente or notion.Notion(llave)
    resumen = ResumenSync()
    cache = _cache_leer()

    base_proyectos = cliente.buscar_base(raiz, "Proyectos") or cliente.crear_base(raiz, "Proyectos", ESQUEMA_PROYECTOS)
    base_entregas = cliente.buscar_base(raiz, "Entregas") or cliente.crear_base(raiz, "Entregas", ESQUEMA_ENTREGAS)

    existentes_proyectos = _por_id(cliente, base_proyectos)
    existentes_entregas = _por_id(cliente, base_entregas)

    conexion = db.conectar()
    try:
        for libro in libros.listar():
            if not libro.compartible:
                continue
            _sincronizar_proyecto(cliente, base_proyectos, libro, conexion, cache, existentes_proyectos, resumen)

        for entrega in entregas.listar_entregas(conexion):
            if not entrega.compartible:
                continue
            _sincronizar_entrega(cliente, base_entregas, entrega, conexion, cache, existentes_entregas, resumen)
    finally:
        conexion.close()

    _cache_guardar(cache)
    return resumen


if __name__ == "__main__":
    resultado = sincronizar()
    print(json.dumps(asdict(resultado), ensure_ascii=False), file=sys.stderr)

"""Consolidación nocturna (ARQUITECTURA-CEREBRO §6): LaunchAgent com.remi.noche
a las 4:00, después de la copia de restic de las 3:00.

Cuatro pasos, en orden:
1. Episodios de hoy → Estado de cada libro tocado. Solo si hay evidencia real
   (los episodios de hoy son la evidencia); si un libro no tuvo episodios
   hoy, no se toca — mismo mecanismo anti-invento de `estado_libro.py`.
2. Fusiona episodios repetidos del mismo día y el mismo libro (mismo
   resumen exacto — no adivina «parecido»).
3. Recalcula los vectores de lo que cambió (`vectores.py` ya solo recalcula
   si el hash cambió).
4. Reordena la mente: vuelve a sembrar los libros de proyecto
   (`sembrar_conocimiento.sembrar()`), que ahora asigna nivel 1 a lo tocado
   en los últimos 7 días y nivel 2 al resto — nunca borra nada.

Nada de esto borra una nota: lo que no se toca baja de nivel, no desaparece.

    uv run python noche.py          # a mano, ahora mismo
    (LaunchAgent com.remi.noche la corre a las 4:00)

Log: ~/Library/Logs/Remi/noche.log — lo arma `scripts/noche.sh`, igual que
`copia.sh` arma copia.log.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import boveda_git
import db
import estado_libro
import libros
import sembrar_conocimiento
import vectores


def _episodios_de_hoy(carpeta: Path, hoy: date) -> list[Path]:
    if not carpeta.is_dir():
        return []
    prefijo = hoy.isoformat()
    return sorted(p for p in carpeta.glob(f"{prefijo}-*.md") if p.is_file())


def _campos(ruta: Path) -> dict[str, str | list[str]]:
    texto = ruta.read_text()
    if not texto.startswith("---"):
        return {}
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return {}
    return libros._frontmatter(partes[1])


def _tema_de(ruta: Path) -> str | None:
    tema = _campos(ruta).get("tema")
    return tema if isinstance(tema, str) and tema else None


def _resumen_bullet(ruta: Path) -> str:
    campos = _campos(ruta)
    titulo = campos.get("titulo")
    resumen = campos.get("resumen")
    piezas = [p for p in (titulo, resumen) if isinstance(p, str) and p]
    return " — ".join(piezas) if piezas else ruta.stem


def _libro_por_tema(tema: str) -> libros.Libro | None:
    for libro in libros.listar():
        if libro.tema == tema:
            return libro
    return None


def _agrupar_por_tema(rutas: list[Path]) -> dict[str, list[Path]]:
    por_tema: dict[str, list[Path]] = defaultdict(list)
    for ruta in rutas:
        por_tema[_tema_de(ruta) or "(sin tema)"].append(ruta)
    return dict(por_tema)


def actualizar_estados_del_dia(hoy: date | None = None) -> dict[str, str]:
    """{tema: "actualizado" | "sin_evidencia_nueva" | "sin_libro"}.

    Un episodio solo cuenta como evidencia si es más nuevo que la última vez
    que se escribió el Estado de ese libro (mtime del archivo). Si no, un
    episodio de hoy sobre algo que ya se resolvió antes de hoy podría
    pisar, noche tras noche, una corrección manual más reciente que el
    episodio mismo — es lo que pasó de verdad al probar esto (ver
    docs/BITACORA.md): re-derivó un «Próximo paso» viejo sobre uno que
    Juan Camilo ya había confirmado a mano ese mismo día."""
    hoy = hoy or datetime.now(timezone.utc).date()
    carpeta_episodios = libros.carpeta().parent / "episodios"
    por_tema = _agrupar_por_tema(_episodios_de_hoy(carpeta_episodios, hoy))

    resultado: dict[str, str] = {}
    for tema, episodios_de_tema in por_tema.items():
        libro = _libro_por_tema(tema)
        if libro is None:
            resultado[tema] = "sin_libro"
            continue
        mtime_estado = libro.archivo.stat().st_mtime
        episodios_de_tema = [ep for ep in episodios_de_tema if ep.stat().st_mtime > mtime_estado]
        if not episodios_de_tema:
            resultado[tema] = "sin_evidencia_nueva"
            continue
        anterior = estado_libro.leer_estado(libro.archivo)
        lineas = [f"Proyecto: {libro.titulo}", ""]
        if anterior.strip():
            lineas += ["Estado anterior:", anterior.strip(), ""]
        lineas.append("Commits nuevos:")
        for ep in episodios_de_tema:
            lineas.append(f"- {_resumen_bullet(ep)}")
        pedido = "\n".join(lineas)[:4000]
        nuevo = estado_libro.redactar(pedido)
        if nuevo is None:
            # redactar() no distingue por qué devolvió None; lo único que se
            # puede afirmar sin pedido no trae evidencia es "sin evidencia
            # nueva" — si sí traía y aun así no hubo texto, o el modelo
            # inventó y la verificación mecánica lo rechazó (el motivo
            # exacto queda en stderr/noche.log como "rechazado por invento").
            resultado[tema] = (
                "sin_evidencia_nueva" if estado_libro.sin_evidencia_nueva(pedido) else "rechazado_o_sin_respuesta"
            )
            continue
        boveda_git.snapshot_antes(f"consolidación nocturna: Estado de {libro.archivo.name}")
        estado_libro.escribir_estado(libro.archivo, nuevo)
        boveda_git.snapshot_despues(
            f"bóveda: consolidación nocturna actualiza el Estado de {libro.archivo.name}"
            f" ({len(episodios_de_tema)} episodio(s) de hoy)"
        )
        resultado[tema] = "actualizado"
    return resultado


def _normalizar_resumen(ruta: Path) -> str:
    resumen = _campos(ruta).get("resumen")
    return re.sub(r"\s+", " ", resumen.strip().lower()) if isinstance(resumen, str) else ""


def fusionar_episodios_del_dia(hoy: date | None = None) -> list[tuple[str, str]]:
    """[(mantenido, fusionado)] — solo cuando dos episodios del mismo día y
    tema tienen el mismo resumen exacto. El que se fusiona no desaparece sin
    rastro: su contenido queda anexado al que se mantiene, y el commit de la
    bóveda deja el revert real."""
    hoy = hoy or datetime.now(timezone.utc).date()
    carpeta_episodios = libros.carpeta().parent / "episodios"
    por_tema = _agrupar_por_tema(_episodios_de_hoy(carpeta_episodios, hoy))

    fusiones: list[tuple[str, str]] = []
    for rutas in por_tema.values():
        if len(rutas) < 2:
            continue
        vistos: dict[str, Path] = {}
        for ruta in sorted(rutas):
            clave = _normalizar_resumen(ruta)
            if not clave:
                continue
            if clave not in vistos:
                vistos[clave] = ruta
                continue
            mantenido = vistos[clave]
            boveda_git.snapshot_antes(f"fusionar episodio repetido {ruta.name} en {mantenido.name}")
            texto_extra = ruta.read_text()
            mantenido.write_text(
                mantenido.read_text().rstrip()
                + f"\n\n---\n\nFusionado con `{ruta.name}` (mismo resumen, mismo día):\n\n"
                + texto_extra
            )
            ruta.unlink()
            boveda_git.snapshot_despues(f"bóveda: fusiona {ruta.name} en {mantenido.name} (episodios repetidos del día)")
            fusiones.append((mantenido.name, ruta.name))
    return fusiones


def recalcular_vectores() -> int:
    conexion = db.conectar()
    try:
        return vectores.actualizar_todos(conexion)
    finally:
        conexion.close()


def reordenar_mente() -> dict[str, int]:
    """Vuelve a sembrar los libros de proyecto: el nivel de cada uno se
    recalcula por su mtime (nivel_de en sembrar_conocimiento.py) — lo tocado
    en 7 días sube a nivel 1, el resto baja a nivel 2. Nunca borra nada."""
    return sembrar_conocimiento.sembrar()


def correr(hoy: date | None = None) -> None:
    arranque = datetime.now(timezone.utc)
    print(f"[noche] arranca {arranque.isoformat()}")

    estados = actualizar_estados_del_dia(hoy)
    for tema, resultado in estados.items():
        print(f"[noche] estado tema={tema} resultado={resultado}")
    if not estados:
        print("[noche] estado: no hubo episodios hoy, ningún libro tocado")

    fusiones = fusionar_episodios_del_dia(hoy)
    for mantenido, fusionado in fusiones:
        print(f"[noche] fusión mantenido={mantenido} fusionado={fusionado}")
    if not fusiones:
        print("[noche] fusión: no había episodios repetidos hoy")

    recalculadas = recalcular_vectores()
    print(f"[noche] vectores recalculadas={recalculadas}")

    cuenta = reordenar_mente()
    print(
        "[noche] reordenar "
        + " ".join(f"{clave}={valor}" for clave, valor in cuenta.items())
    )

    fin = datetime.now(timezone.utc)
    print(f"[noche] termina {fin.isoformat()} duracion_s={(fin - arranque).total_seconds():.1f}")


if __name__ == "__main__":
    correr()

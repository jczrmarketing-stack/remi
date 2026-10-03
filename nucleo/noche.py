"""Consolidación nocturna (ARQUITECTURA-CEREBRO §6): LaunchAgent com.remi.noche
a las 4:00, después de la copia de restic de las 3:00.

Cinco pasos, en orden:
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
5. Reporte de la noche (reemplaza la entrega por voz, descartada): compara
   el HEAD de la bóveda al arrancar contra el de ahora y manda por
   `POST /telegram/avisar` «Anoche cambié N libros» con hasta 3 diffs cortos
   (8 líneas c/u), o «Anoche no toqué nada» si no hubo cambios.

Nada de esto borra una nota: lo que no se toca baja de nivel, no desaparece.

    uv run python noche.py          # a mano, ahora mismo
    (LaunchAgent com.remi.noche la corre a las 4:00)

Log: ~/Library/Logs/Remi/noche.log — lo arma `scripts/noche.sh`, igual que
`copia.sh` arma copia.log.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

import boveda_git
import db
import estado_libro
import experiencia
import libros
import preguntas
import sembrar_conocimiento
import telegram
import vectores

RUTA_CONFIG_SERVIDOR = Path(__file__).resolve().parent.parent / "config" / "nucleo.json"


def _episodios_de_hoy(carpeta: Path, hoy: date) -> list[Path]:
    if not carpeta.is_dir():
        return []
    prefijo = hoy.isoformat()
    return sorted(p for p in carpeta.glob(f"{prefijo}-*.md") if p.is_file() and not libros.fuera_del_estante(p))


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


def _head_git() -> str | None:
    """El HEAD de la bóveda antes de que esta corrida toque nada, o None si
    la bóveda no es un repo git todavía (o no tiene ningún commit) — mismo
    criterio de `boveda_git._es_repo`."""
    raiz = boveda_git.raiz()
    if not (raiz / ".git").is_dir():
        return None
    try:
        resultado = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        return None
    return resultado.stdout.strip()


def _recortar_diff(diff: str, max_lineas: int) -> str:
    """Las primeras líneas de `git diff` son cabecera (`diff --git`, `index`,
    `---`/`+++`) — recortar el texto crudo a `max_lineas` se comía el cambio
    real antes de llegar a él. Se arranca desde el primer `@@` (el hunk) si
    hay uno; si no (archivo nuevo/borrado sin hunk, o binario), se recorta
    tal cual."""
    lineas = diff.splitlines()
    for i, linea in enumerate(lineas):
        if linea.startswith("@@"):
            lineas = lineas[i:]
            break
    return "\n".join(lineas[:max_lineas])


def diff_de_la_noche(referencia: str | None, max_lineas: int = 8) -> list[tuple[str, str]]:
    """[(libro, diff_corto)] de lo que tocó esta corrida en la carpeta de
    libros (`libros.carpeta()`), comparado contra `referencia` (el HEAD de
    la bóveda al arrancar `correr()`). Cada diff se recorta a `max_lineas`
    líneas de hunk (`_recortar_diff`); el nombre es el título del libro si
    todavía se puede leer, o el nombre de archivo si no (por ejemplo si el
    libro se borró en la corrida)."""
    if referencia is None:
        return []
    raiz = boveda_git.raiz()
    try:
        nombres = subprocess.run(
            ["git", "-C", str(raiz), "diff", "--name-only", referencia, "--", str(libros.carpeta())],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
    except subprocess.CalledProcessError:
        return []

    cambios: list[tuple[str, str]] = []
    for nombre_relativo in sorted(nombre for nombre in nombres if nombre):
        try:
            diff = subprocess.run(
                ["git", "-C", str(raiz), "diff", referencia, "--", nombre_relativo],
                capture_output=True, text=True, check=True,
            ).stdout
        except subprocess.CalledProcessError:
            continue
        ruta_absoluta = raiz / nombre_relativo
        libro = libros.leer(ruta_absoluta) if ruta_absoluta.exists() else None
        etiqueta = libro.titulo if libro is not None else Path(nombre_relativo).stem
        cambios.append((etiqueta, _recortar_diff(diff, max_lineas)))
    return cambios


def _url_avisar() -> str:
    config = json.loads(RUTA_CONFIG_SERVIDOR.read_text())
    return f"http://{config['host']}:{config['puerto']}/telegram/avisar"


def enviar_reporte_de_la_noche(cambios: list[tuple[str, str]]) -> None:
    """POST a `/telegram/avisar` (nunca en proceso: `noche.py` corre aparte
    del servidor) con el resumen de esta corrida. `urgente: true` porque la
    consolidación corre a las 4:00, dentro del silencio 23:00–7:00 — sin
    eso, `avisar()` lo descartaría en silencio y el reporte nunca llegaría
    (no hay cola ni reintento). Un fallo acá no puede tumbar la
    consolidación — mismo criterio de `boveda_git._commit`: se anota en
    stderr y sigue."""
    texto = telegram.mensaje_reporte_noche(cambios)
    try:
        httpx.post(_url_avisar(), json={"texto": texto, "urgente": True}, timeout=10)
    except Exception as error:  # noqa: BLE001 — un aviso que falla no tumba la noche
        print(f"[noche] no pude mandar el reporte de la noche ({type(error).__name__}): {error}", file=sys.stderr, flush=True)


def correr(hoy: date | None = None) -> None:
    arranque = datetime.now(timezone.utc)
    print(f"[noche] arranca {arranque.isoformat()}")
    referencia = _head_git()

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

    cambios = diff_de_la_noche(referencia)
    enviar_reporte_de_la_noche(cambios)
    print(f"[noche] reporte libros_cambiados={len(cambios)}")

    # T3.6: la pregunta pendiente más vieja, por Telegram — una vez al día
    # como mucho (preguntas.py ya cuida eso).
    conexion = db.conectar()
    try:
        preguntada = preguntas.avisar_por_telegram_si_toca(conexion, arranque)
    finally:
        conexion.close()
    print(f"[noche] pregunta por telegram={'sí' if preguntada else 'no'}")

    # T8.4: la nota de las sesiones de hace 48 h, revisada contra lo que
    # pasó después.
    revisados = experiencia.revisar_resultados_pendientes(arranque)
    print(f"[noche] resultados revisados (48h)={revisados}")

    # T9.5: las conversaciones de la ventanita/Telegram, 60 min sin
    # turnos, también dejan episodio si tuvieron sustancia.
    import cierre

    conversaciones_cerradas = cierre.cerrar_conversaciones_inactivas(arranque)
    print(f"[noche] conversaciones con episodio={conversaciones_cerradas}")

    fin = datetime.now(timezone.utc)
    print(f"[noche] termina {fin.isoformat()} duracion_s={(fin - arranque).total_seconds():.1f}")


if __name__ == "__main__":
    correr()

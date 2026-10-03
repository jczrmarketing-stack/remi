#!/usr/bin/env python3
"""El banco de la revisión (docs/PLAN-REVISION.md, R0): un núcleo de prueba
aislado para probar a Remi sin tocar nada real.

    python3 scripts/banco.py arrancar     copia la base y la bóveda, levanta :4499
    python3 scripts/banco.py frases       manda el guion de frases y muestra qué contestó
    python3 scripts/banco.py parar        apaga el núcleo de prueba

La copia vive en $TMPDIR/remi-banco (se rehace en cada `arrancar`). La base y
la bóveda reales solo se leen para copiarlas. Telegram apagado, sin precalentar
la voz. La guarda F4.2b del núcleo exige la bóveda aislada: si esto la apuntara
a la real, el núcleo no arrancaría.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = Path(tempfile.gettempdir()) / "remi-banco"
PUERTO = 4499
URL = f"http://127.0.0.1:{PUERTO}"

# El guion fijo (R0.3): una frase por cada camino del clasificador y del
# cerebro, para que cada corrida sea comparable con la anterior.
GUION: list[tuple[str, dict[str, object]]] = [
    ("cortesía", {"texto": "Gracias."}),
    ("idea", {"texto": "una app que ordene las facturas del mes sola"}),
    ("anota esto", {"texto": "anota esto: comprar cable usb-c"}),
    ("tarea de hoy", {"texto": "voy a llamar al banco"}),
    ("cierre", {"texto": "listo, ya terminé"}),
    ("pregunta sin pensar", {"texto": "¿qué tengo pendiente hoy?"}),
    ("pregunta pensando", {"texto": "¿qué tengo pendiente hoy?", "think": True, "motor": "claude", "modo": "rapido"}),
    ("charla", {"texto": "¿qué opinas de que trabaje el sábado?", "think": True, "motor": "claude", "modo": "rapido"}),
    ("encargo", {"texto": "ordena esto en un prompt: arreglar el login que se cae cuando el token vence", "think": True, "motor": "claude", "modo": "prompt"}),
    ("cliente", {"texto": "me escribió Alfonso: ¿pueden bajar el precio de la fase 1?", "think": True, "motor": "claude", "modo": "rapido"}),
    ("estado propio", {"texto": "¿estás funcionando bien? ¿qué te falta?", "think": True, "motor": "claude", "modo": "rapido"}),
]


def _pedido(ruta: str, cuerpo: dict[str, object] | None = None, metodo: str = "GET") -> object:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else (b"" if metodo == "POST" else None)
    pedido = urllib.request.Request(URL + ruta, data=datos, method=metodo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=300) as respuesta:
        texto = respuesta.read()
        return json.loads(texto) if texto else None


def _arriba() -> bool:
    try:
        _pedido("/salud")
        return True
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return False


def _pid_en_el_puerto() -> list[int]:
    salida = subprocess.run(["lsof", "-nP", f"-tiTCP:{PUERTO}", "-sTCP:LISTEN"], capture_output=True, text=True)
    return [int(p) for p in salida.stdout.split()]


def parar() -> None:
    for pid in _pid_en_el_puerto():
        orden = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
        if "uvicorn servidor:app" in orden:
            os.kill(pid, signal.SIGTERM)
            print(f"banco: apagado (pid {pid})")
        else:
            print(f"banco: :{PUERTO} lo usa otra cosa ({orden.strip()}), no la toco")


def arrancar() -> None:
    if _pid_en_el_puerto():
        parar()
        time.sleep(1)
    if BANCO.exists():
        shutil.rmtree(BANCO)
    BANCO.mkdir(parents=True)
    shutil.copytree((RAIZ / "conocimiento").resolve(), BANCO / "boveda", ignore=shutil.ignore_patterns(".obsidian"))
    shutil.copyfile(RAIZ / "nucleo" / "remi.db", BANCO / "remi.db")
    entorno = dict(os.environ)
    entorno.update(
        REMI_DB_PATH=str(BANCO / "remi.db"),
        REMI_CONOCIMIENTO=str(BANCO / "boveda" / "proyectos"),
        REMI_BOVEDA=str(BANCO / "boveda"),
        REMI_TELEGRAM="0",
        REMI_TTS_PRECALENTAR="0",
    )
    log = open(BANCO / "nucleo.log", "w")
    subprocess.Popen(
        ["uv", "run", "uvicorn", "servidor:app", "--host", "127.0.0.1", "--port", str(PUERTO)],
        cwd=RAIZ / "nucleo", env=entorno, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    for _ in range(90):
        if _arriba():
            print(f"banco: arriba en {URL} · copia en {BANCO} · log en {BANCO / 'nucleo.log'}")
            return
        time.sleep(1)
    print(f"banco: no arrancó en 90 s; mira {BANCO / 'nucleo.log'}", file=sys.stderr)
    sys.exit(1)


def frases() -> None:
    if not _arriba():
        print("banco: no está arriba (python3 scripts/banco.py arrancar)", file=sys.stderr)
        sys.exit(1)
    for nombre, cuerpo in GUION:
        _pedido("/conversaciones/nueva", metodo="POST")
        arranque = time.perf_counter()
        respuesta = _pedido("/mensaje", cuerpo, "POST")
        ms = (time.perf_counter() - arranque) * 1000
        assert isinstance(respuesta, dict)
        tarea = respuesta.get("tarea")
        print(f"— {nombre} ({ms:.0f} ms) · tipo={respuesta.get('tipo')} · tarea={'sí' if tarea else 'no'} · motor={respuesta.get('motor_usado') or '-'}")
        print("  " + str(respuesta.get("texto") or respuesta.get("voz"))[:400].replace("\n", " ⏎ "))


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else ""
    {"arrancar": arrancar, "parar": parar, "frases": frases}.get(accion, lambda: print(__doc__))()

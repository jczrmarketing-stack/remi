#!/usr/bin/env python3
"""SessionStart y SessionEnd de Claude Code, hacia el núcleo de Remi.

Al abrir, imprime el contexto del proyecto para que Claude lo reciba.
Al cerrar, manda la sesión. Si el núcleo no está, no imprime nada y sale 0:
abrir o cerrar Claude no depende de Remi.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

# B3.2: lo que _armar_encargo (servidor.py) antepone a un encargo que
# cierra un hito con evidencia de código. Juan Camilo pega ese encargo
# como el primer mensaje de la sesión nueva; el gancho SessionEnd lee el
# transcript y lo manda como datos["hito"], para no depender de que nadie
# lo recuerde ni de adivinarlo por el título.
_HITO = re.compile(r"^hito:\s*([a-z0-9][a-z0-9_-]*)#(\d+)\s*$", re.IGNORECASE | re.MULTILINE)


def _texto_del_contenido(contenido: object) -> str | None:
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        trozos = [b.get("text", "") for b in contenido if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(trozos) if trozos else None
    return None


def hito_del_primer_turno(transcript_path: str) -> str | None:
    """«tema#n» si el primer turno del usuario empieza con `hito: …`.
    None ante cualquier problema (sin archivo, JSON roto, vacío): nunca
    rompe el cierre de la sesión por esto."""
    if not transcript_path:
        return None
    try:
        with open(transcript_path, encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    entrada = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entrada, dict) or entrada.get("type") != "user":
                    continue
                mensaje = entrada.get("message")
                contenido = mensaje.get("content") if isinstance(mensaje, dict) else None
                texto = _texto_del_contenido(contenido)
                if texto is None:
                    continue
                coincidencia = _HITO.search(texto)
                return f"{coincidencia.group(1)}#{coincidencia.group(2)}" if coincidencia else None
    except OSError:
        return None
    return None


def _post(tipo: str, ruta: str, datos: dict[str, object]) -> dict[str, object] | None:
    base = os.environ.get("REMI_NUCLEO_URL", "http://127.0.0.1:4400").rstrip("/")
    url = base if base.endswith("/evento") else f"{base}/evento"
    cuerpo = json.dumps({"tipo": tipo, "ruta": ruta, "datos": datos}, ensure_ascii=False).encode()
    pedido = urllib.request.Request(
        url, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(pedido, timeout=2) as respuesta:
            crudo = respuesta.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        # Si el núcleo está caído al cerrar la sesión, el episodio se pierde
        # en silencio (ARQUITECTURA §12: "el hook le avisa solo"). Dejamos
        # rastro en el log de la ventanita para poder diagnosticarlo, en vez
        # de que la carpeta de episodios simplemente quede vacía sin motivo.
        try:
            log = os.path.expanduser("~/Library/Logs/Remi/ventanita.log")
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "a") as archivo:
                archivo.write(f"[gancho] {tipo} no llegó al núcleo ({type(error).__name__}): {error}\n")
        except OSError:
            pass
        return None
    try:
        datos_respuesta = json.loads(crudo) if crudo.strip() else {}
    except json.JSONDecodeError:
        return None
    return datos_respuesta if isinstance(datos_respuesta, dict) else None


def main() -> int:
    try:
        crudo = sys.stdin.read()
        evento = json.loads(crudo) if crudo.strip() else {}
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(evento, dict):
        return 0
    nombre = str(evento.get("hook_event_name") or "")
    ruta = str(evento.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "")
    datos = {
        "session_id": str(evento.get("session_id") or ""),
        "transcript_path": str(evento.get("transcript_path") or ""),
        "source": str(evento.get("source") or ""),
    }
    if nombre == "SessionStart":
        respuesta = _post("sesion_inicio", ruta, datos)
        contexto = (respuesta or {}).get("contexto")
        if isinstance(contexto, str) and contexto.strip():
            json.dump(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": contexto.strip(),
                    }
                },
                sys.stdout,
                ensure_ascii=False,
            )
            sys.stdout.write("\n")
        return 0
    if nombre == "SessionEnd":
        hito = hito_del_primer_turno(datos["transcript_path"])
        if hito is not None:
            datos["hito"] = hito
        _post("sesion_fin", ruta, datos)
        return 0
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)

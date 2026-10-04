"""B10.2 (PLAN-FINAL.md): accesibilidad de macOS — la app activa y el
título de ventana entran como contexto. Nada sale del Mac: esto solo lee
el frontmost app con AppleScript (`osascript`), nunca manda nada a
ningún servidor.

**ESPERA PERMISO**: Juan Camilo da el permiso de Accesibilidad a mano
(Ajustes del Sistema → Privacidad y Seguridad → Accesibilidad). Sin ese
permiso, `osascript` falla o devuelve vacío — `leer_ventana_activa` lo
atrapa y devuelve `None`, nunca rompe nada. El `lector` se inyecta
siempre (nunca una llamada real de `osascript` en pytest): las pruebas
usan un doble.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable

_SCRIPT_APPLESCRIPT = """
tell application "System Events"
    set elApp to name of first application process whose frontmost is true
end tell
set elTitulo to ""
try
    tell application "System Events"
        tell (first application process whose frontmost is true)
            set elTitulo to name of front window
        end tell
    end tell
end try
return elApp & "|||" & elTitulo
"""


@dataclass(frozen=True)
class VentanaActiva:
    app: str
    titulo: str


LectorVentanaActiva = Callable[[], "VentanaActiva | None"]


def leer_ventana_activa_macos() -> VentanaActiva | None:
    """La implementación real — requiere el permiso de Accesibilidad.
    Cualquier fallo (permiso no dado, osascript ausente, sin GUI) vuelve
    `None`, nunca una excepción que tumbe el llamador."""
    try:
        resultado = subprocess.run(
            ["osascript", "-e", _SCRIPT_APPLESCRIPT], capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if resultado.returncode != 0 or not resultado.stdout.strip():
        return None
    partes = resultado.stdout.strip().split("|||")
    if len(partes) != 2 or not partes[0]:
        return None
    return VentanaActiva(app=partes[0], titulo=partes[1])

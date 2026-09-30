#!/usr/bin/env bash
# Saca a Remi del Mac: baja los dos agentes y borra la app.
#
#     ./scripts/desinstalar.sh
#
# NO toca nucleo/remi.db. Ahí vive todo lo que Remi sabe de vos: tareas,
# sesiones, ideas y memoria. Si alguna vez hay que borrarlo, es a mano y a
# propósito.
set -euo pipefail

ETIQUETA="com.remi.nucleo"
ETIQUETA_APP="com.remi.ventanita"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Remi · desinstalando"

# `bootout` vuelve antes de que el agente termine de irse: sin esperar,
# el script decía «bajado» con el servicio todavía arriba.
for etiqueta in "$ETIQUETA_APP" "$ETIQUETA" "com.remi.whisper" "com.remi.copia" "com.remi.vigia"; do
  plist="$HOME/Library/LaunchAgents/$etiqueta.plist"
  if launchctl list "$etiqueta" > /dev/null 2>&1; then
    launchctl bootout "gui/$UID/$etiqueta" 2>/dev/null \
      || launchctl unload "$plist" 2>/dev/null || true
    for _ in $(seq 1 50); do
      launchctl list "$etiqueta" > /dev/null 2>&1 || break
      sleep 0.2
    done
    if launchctl list "$etiqueta" > /dev/null 2>&1; then
      echo "  $etiqueta no se termina de bajar. A mano: launchctl bootout gui/$UID/$etiqueta" >&2
    else
      echo "  bajado:  $etiqueta"
    fi
  fi
  rm -f "$plist"
done

osascript -e 'quit app "Remi"' 2>/dev/null || true
pkill -f "Remi.app/Contents/MacOS" 2>/dev/null || true

LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [[ -d /Applications/Remi.app ]]; then
  "$LSREGISTER" -u /Applications/Remi.app 2>/dev/null || true
  rm -rf /Applications/Remi.app
  echo "  borrada: /Applications/Remi.app"
fi
# La copia construida en target/ también se llama Remi.app: sin sacarla del
# registro, `open -a Remi` la seguiría abriendo después de desinstalar.
CONSTRUIDA="$RAIZ/apps/ventanita/src-tauri/target/release/bundle/macos/Remi.app"
if [[ -d "$CONSTRUIDA" ]]; then
  "$LSREGISTER" -u "$CONSTRUIDA" 2>/dev/null || true
  echo "  desregistrada la copia de target/ (el .app construido queda en el repo)"
fi

echo
echo "Listo. La base NO se tocó: $RAIZ/nucleo/remi.db"
echo "Los logs siguen en ~/Library/Logs/Remi/ por si querés mirarlos."
echo "Para volver: ./scripts/instalar.sh"

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
for etiqueta in "$ETIQUETA_APP" "$ETIQUETA"; do
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
if [[ -d /Applications/Remi.app ]]; then
  rm -rf /Applications/Remi.app
  echo "  borrada: /Applications/Remi.app"
fi

echo
echo "Listo. La base NO se tocó: $RAIZ/nucleo/remi.db"
echo "Los logs siguen en ~/Library/Logs/Remi/ por si querés mirarlos."
echo "Para volver: ./scripts/instalar.sh"

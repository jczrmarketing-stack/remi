#!/usr/bin/env bash
# Compila Remi y reemplaza la que está instalada. Es la forma de probar una
# fase: `tauri dev` quedó atrás — la app de /Applications es la de verdad,
# la que tiene su propio permiso de micrófono.
#
#     ./scripts/actualizar.sh
#
# No borra target/: la próxima compilación es corta. Al final dice cuánto
# espacio queda.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENTANITA="$RAIZ/apps/ventanita"
CONSTRUIDA="$VENTANITA/src-tauri/target/release/bundle/macos/Remi.app"
INSTALADA="/Applications/Remi.app"
ETIQUETA="com.remi.nucleo"
ETIQUETA_APP="com.remi.ventanita"

echo "Remi · actualizando"
echo "  commit: $(git -C "$RAIZ" log --oneline -1)"
if [[ -n "$(git -C "$RAIZ" status --porcelain)" ]]; then
  echo "  ojo:    hay cambios sin commitear; se instala lo que hay en disco"
fi
echo

echo "Compilando…"
(cd "$VENTANITA" && npm run tauri -- build --bundles app)

if [[ ! -d "$CONSTRUIDA" ]]; then
  echo "No encontré $CONSTRUIDA" >&2
  exit 1
fi

# La app se cierra antes de reemplazarla: copiar encima de un bundle en uso
# deja una mezcla de la vieja y la nueva.
echo
echo "Reemplazando la instalada…"
launchctl bootout "gui/$UID/$ETIQUETA_APP" 2>/dev/null || true
osascript -e 'quit app "Remi"' 2>/dev/null || true
for _ in $(seq 1 25); do
  pgrep -f "$INSTALADA/Contents/MacOS" > /dev/null || break
  sleep 0.2
done
pkill -f "$INSTALADA/Contents/MacOS" 2>/dev/null || true

rm -rf "$INSTALADA"
cp -R "$CONSTRUIDA" "$INSTALADA"

echo "Recargando los agentes…"
"$RAIZ/scripts/instalar.sh" > /dev/null
echo

echo "Instalada la de: $(git -C "$RAIZ" log --oneline -1)"
launchctl list | grep -E "com\.remi\.(nucleo|ventanita)" | grep -v application || true
LIBRE="$(df -H /System/Volumes/Data | tail -1 | awk '{print $4}')"
echo "Espacio libre: $LIBRE"

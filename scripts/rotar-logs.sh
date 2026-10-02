#!/usr/bin/env bash
# Logs de Remi: rotan por tamaño, nunca pierden lo de hoy (T5 · 2).
#
#     ./scripts/rotar-logs.sh
#     (noche.sh la corre una vez al día, antes de la consolidación)
#
# Por archivo: si pasa de MAXIMO_BYTES, una copia a <archivo>.1 (lo que
# había, por si hace falta mirar atrás — nunca se borra) y el archivo
# queda vacío. Vaciarlo con `: >` es seguro con un escritor que sigue con
# el archivo abierto en O_APPEND (launchd StandardOutPath/StandardErrorPath,
# o `tee -a`): es el mismo inodo, el próximo write cae al final del
# archivo ya corto — no hace falta reiniciar ningún proceso.
set -euo pipefail

CARPETA="${REMI_LOGS:-$HOME/Library/Logs/Remi}"
MAXIMO_BYTES=$((10 * 1024 * 1024))  # 10 MiB

[[ -d "$CARPETA" ]] || exit 0

for log in "$CARPETA"/*.log; do
  [[ -f "$log" ]] || continue
  tam=$(stat -f%z "$log" 2>/dev/null || echo 0)
  if (( tam > MAXIMO_BYTES )); then
    cp -f "$log" "$log.1"
    : > "$log"
    echo "rotar-logs: $(basename "$log") rotado ($tam bytes)"
  fi
done

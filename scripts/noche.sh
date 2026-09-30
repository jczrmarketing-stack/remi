#!/usr/bin/env bash
# Consolidación nocturna de Remi (Fase C · 2): episodios del día → Estado de
# los libros tocados, fusiona episodios repetidos, recalcula vectores y
# reordena la mente (ARQUITECTURA-CEREBRO §6). Corre después de la copia.
#
#     ./scripts/noche.sh            # a mano, ahora mismo
#     (LaunchAgent com.remi.noche la corre a las 4:00)
#
# Log: ~/Library/Logs/Remi/noche.log.
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LOG="$HOME/Library/Logs/Remi/noche.log"
mkdir -p "$(dirname "$LOG")"
if [[ -t 1 ]]; then
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done | tee -a "$LOG") 2>&1
else
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done) 2>&1
fi

cd "$RAIZ/nucleo"
uv run python noche.py

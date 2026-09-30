#!/usr/bin/env bash
# Refresco semanal del oficio Claude Code (Fase S · 5): trae el changelog
# oficial y anota SOLO lo nuevo en remi-mente/oficios/claude-code.md, con
# fecha y verificación anti-invento contra el changelog real.
#
#     ./scripts/refresco-claude-code.sh   # a mano, ahora mismo
#     (LaunchAgent com.remi.refresco-claude-code lo corre los domingos a las 5:00,
#      después de la copia de las 3:00 y la consolidación nocturna de las 4:00)
#
# Log: ~/Library/Logs/Remi/refresco-claude-code.log.
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LOG="$HOME/Library/Logs/Remi/refresco-claude-code.log"
mkdir -p "$(dirname "$LOG")"
if [[ -t 1 ]]; then
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done | tee -a "$LOG") 2>&1
else
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done) 2>&1
fi

cd "$RAIZ/nucleo"
uv run python refresco_claude_code.py

#!/usr/bin/env bash
# Copia nocturna cifrada de Remi (3e · 2): remi.db (por la API de backup de
# SQLite) y la bóveda remi-mente/, con restic, al destino de config/copia.json
# (iCloud Drive por defecto). Borra lo de más de 30 días.
#
#     ./scripts/copia.sh            # a mano
#     (LaunchAgent com.remi.copia la corre a las 3:00)
#
# Log: ~/Library/Logs/Remi/copia.log. Sale con 1 si algo falló.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/copia-comun.sh"

LOG="$HOME/Library/Logs/Remi/copia.log"
mkdir -p "$(dirname "$LOG")"
# Con fecha en cada línea. A mano, también a la pantalla; desde launchd, la
# salida ya va a copia.log (así no sale dos veces).
if [[ -t 1 ]]; then
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done | tee -a "$LOG") 2>&1
else
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done) 2>&1
fi

arranque=$(date +%s)
preparar_restic "${1:-}"
echo "copia: destino=$DESTINO repo=$RESTIC_REPOSITORY"

# 1. La foto de remi.db, con la API de backup de SQLite.
mkdir -p "$PREPARADO"
python3 - "$DB" "$PREPARADO/remi.db" <<'PY'
import sqlite3, sys
origen = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
destino = sqlite3.connect(sys.argv[2])
with destino:
    origen.backup(destino)
estado = destino.execute("PRAGMA integrity_check").fetchone()[0]
origen.close(); destino.close()
if estado != "ok":
    sys.exit(f"la foto de remi.db salió dañada: {estado}")
print("copia: remi.db fotografiada con la API de backup (integrity_check ok)")
PY

# 2. El repositorio cifrado (la primera vez se crea).
mkdir -p "$(dirname "$RESTIC_REPOSITORY")" 2>/dev/null || true
if ! "$RESTIC" cat config >/dev/null 2>&1; then
  echo "copia: repositorio nuevo en $RESTIC_REPOSITORY"
  "$RESTIC" init
fi

# 3. La copia y la limpieza de lo viejo.
"$RESTIC" backup --tag nocturna --host remi "$PREPARADO/remi.db" "$BOVEDA"
"$RESTIC" forget --host remi --keep-within "${DIAS}d" --prune

echo "copia: lista en $(( $(date +%s) - arranque )) s"

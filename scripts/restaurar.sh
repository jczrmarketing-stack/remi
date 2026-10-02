#!/usr/bin/env bash
# Trae de vuelta remi.db y la bóveda desde la copia cifrada (3e · 3).
#
#     ./scripts/restaurar.sh                  # a una carpeta temporal, y verifica
#     ./scripts/restaurar.sh --en DIR         # a DIR, y verifica
#     ./scripts/restaurar.sh --reemplazar     # además los pone en su lugar
#
# Con --reemplazar: para el núcleo, aparta lo que haya (remi.db.antes-AAAAMMDD-HHMMSS
# y remi-mente.antes-…, nunca se borra nada), copia lo restaurado y lo vuelve
# a arrancar. --db y --boveda cambian a dónde van (para probar con copias).
# --copia ID elige otra copia que la última; --destino r2|b2, otro repositorio.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/copia-comun.sh"

EN="" ; REEMPLAZAR=0 ; COPIA="latest" ; DESTINO_PEDIDO="" ; DB_FINAL="$DB" ; BOVEDA_FINAL="$BOVEDA"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --en) EN="$2"; shift 2 ;;
    --reemplazar) REEMPLAZAR=1; shift ;;
    --copia) COPIA="$2"; shift 2 ;;
    --destino) DESTINO_PEDIDO="$2"; shift 2 ;;
    --db) DB_FINAL="$2"; shift 2 ;;
    --boveda) BOVEDA_FINAL="$2"; shift 2 ;;
    *) echo "No conozco la opción $1" >&2; exit 2 ;;
  esac
done

arranque=$(python3 -c 'import time;print(time.time())')
preparar_restic "$DESTINO_PEDIDO"
[[ -n "$EN" ]] || EN="$(mktemp -d "${TMPDIR:-/tmp}/remi-restaurar.XXXXXX")"
mkdir -p "$EN"
echo "Restaurando la copia «${COPIA}» de $DESTINO a $EN"

"$RESTIC" restore "$COPIA" --target "$EN" --host remi >/dev/null

# Qué había en la copia (para comparar la bóveda archivo por archivo) y
# dónde quedó cada cosa: restic restaura con la ruta absoluta de origen.
# La bóveda es la única ruta que NO es ni remi.db ni .env — nunca «la
# primera que no sea remi.db» (desde que .env entra a la copia, T5 · 4,
# eso agarraría cualquiera de las dos a ciegas).
ORIGEN_DB="$PREPARADO/remi.db"
TODAS_LAS_RUTAS="$("$RESTIC" ls --json "$COPIA" --host remi | python3 -c '
import json, sys
for linea in sys.stdin:
    d = json.loads(linea)
    if d.get("struct_type") == "snapshot":
        for p in d.get("paths", []):
            print(p)
        break
')"
ORIGEN_BOVEDA="$(grep -v -F -x "$ORIGEN_DB" <<<"$TODAS_LAS_RUTAS" | grep -v -F -x "$RUTA_ENV" | head -1)"
ESPERADOS="$("$RESTIC" ls --recursive "$COPIA" --host remi "$ORIGEN_BOVEDA" | grep -v "^$ORIGEN_BOVEDA\$" | grep "^$ORIGEN_BOVEDA/" | sort)"
DB_RESTAURADA="$EN$ORIGEN_DB"
BOVEDA_RESTAURADA="$EN$ORIGEN_BOVEDA"
ENV_RESTAURADO="$EN$RUTA_ENV"
HAY_ENV_EN_LA_COPIA=0
grep -q -F -x "$RUTA_ENV" <<<"$TODAS_LAS_RUTAS" && HAY_ENV_EN_LA_COPIA=1

# — Verificar: remi.db abre y está sana; la bóveda está completa —
python3 - "$DB_RESTAURADA" <<'PY'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
estado = c.execute("PRAGMA integrity_check").fetchone()[0]
tablas = [f[0] for f in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
if estado != "ok":
    sys.exit(f"remi.db restaurada está dañada: {estado}")
cuentas = ", ".join(f"{t}={c.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]}" for t in ("memoria", "turnos", "tareas", "ideas", "sesiones") if t in tablas)
print(f"remi.db: abre, integrity_check ok, {len(tablas)} tablas ({cuentas})")
PY
faltan=0
while IFS= read -r ruta; do
  [[ -z "$ruta" ]] && continue
  [[ -e "$EN$ruta" ]] || { echo "falta en la bóveda: $ruta" >&2; faltan=$((faltan + 1)); }
done <<<"$ESPERADOS"
total=$(grep -c . <<<"$ESPERADOS" || true)
if [[ $faltan -gt 0 ]]; then
  echo "La bóveda restaurada está incompleta: faltan $faltan de $total." >&2
  exit 1
fi
echo "bóveda: completa, $total entradas"

if [[ $REEMPLAZAR -eq 1 ]]; then
  marca="antes-$(date +%Y%m%d-%H%M%S)"
  nucleo_real=0
  [[ "$DB_FINAL" == "$DB" ]] && nucleo_real=1
  if [[ $nucleo_real -eq 1 ]]; then
    echo "Parando el núcleo…"
    launchctl bootout "gui/$UID/com.remi.nucleo" 2>/dev/null || true
    sleep 1
  fi
  apartado=0
  mkdir -p "$(dirname "$DB_FINAL")"
  for sufijo in "" "-wal" "-shm"; do
    if [[ -e "$DB_FINAL$sufijo" ]]; then mv "$DB_FINAL$sufijo" "$DB_FINAL$sufijo.$marca"; apartado=1; fi
  done
  cp -p "$DB_RESTAURADA" "$DB_FINAL"
  if [[ -e "$BOVEDA_FINAL" ]]; then
    mv "$BOVEDA_FINAL" "$BOVEDA_FINAL.$marca"; apartado=1
  fi
  mkdir -p "$(dirname "$BOVEDA_FINAL")"
  cp -Rp "$BOVEDA_RESTAURADA" "$BOVEDA_FINAL"
  echo "En su lugar: $DB_FINAL y $BOVEDA_FINAL"
  if [[ $nucleo_real -eq 1 && $HAY_ENV_EN_LA_COPIA -eq 1 ]]; then
    if [[ -e "$RUTA_ENV" ]]; then
      mv "$RUTA_ENV" "$RUTA_ENV.$marca"; apartado=1
    fi
    cp -p "$ENV_RESTAURADO" "$RUTA_ENV"
    chmod 600 "$RUTA_ENV"
    echo "En su lugar: $RUTA_ENV"
  fi
  [[ $apartado -eq 1 ]] && echo "Lo que había quedó apartado con .$marca (no se borró nada)."
  if [[ $nucleo_real -eq 1 ]]; then
    launchctl bootstrap "gui/$UID" "$HOME/Library/LaunchAgents/com.remi.nucleo.plist"
    echo "Núcleo arrancado de nuevo."
  fi
fi

python3 -c "import time;print(f'Listo en {time.time() - $arranque:.1f} s.')"

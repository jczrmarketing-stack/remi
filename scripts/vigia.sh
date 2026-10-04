#!/usr/bin/env bash
# Vigía de Remi (3e · 4). Cada minuto (LaunchAgent com.remi.vigia) le pega a
# /salud. Si falla 5 minutos seguidos, avisa una vez con una notificación de
# macOS; cuando vuelve, avisa que volvió. Telegram, cuando exista la fase 4.
#
# Solo escribe en vigia.log cuando algo cambia: nunca una línea por minuto.
set -uo pipefail

URL="${REMI_SALUD_URL:-http://127.0.0.1:4400/salud}"
ESTADO="$HOME/Library/Application Support/Remi/vigia.estado"
LOG="$HOME/Library/Logs/Remi/vigia.log"
MINUTOS_PARA_AVISAR="${REMI_VIGIA_MINUTOS:-5}"
mkdir -p "$(dirname "$ESTADO")" "$(dirname "$LOG")"

fallas=0 ; avisado=0
[[ -f "$ESTADO" ]] && read -r fallas avisado < "$ESTADO" || true
[[ "$fallas" =~ ^[0-9]+$ ]] || fallas=0
[[ "$avisado" =~ ^[01]$ ]] || avisado=0

anotar() { printf '%s %s\n' "$(date '+%F %T')" "$1" >> "$LOG"; }
avisar() {
  # Sin sonido (ley de los nudges: la ventanita avisa, no suena).
  osascript -e "display notification \"$1\" with title \"Remi\"" >/dev/null 2>&1 || true
}

if curl -s -f --max-time 5 "$URL" >/dev/null 2>&1; then
  if [[ $avisado -eq 1 ]]; then
    anotar "volvió tras $fallas min"
    avisar "Volví. Estuve caído $fallas minutos."
  elif [[ $fallas -gt 0 ]]; then
    anotar "responde de nuevo (fallaron $fallas min, sin aviso)"
  fi
  fallas=0 ; avisado=0
else
  fallas=$((fallas + 1))
  [[ $fallas -eq 1 ]] && anotar "no responde /salud"
  if [[ $fallas -ge $MINUTOS_PARA_AVISAR && $avisado -eq 0 ]]; then
    anotar "caído hace $fallas min: aviso"
    avisar "No respondo hace $fallas minutos. Si no vuelvo solo, corre ./scripts/instalar.sh."
    avisado=1
  fi
fi
printf '%s %s\n' "$fallas" "$avisado" > "$ESTADO"

# — Doctor a las 7:30 (docs/ROBUSTEZ.md §2) —
# vigia.sh no tiene cron propio: ya lo dispara el LaunchAgent com.remi.vigia
# cada minuto (StartInterval 60, scripts/instalar.sh), así que alcanza con
# mirar el reloj acá y no repetirlo dos veces el mismo día si el LaunchAgent
# dispara tarde (Mac dormida a las 7:30, por ejemplo). Si doctor.sh sale 0
# (todo OK), silencio total: no se manda nada.
DOCTOR="$(dirname "${BASH_SOURCE[0]}")/doctor.sh"
MARCA_DOCTOR="$HOME/Library/Application Support/Remi/vigia.doctor-fecha"
HOY_BOGOTA="$(TZ="America/Bogota" date '+%F')"
HORA_BOGOTA="$(TZ="America/Bogota" date '+%H:%M')"
if [[ "$HORA_BOGOTA" == "07:30" && "$(cat "$MARCA_DOCTOR" 2>/dev/null)" != "$HOY_BOGOTA" ]]; then
  echo "$HOY_BOGOTA" > "$MARCA_DOCTOR"
  if [[ -x "$DOCTOR" ]] && ! salida_doctor="$("$DOCTOR" 2>&1)"; then
    fallas_doctor="$(grep '^FALLA' <<<"$salida_doctor")"
    anotar "doctor de las 7:30 con fallas, aviso por Telegram"
    cuerpo="$(python3 -c 'import json, sys; print(json.dumps({"texto": sys.argv[1]}))' \
      "Doctor de Remi, $HOY_BOGOTA:
$fallas_doctor")"
    curl -s -f --max-time 5 -X POST "${URL%/salud}/telegram/avisar" \
      -H 'Content-Type: application/json' -d "$cuerpo" >/dev/null 2>&1 || true
  fi
fi

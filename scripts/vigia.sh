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
    avisar "No respondo hace $fallas minutos. Si no vuelvo solo, corré ./scripts/instalar.sh."
    avisado=1
  fi
fi
printf '%s %s\n' "$fallas" "$avisado" > "$ESTADO"

#!/usr/bin/env bash
# El doctor de Remi (Fase robustez, docs/ROBUSTEZ.md §2 y docs/ARQUITECTURA-CEREBRO.md §14):
# 10 chequeos, cada uno imprime una línea OK o FALLA. Sale 1 si algo falló, 0 si
# todo OK. El vigía lo corre cada mañana (scripts/vigia.sh) y avisa por Telegram
# solo si hay FALLA — doctor.sh en sí nunca avisa, solo diagnostica.
#
#     ./scripts/doctor.sh
#
# Nunca `set -e`: un chequeo que falla no debe cortar a los que siguen. Toda
# llamada de red lleva --max-time 5 para no colgarse sin red. Pensado para
# correr en menos de 10 s en total.
#
# Las 10 piezas (ajustadas a exactamente 10 líneas, fusionando «copia cifrada»
# y «episodio» en un solo chequeo de frescura — las dos son «¿la tarea nocturna
# corrió hace poco?» y comparten forma):
#   1. núcleo (/salud)              6. LaunchAgents com.remi.*
#   2. panel                         7. bóveda git limpia
#   3. whisper                       8. llaves en nucleo/.env (solo nombres)
#   4. kokoro                        9. frescura: copia cifrada + episodio
#   5. ollama                       10. disco libre
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUCLEO="$RAIZ/nucleo"

# — Puertos: de la config real (config/nucleo.json), nunca a mano en dos lugares —
PUERTO_NUCLEO=4400
HOST_NUCLEO=127.0.0.1
PUERTO_PANEL=4402
if [[ -f "$RAIZ/config/nucleo.json" ]]; then
  PUERTO_NUCLEO="$(python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['puerto'])" 2>/dev/null || echo 4400)"
  HOST_NUCLEO="$(python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['host'])" 2>/dev/null || echo 127.0.0.1)"
  PUERTO_PANEL="$(python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['puerto_panel'])" 2>/dev/null || echo 4402)"
fi
PUERTO_WHISPER=4401
if [[ -f "$RAIZ/config/ventanita.json" ]]; then
  PUERTO_WHISPER="$(python3 -c "
import json, urllib.parse as u
print(u.urlparse(json.load(open('$RAIZ/config/ventanita.json'))['voz']['whisper_server_url']).port)
" 2>/dev/null || echo 4401)"
fi

fallas=0

ok() { printf 'OK     %s\n' "$1"; }
falla() { printf 'FALLA  %s — %s\n' "$1" "$2"; fallas=$((fallas + 1)); }

# — 1. núcleo responde en /salud —
if cuerpo="$(curl -s -f --max-time 5 "http://$HOST_NUCLEO:$PUERTO_NUCLEO/salud" 2>/dev/null)" \
  && grep -q '"ok":[[:space:]]*true' <<<"$cuerpo"; then
  ok "núcleo (/salud :$PUERTO_NUCLEO)"
else
  falla "núcleo (/salud :$PUERTO_NUCLEO)" "no responde, o la base no abre"
fi

# — 2. panel responde, y si el túnel ya existe, no está público sin Access —
HOSTNAME_PANEL_PUBLICO="${REMI_HOSTNAME_PANEL:-remi.inv3rza.com}"
if curl -s -f --max-time 5 -o /dev/null "http://127.0.0.1:$PUERTO_PANEL"; then
  codigo_publico="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "https://$HOSTNAME_PANEL_PUBLICO" 2>/dev/null || echo 0)"
  if [[ "$codigo_publico" == "200" ]]; then
    falla "panel (:$PUERTO_PANEL)" "el panel está público: https://$HOSTNAME_PANEL_PUBLICO respondió 200 sin pasar por Access"
  else
    ok "panel (:$PUERTO_PANEL)"
  fi
else
  falla "panel (:$PUERTO_PANEL)" "no responde"
fi

# — 3. whisper disponible: whisper-server residente, o whisper-cli en el PATH —
# (el agente com.remi.whisper deja el modelo cargado; si no está, la ventanita
# cae sola a whisper-cli — ver scripts/instalar.sh)
if curl -s -f --max-time 5 -o /dev/null "http://127.0.0.1:$PUERTO_WHISPER/"; then
  ok "whisper (whisper-server residente :$PUERTO_WHISPER)"
elif command -v whisper-cli >/dev/null 2>&1; then
  ok "whisper (whisper-cli en el PATH, sin servidor residente)"
else
  falla "whisper" "ni whisper-server en :$PUERTO_WHISPER ni whisper-cli en el PATH"
fi

# — 4. kokoro disponible: el paquete está instalado en nucleo/.venv —
# find_spec no importa el módulo (no carga torch ni pesos): rápido a propósito.
if [[ -d "$NUCLEO" ]] && (cd "$NUCLEO" && uv run python -c "
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec('kokoro') else 1)
" >/dev/null 2>&1); then
  ok "kokoro (paquete instalado)"
else
  falla "kokoro" "el paquete no está instalado en nucleo/.venv (uv sync en nucleo/)"
fi

# — 5. ollama disponible —
if curl -s -f --max-time 5 -o /dev/null "http://127.0.0.1:11434/api/tags"; then
  ok "ollama (:11434)"
else
  falla "ollama" "no responde en 127.0.0.1:11434 (ollama serve, o brew services start ollama)"
fi

# — 6. LaunchAgents com.remi.* cargados, y los ganchos que alimentan a Remi —
# (F4.6: los ganchos van dentro de esta pieza para no renumerar las 10.)
# git: core.hooksPath con post-commit enlazado a scripts/hooks/git-gancho.
# Claude Code: SessionStart y SessionEnd hacia scripts/hooks/claude-sesion.py.
cargados="$(launchctl list 2>/dev/null | grep -c 'com\.remi\.' || true)"
cargados="${cargados:-0}"
ganchos_faltan=""
DIR_GANCHOS="$(git config --global core.hooksPath 2>/dev/null || true)"
DIR_GANCHOS="${DIR_GANCHOS/#\~/$HOME}"
if [[ -z "$DIR_GANCHOS" ]] || [[ "$(python3 -c "import os,sys;print(os.path.realpath(sys.argv[1]))" "$DIR_GANCHOS/post-commit" 2>/dev/null)" != "$RAIZ/scripts/hooks/git-gancho" ]]; then
  ganchos_faltan="git post-commit (scripts/hooks/instalar-git.sh)"
fi
claude_falta="$(python3 - "$HOME/.claude/settings.json" <<'PY' 2>/dev/null || echo "settings.json ilegible"
import json, sys
try:
    hooks = json.load(open(sys.argv[1])).get("hooks", {})
except OSError:
    hooks = {}
faltan = [
    evento for evento in ("SessionStart", "SessionEnd")
    if not any("claude-sesion.py" in str(h.get("command", "")) for g in hooks.get(evento, []) for h in g.get("hooks", []))
]
print(", ".join(faltan))
PY
)"
if [[ -n "$claude_falta" ]]; then
  ganchos_faltan="${ganchos_faltan:+$ganchos_faltan; }Claude Code $claude_falta (python3 scripts/hooks/instalar-claude.py)"
fi
if [[ "$cargados" -gt 0 && -z "$ganchos_faltan" ]]; then
  ok "LaunchAgents com.remi.* ($cargados cargados) y ganchos (git, Claude Code)"
elif [[ "$cargados" -gt 0 ]]; then
  falla "LaunchAgents y ganchos" "falta: $ganchos_faltan"
else
  falla "LaunchAgents com.remi.*" "ninguno cargado (./scripts/instalar.sh)"
fi

# — 7. bóveda (remi-mente) git limpia —
BOVEDA="${REMI_BOVEDA:-$RAIZ/conocimiento}"
BOVEDA_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$BOVEDA" 2>/dev/null || echo "$BOVEDA")"
if [[ -d "$BOVEDA_REAL/.git" ]]; then
  if [[ -z "$(git -C "$BOVEDA_REAL" status --porcelain 2>/dev/null)" ]]; then
    ok "bóveda git limpia ($BOVEDA_REAL)"
  else
    falla "bóveda git" "hay cambios sin commitear en $BOVEDA_REAL"
  fi
else
  falla "bóveda git" "$BOVEDA_REAL no existe o no es un repo git"
fi

# — 8. llaves presentes en nucleo/.env (solo nombres, nunca valores) —
ENV_FILE="$NUCLEO/.env"
NOMBRES_ESPERADOS=(TELEGRAM_TOKEN TELEGRAM_CHAT_ID NOTION_TOKEN NOTION_PAGINA_ID GROQ_API_KEY OPENROUTER_API_KEY VENICE_API_KEY)
if [[ -f "$ENV_FILE" ]]; then
  faltan=()
  for nombre in "${NOMBRES_ESPERADOS[@]}"; do
    grep -q "^${nombre}=" "$ENV_FILE" 2>/dev/null || faltan+=("$nombre")
  done
  if [[ ${#faltan[@]} -eq 0 ]]; then
    ok "llaves en nucleo/.env (${#NOMBRES_ESPERADOS[@]} nombres)"
  else
    falla "llaves en nucleo/.env" "faltan los nombres: ${faltan[*]}"
  fi
else
  falla "llaves en nucleo/.env" "el archivo no existe"
fi

# — 9. frescura: última copia cifrada (<26 h) y último episodio (<48 h) —
# Dos plazos distintos, un solo chequeo: ambos son «¿la tarea nocturna corrió
# hace poco?». La foto que copia.sh deja antes de cifrar con restic
# (scripts/copia-comun.sh § PREPARADO) sirve de marca de tiempo sin tocar
# restic ni el Llavero desde acá.
COPIA_MARCA="$HOME/Library/Application Support/Remi/copia/remi.db"
EPISODIOS_DIR="$BOVEDA_REAL/episodios"
ahora="$(date +%s)"
problemas_frescura=()

if [[ -f "$COPIA_MARCA" ]]; then
  edad_copia_h=$(( (ahora - $(stat -f %m "$COPIA_MARCA")) / 3600 ))
  [[ $edad_copia_h -ge 26 ]] && problemas_frescura+=("copia de hace ${edad_copia_h}h (>=26h)")
else
  problemas_frescura+=("sin copia cifrada todavía")
fi

if [[ -d "$EPISODIOS_DIR" ]]; then
  ultimo_episodio="$(find "$EPISODIOS_DIR" -maxdepth 1 -name '*.md' -type f -exec stat -f '%m %N' {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f1)"
  if [[ -n "$ultimo_episodio" ]]; then
    edad_episodio_h=$(( (ahora - ultimo_episodio) / 3600 ))
    [[ $edad_episodio_h -ge 48 ]] && problemas_frescura+=("episodio de hace ${edad_episodio_h}h (>=48h)")
  else
    problemas_frescura+=("sin episodios todavía")
  fi
else
  problemas_frescura+=("no existe $EPISODIOS_DIR")
fi

if [[ ${#problemas_frescura[@]} -eq 0 ]]; then
  ok "frescura (copia cifrada <26h, episodio <48h)"
else
  falla "frescura" "$(IFS=', '; echo "${problemas_frescura[*]}")"
fi

# — 10. disco con más de 10 GB libres —
libre_gb="$(df -g "$RAIZ" 2>/dev/null | awk 'NR==2{print $3}')"
if [[ -n "${libre_gb:-}" && "$libre_gb" =~ ^[0-9]+$ && "$libre_gb" -ge 10 ]]; then
  ok "disco (${libre_gb} GB libres)"
else
  falla "disco" "${libre_gb:-no pude medir} GB libres (hace falta >=10)"
fi

echo
if [[ "$fallas" -eq 0 ]]; then
  echo "doctor: 10/10 OK"
  exit 0
else
  echo "doctor: $fallas chequeo(s) en FALLA"
  exit 1
fi

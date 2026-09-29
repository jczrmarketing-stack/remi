#!/usr/bin/env bash
# Deja el núcleo de Remi arrancando solo con el Mac.
#
# Idempotente: correlo las veces que haga falta. Si el LaunchAgent ya está,
# lo reemplaza y lo vuelve a cargar; no duplica nada.
#
#     ./scripts/instalar.sh
#
# El núcleo es el que sabe: la base, la memoria, la voz y el pensar. La
# ventanita sin él arranca igual, pero muda.
set -euo pipefail

ETIQUETA="com.remi.nucleo"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUCLEO="$RAIZ/nucleo"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETA.plist"
LOGS="$HOME/Library/Logs/Remi"

echo "Remi · instalando el núcleo como servicio"
echo "  repo:  $RAIZ"

# — El puerto sale de config/nucleo.json, que es la única fuente —
PUERTO="$(python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['puerto'])")"
HOST="$(python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['host'])")"
echo "  puerto: $HOST:$PUERTO"

# — uv es quien levanta el servidor: sin él no hay nada que instalar —
UV="$(command -v uv || true)"
if [[ -z "$UV" ]]; then
  echo "No encontré \`uv\`. Instalalo y volvé a correr esto." >&2
  exit 1
fi
echo "  uv:     $UV"

# launchd NO hereda tu shell: un PATH que no nombre a `claude` deja a Remi
# sin poder pensar, y el error aparece recién en el log. Por eso se resuelve
# acá y se escribe en el plist.
CLAUDE="$(command -v claude || true)"
if [[ -n "$CLAUDE" ]]; then
  DIR_CLAUDE="$(dirname "$CLAUDE")"
  echo "  claude: $CLAUDE"
else
  DIR_CLAUDE=""
  echo "  claude: NO ESTÁ EN EL PATH — Remi va a andar, pero sin «pensar»." >&2
fi

RUTA="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
if [[ -n "$DIR_CLAUDE" && ":$RUTA:" != *":$DIR_CLAUDE:"* ]]; then
  RUTA="$DIR_CLAUDE:$RUTA"
fi

mkdir -p "$LOGS" "$HOME/Library/LaunchAgents"

# — Si ya estaba corriendo, se baja antes de reemplazarlo —
# `bootout` vuelve antes de que el servicio termine de irse: si cargamos el
# nuevo enseguida, launchd lo rechaza y el núcleo queda abajo sin que nadie
# se entere. Por eso se espera a que desaparezca de verdad.
if launchctl list | grep -q "$ETIQUETA"; then
  echo "  (ya estaba cargado: lo bajo para reemplazarlo)"
  launchctl bootout "gui/$UID/$ETIQUETA" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
  for _ in $(seq 1 50); do
    launchctl list | grep -q "$ETIQUETA" || break
    sleep 0.2
  done
  if launchctl list | grep -q "$ETIQUETA"; then
    echo "  No se termina de bajar. Probá a mano: launchctl bootout gui/$UID/$ETIQUETA" >&2
    exit 1
  fi
fi

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$ETIQUETA</string>
	<key>ProgramArguments</key>
	<array>
		<string>$UV</string>
		<string>run</string>
		<string>uvicorn</string>
		<string>servidor:app</string>
		<string>--host</string>
		<string>$HOST</string>
		<string>--port</string>
		<string>$PUERTO</string>
	</array>
	<key>WorkingDirectory</key>
	<string>$NUCLEO</string>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>$RUTA</string>
		<key>HOME</key>
		<string>$HOME</string>
	</dict>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>StandardOutPath</key>
	<string>$LOGS/nucleo.log</string>
	<key>StandardErrorPath</key>
	<string>$LOGS/nucleo.log</string>
</dict>
</plist>
PLISTEOF

plutil -lint "$PLIST" > /dev/null
launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null || launchctl load "$PLIST"

echo
echo "Listo. El núcleo arranca con el Mac y se levanta solo si se cae."
echo "  log:      $LOGS/nucleo.log"
echo "  bajarlo:  launchctl bootout gui/$UID/$ETIQUETA"
echo "  estado:   launchctl list | grep $ETIQUETA"

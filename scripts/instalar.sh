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
ETIQUETA_APP="com.remi.ventanita"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUCLEO="$RAIZ/nucleo"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETA.plist"
PLIST_APP="$HOME/Library/LaunchAgents/$ETIQUETA_APP.plist"
LOGS="$HOME/Library/Logs/Remi"

# Por RUTA, nunca por nombre: en el repo queda una copia construida en
# target/, y `open -a Remi` abría ESA. Las dos se llaman igual y
# LaunchServices elegía la del build.
APP="/Applications/Remi.app"

# Remi se abre sola al iniciar sesión. --sin-inicio-automatico deja el
# núcleo instalado igual, pero la ventanita la abrís vos.
INICIO_AUTOMATICO=1
for argumento in "$@"; do
  case "$argumento" in
    --sin-inicio-automatico) INICIO_AUTOMATICO=0 ;;
    *) echo "No conozco la opción $argumento" >&2; exit 1 ;;
  esac
done

echo "Remi · instalando"
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

# — Bajar un agente y esperar a que se vaya de verdad —
# `bootout` vuelve antes de que el servicio termine de irse: si cargamos el
# nuevo enseguida, launchd lo rechaza y el agente queda abajo sin que nadie
# se entere.
# `launchctl list <label>` acierta el agente exacto. Con `| grep` no: cuando
# Remi está abierta, LaunchServices registra un
# `application.com.remi.ventanita.NNN` que también matchea, y el script creía
# que el agente seguía cargado.
esta_cargado() {
  launchctl list "$1" > /dev/null 2>&1
}

bajar_agente() {
  local etiqueta="$1" plist="$2"
  esta_cargado "$etiqueta" || return 0
  launchctl bootout "gui/$UID/$etiqueta" 2>/dev/null \
    || launchctl unload "$plist" 2>/dev/null || true
  for _ in $(seq 1 50); do
    esta_cargado "$etiqueta" || return 0
    sleep 0.2
  done
  echo "  $etiqueta no se termina de bajar. A mano: launchctl bootout gui/$UID/$etiqueta" >&2
  return 1
}

bajar_agente "$ETIQUETA" "$PLIST"

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
echo "  núcleo: instalado"

# — Segundo agente: abrir Remi al iniciar sesión —
# Sin KeepAlive a propósito: si cerrás la ventanita, se queda cerrada hasta
# el próximo inicio de sesión. El núcleo sí se relevanta; la app es tuya.
bajar_agente "$ETIQUETA_APP" "$PLIST_APP" || true

if [[ "$INICIO_AUTOMATICO" -eq 1 ]]; then
  cat > "$PLIST_APP" <<PLISTAPPEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$ETIQUETA_APP</string>
	<key>ProgramArguments</key>
	<array>
		<string>/usr/bin/open</string>
		<string>-a</string>
		<string>/Applications/Remi.app</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>StandardOutPath</key>
	<string>$LOGS/ventanita.log</string>
	<key>StandardErrorPath</key>
	<string>$LOGS/ventanita.log</string>
</dict>
</plist>
PLISTAPPEOF
  plutil -lint "$PLIST_APP" > /dev/null
  launchctl bootstrap "gui/$UID" "$PLIST_APP" 2>/dev/null || launchctl load "$PLIST_APP"
  echo "  app:    abre sola al iniciar sesión"
else
  rm -f "$PLIST_APP"
  echo "  app:    la abrís vos (--sin-inicio-automatico)"
fi

echo
echo "Listo."
echo "  logs:     $LOGS/"
echo "  estado:   launchctl list | grep remi"
echo "  bajarlos: ./scripts/desinstalar.sh"

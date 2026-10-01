#!/usr/bin/env bash
# Túnel de Remi: remi.inv3rza.com -> el panel (127.0.0.1:4402), con
# Cloudflare Tunnel. Así el panel abre desde el teléfono sin exponer el Mac.
#
#     ./scripts/tunel.sh
#
# Idempotente: correlo las veces que haga falta. El único paso que hace
# Juan Camilo a mano es `cloudflared tunnel login` (una vez, abre el
# navegador) — este script lo detecta y explica el comando exacto, sin
# fallar feo.
#
# No toca ~/.cloudflared/config.yml: esa config ya la usa otro túnel
# (organic-cash → dash.organicstack.io) y no es de Remi. Este script escribe
# la suya propia en ~/.cloudflared/remi-config.yml.
#
# Al final, `exec cloudflared tunnel run`: el proceso que queda vivo es
# cloudflared, no este script — así el LaunchAgent com.remi.tunel (con
# KeepAlive) vigila al túnel de verdad, no a un wrapper.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TUNEL_NOMBRE="remi"
HOSTNAME_PANEL="remi.inv3rza.com"
# El puerto real del panel sale de config/nucleo.json (puerto_panel), nunca
# a mano en dos lugares — ahí lo lee también apps/panel/scripts/puerto-panel.mjs.
PUERTO_PANEL=4402
if [[ -f "$RAIZ/config/nucleo.json" ]]; then
  PUERTO_PANEL="$(python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['puerto_panel'])" 2>/dev/null || echo 4402)"
fi
PANEL_URL="http://127.0.0.1:$PUERTO_PANEL"
CLOUDFLARED_DIR="$HOME/.cloudflared"
CONFIG="$CLOUDFLARED_DIR/remi-config.yml"

echo "Remi · túnel"

# — 1. cloudflared: con brew si no está —
if ! command -v cloudflared >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "  cloudflared: no está, instalando con brew..."
    brew install cloudflared
  else
    echo "No encontré \`cloudflared\` ni \`brew\` para instalarlo." >&2
    echo "A mano: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
    exit 1
  fi
fi
echo "  cloudflared: $(command -v cloudflared)"

# — 2. login (el único paso manual) —
if [[ ! -f "$CLOUDFLARED_DIR/cert.pem" ]]; then
  cat <<MSG

Falta el login de cloudflared en este Mac — es a mano, una sola vez.
Corré esto y elegí el dominio inv3rza.com cuando el navegador lo pida:

    cloudflared tunnel login

Después volvé a correr ./scripts/tunel.sh.
MSG
  exit 0
fi
echo "  login: ya está ($CLOUDFLARED_DIR/cert.pem)"

# — 3. el túnel: crearlo si no existe, reusarlo si ya está —
buscar_uuid() {
  cloudflared tunnel list -o json 2>/dev/null | python3 -c "
import json, sys
try:
    tuneles = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for t in tuneles:
    if t.get('name') == '$TUNEL_NOMBRE' and not t.get('deleted_at'):
        print(t['id'])
        break
"
}

UUID="$(buscar_uuid)"
if [[ -z "$UUID" ]]; then
  echo "  túnel: creando '$TUNEL_NOMBRE'..."
  cloudflared tunnel create "$TUNEL_NOMBRE"
  UUID="$(buscar_uuid)"
fi

if [[ -z "$UUID" ]]; then
  echo "No pude crear ni encontrar el túnel '$TUNEL_NOMBRE' en Cloudflare." >&2
  exit 1
fi
echo "  túnel: $TUNEL_NOMBRE ($UUID)"

CREDENCIALES="$CLOUDFLARED_DIR/$UUID.json"
if [[ ! -f "$CREDENCIALES" ]]; then
  echo "El túnel '$TUNEL_NOMBRE' ya existe en la cuenta de Cloudflare, pero este Mac" >&2
  echo "no tiene sus credenciales ($CREDENCIALES)." >&2
  echo "Si se creó en otra máquina, copiá ese archivo acá. Si no, borralo y volvé a" >&2
  echo "correr este script para crear uno nuevo: cloudflared tunnel delete $TUNEL_NOMBRE" >&2
  exit 1
fi

# — 4. config propia, nunca la de otro túnel —
cat > "$CONFIG" <<YAML
tunnel: $UUID
credentials-file: $CREDENCIALES

ingress:
  - hostname: $HOSTNAME_PANEL
    service: $PANEL_URL
  - service: http_status:404
YAML
echo "  config: $CONFIG"

# — 5. la ruta DNS (si ya está, cloudflared lo dice y no rompe nada) —
cloudflared tunnel route dns "$TUNEL_NOMBRE" "$HOSTNAME_PANEL" 2>&1 \
  | grep -v "already configured" || true

echo "  listo: $HOSTNAME_PANEL -> $PANEL_URL"
echo

# — 6. correr de verdad (exec: el LaunchAgent vigila a cloudflared, no a bash) —
exec cloudflared tunnel --config "$CONFIG" run "$TUNEL_NOMBRE"

#!/usr/bin/env bash
# El ayudante del Mac: recarga Remi y corre las pruebas donde corren de verdad.
#
# La sesión de Claude en la app edita este repo desde otra máquina: puede
# escribir archivos y commitear, pero no reiniciar los LaunchAgents ni abrir
# el Chromium de Playwright acá. Este script hace esas dos cosas en el Mac, y
# nada más.
#
#     ./scripts/recargar.sh              recarga una vez (build del panel + reinicio)
#     ./scripts/recargar.sh pytest       pytest + mypy del núcleo
#     ./scripts/recargar.sh panel        lint + Playwright del panel
#     ./scripts/recargar.sh vitest       tsc + vitest de la ventanita
#     ./scripts/recargar.sh todo         pytest, panel y, al final, recarga
#     ./scripts/recargar.sh --vigilar    se queda esperando pedidos; Ctrl-C lo apaga
#
# En --vigilar atiende lo que aparezca en .recargar/pedido: una línea
# «<número> <acción>», donde la acción solo puede ser una de la lista fija de
# arriba — nunca un comando libre. El resultado queda en .recargar/ (fuera
# de git): salida-<número>.log con todo lo que imprimió, y `hecho` con
# «<número> <acción> <código de salida>».
#
# No instala nada, no queda corriendo al cerrar la terminal y no toca la base
# ni la bóveda: reinicia los dos agentes que ya existen (com.remi.nucleo y
# com.remi.panel) para que lean el código nuevo.
#
# Compatible con el bash 3.2 de macOS. Nunca `set -e`: un paso que falla se
# reporta, no corta el bucle.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZONA="$RAIZ/.recargar"
mkdir -p "$ZONA"

config() { # clave, valor por defecto — de config/nucleo.json, nunca a mano
  python3 -c "import json;print(json.load(open('$RAIZ/config/nucleo.json'))['$1'])" 2>/dev/null || echo "$2"
}
HOST_NUCLEO="$(config host 127.0.0.1)"
PUERTO_NUCLEO="$(config puerto 4400)"
PUERTO_PANEL="$(config puerto_panel 4402)"

esperar() { # url, segundos
  local url="$1" tope="$2" i=0
  while [ "$i" -lt "$tope" ]; do
    if curl -s -f --max-time 2 -o /dev/null "$url"; then return 0; fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

hacer_recargar() {
  echo "== panel: build ($(git -C "$RAIZ" log --oneline -1))"
  (cd "$RAIZ/apps/panel" && npm run build) || { echo "FALLA: el build del panel"; return 1; }
  echo "== reinicio: com.remi.nucleo y com.remi.panel"
  launchctl kickstart -k "gui/$UID/com.remi.nucleo" || { echo "FALLA: no pude reiniciar el núcleo"; return 1; }
  launchctl kickstart -k "gui/$UID/com.remi.panel" || { echo "FALLA: no pude reiniciar el panel"; return 1; }
  esperar "http://$HOST_NUCLEO:$PUERTO_NUCLEO/salud" 120 || { echo "FALLA: el núcleo no volvió en 120 s"; return 1; }
  esperar "http://127.0.0.1:$PUERTO_PANEL" 60 || { echo "FALLA: el panel no volvió en 60 s"; return 1; }
  echo "OK recargado"
}

hacer_pytest() {
  echo "== núcleo: pytest + mypy"
  (cd "$RAIZ/nucleo" && uv run pytest -q && uv run mypy .)
}

hacer_panel() {
  # NEXT_DIST_DIR aparte: el build de las pruebas no pisa el .next que está
  # sirviendo el panel de verdad (next.config.mjs ya lee esa variable).
  echo "== panel: lint + Playwright"
  (cd "$RAIZ/apps/panel" && npm run generar && npm run lint && NEXT_DIST_DIR=.next-pruebas npx playwright test)
}

hacer_vitest() {
  echo "== ventanita: tsc + vitest"
  (cd "$RAIZ/apps/ventanita" && npm run generar && npx tsc --noEmit && npm test)
}

hacer_todo() {
  local codigo=0
  hacer_pytest || codigo=1
  hacer_panel || codigo=1
  # La recarga va siempre: aunque una prueba falle, el panel real tiene que
  # quedar sirviendo lo que hay en disco.
  hacer_recargar || codigo=1
  return "$codigo"
}

accion_valida() {
  case "$1" in
    recargar|pytest|panel|vitest|todo) return 0 ;;
    *) return 1 ;;
  esac
}

vigilar() {
  echo "Remi · ayudante esperando pedidos en .recargar/pedido — Ctrl-C lo apaga"
  local ultimo="" numero accion codigo
  if [ -f "$ZONA/hecho" ]; then ultimo="$(cut -d' ' -f1 "$ZONA/hecho" 2>/dev/null)"; fi
  while true; do
    if [ -f "$ZONA/pedido" ]; then
      numero=""; accion=""
      read -r numero accion < "$ZONA/pedido" || true
      if [ -n "$numero" ] && [ "$numero" != "$ultimo" ]; then
        if [[ "$numero" =~ ^[0-9]+$ ]] && accion_valida "$accion"; then
          echo "[$(date '+%H:%M:%S')] pedido $numero: $accion"
          "hacer_$accion" > "$ZONA/salida-$numero.log" 2>&1
          codigo=$?
          echo "$numero $accion $codigo" > "$ZONA/hecho"
          echo "[$(date '+%H:%M:%S')] pedido $numero: terminó con $codigo"
        else
          echo "[$(date '+%H:%M:%S')] pedido ignorado (no es «<número> <acción conocida>»)"
          echo "$numero desconocida 2" > "$ZONA/hecho"
        fi
        ultimo="$numero"
      fi
    fi
    sleep 2
  done
}

case "${1:-recargar}" in
  --vigilar) vigilar ;;
  *)
    if accion_valida "${1:-recargar}"; then
      "hacer_${1:-recargar}"
    else
      echo "No conozco «$1». Opciones: recargar · pytest · panel · vitest · todo · --vigilar" >&2
      exit 2
    fi
    ;;
esac

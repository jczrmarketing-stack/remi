# Lo que comparten copia.sh y restaurar.sh: dónde está cada cosa y cómo se
# le habla a restic. Se incluye con `source`, no se corre solo.

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESTIC="$(command -v restic || echo /opt/homebrew/bin/restic)"
CONFIG="$RAIZ/config/copia.json"
DB="$RAIZ/nucleo/remi.db"
# Las llaves (T5 · 4): cifradas igual que remi.db, en el mismo repo restic.
RUTA_ENV="$RAIZ/nucleo/.env"
# La bóveda es la carpeta real, no el enlace «conocimiento».
BOVEDA="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$RAIZ/conocimiento")"
# La foto de remi.db que se copia: hecha con la API de backup de SQLite, nunca
# el archivo en caliente (un write a mitad dejaría una copia rota).
PREPARADO="$HOME/Library/Application Support/Remi/copia"

leer_config() {
  python3 - "$CONFIG" "${1:-}" <<'PY'
import json, os, sys
c = json.load(open(sys.argv[1]))
destino = sys.argv[2] or c["destino"]
d = c["destinos"][destino]
print(destino)
print(os.path.expanduser(d["repo"]))
print(c.get("conservar_dias", 30))
print(d.get("llavero_id", ""))
print(d.get("llavero_clave", ""))
PY
}

preparar_restic() {
  local destino_pedido="${1:-}"
  local lineas
  lineas="$(leer_config "$destino_pedido")"
  DESTINO="$(sed -n 1p <<<"$lineas")"
  export RESTIC_REPOSITORY="$(sed -n 2p <<<"$lineas")"
  DIAS="$(sed -n 3p <<<"$lineas")"
  local llavero_id llavero_clave
  llavero_id="$(sed -n 4p <<<"$lineas")"
  llavero_clave="$(sed -n 5p <<<"$lineas")"
  # La clave de cifrado sale del Llavero en cada corrida; nunca queda en disco.
  export RESTIC_PASSWORD_COMMAND="security find-generic-password -s remi-copia -a remi -w"
  if [[ "$DESTINO" == "r2" ]]; then
    export AWS_ACCESS_KEY_ID="$(security find-generic-password -s "$llavero_id" -w)"
    export AWS_SECRET_ACCESS_KEY="$(security find-generic-password -s "$llavero_clave" -w)"
  elif [[ "$DESTINO" == "b2" ]]; then
    export B2_ACCOUNT_ID="$(security find-generic-password -s "$llavero_id" -w)"
    export B2_ACCOUNT_KEY="$(security find-generic-password -s "$llavero_clave" -w)"
  fi
}

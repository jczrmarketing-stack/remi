#!/bin/sh
# Deja el gancho de Remi como core.hooksPath, sin borrar el de cada repo:
# git-gancho corre el .git/hooks del repo después de avisar.
#
# Idempotente. REMI_HOOKS_DEST cambia el destino (las pruebas).
# REMI_NO_CONFIGURAR_GIT=1 no toca la config global.
set -eu

RAIZ=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
GANCHO="$RAIZ/scripts/hooks/git-gancho"
DEST="${REMI_HOOKS_DEST:-$HOME/.config/git/hooks}"

NOMBRES="
applypatch-msg
pre-applypatch
post-applypatch
pre-commit
pre-merge-commit
prepare-commit-msg
commit-msg
post-commit
pre-rebase
post-checkout
post-merge
pre-push
pre-receive
update
proc-receive
post-receive
post-update
reference-transaction
push-to-checkout
pre-auto-gc
post-rewrite
sendemail-validate
fsmonitor-watchman
post-index-change
"

mkdir -p "$DEST"
chmod +x "$GANCHO" "$RAIZ/scripts/hooks/avisar-commit.py"
for nombre in $NOMBRES; do
  ln -sfn "$GANCHO" "$DEST/$nombre"
done

if [ "${REMI_NO_CONFIGURAR_GIT:-}" != "1" ]; then
  git config --global core.hooksPath "$DEST"
fi

echo "ganchos en $DEST"

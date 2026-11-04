#!/usr/bin/env bash
# Atajo: ./scripts/verificar.sh [--todo | --actualizar-linea-base]
exec python3 "$(dirname "$0")/verificar.py" "$@"

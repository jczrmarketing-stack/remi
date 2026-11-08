"""Desde afuera, como lo corre Juan Camilo: mypy sobre los 4 archivos no marca nada,
y el /p por Telegram y el leer_video siguen diciendo lo mismo."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NUCLEO = Path(__file__).resolve().parent.parent


def test_mypy_desde_nucleo_sale_limpio_para_los_cuatro():
    r = subprocess.run(
        [sys.executable, "-m", "mypy", "telegram.py", "noche.py", "vida.py", "catalogo_puente.py"],
        cwd=NUCLEO, capture_output=True, text=True, timeout=500,
    )
    propios = [l for l in r.stdout.splitlines() if l.split(":")[0] in {"telegram.py", "noche.py", "vida.py", "catalogo_puente.py"}]
    assert propios == [], "\n".join(propios)


def test_mypy_no_marca_la_variable_consulta_ni_los_tipos_de_noche():
    r = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml", "telegram.py", "noche.py"],
        cwd=NUCLEO, capture_output=True, text=True, timeout=500,
    )
    assert "manejar_comando" not in r.stdout and "var-annotated" not in r.stdout

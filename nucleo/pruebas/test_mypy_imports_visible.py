"""Visto desde afuera: mypy no marca los dos import-not-found."""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_mypy_no_marca_import_not_found_de_los_dos_modulos():
    r = subprocess.run(
        [sys.executable, "-m", "mypy", "."],
        cwd=RAIZ, capture_output=True, text=True, timeout=500,
    )
    salida = r.stdout + r.stderr
    assert "sentence_transformers" not in salida
    assert 'module named "afirmaciones"' not in salida

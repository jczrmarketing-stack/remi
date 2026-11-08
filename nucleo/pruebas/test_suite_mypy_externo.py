"""Desde afuera: el núcleo entero no reporta errores de mypy en suite.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_mypy_del_nucleo_no_nombra_suite():
    r = subprocess.run([sys.executable, "-m", "mypy", "--config-file", str(RAIZ / "pyproject.toml"), str(RAIZ / "suite.py")],
                       capture_output=True, text=True, cwd=RAIZ.parent)
    assert "suite.py:" not in "\n".join(l for l in r.stdout.splitlines() if "error" in l)

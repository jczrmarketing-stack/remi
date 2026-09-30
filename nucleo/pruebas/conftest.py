import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import os
import tempfile

# Ninguna prueba toca el remi.db real. Las que llaman a pensar() o a db sin
# su propio REMI_DB_PATH terminaban escribiendo turnos en la base de Juan
# Camilo (29/09, Fase 3a). Por defecto, una base temporal para toda la
# corrida; las que quieren la suya la siguen poniendo con monkeypatch.
os.environ.setdefault(
    "REMI_DB_PATH", os.path.join(tempfile.mkdtemp(prefix="remi-pruebas-"), "remi.db")
)

# Las pruebas nunca siembran las fichas reales de conocimiento/ al entrar al
# ciclo de vida del servidor; las que prueban la siembra la piden explícito.
os.environ.setdefault("REMI_SEMBRAR_CONOCIMIENTO", "0")


import pytest


@pytest.fixture(autouse=True)
def _base_propia(tmp_path, monkeypatch):
    """Cada prueba, su base. Las que ponen su propio REMI_DB_PATH lo pisan
    después, porque su monkeypatch corre después de este."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    # Ni la bóveda real: un episodio de prueba no puede aparecer en remi-mente.
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))

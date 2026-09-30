import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import os

# Las pruebas nunca siembran las fichas reales de conocimiento/ al entrar al
# ciclo de vida del servidor; las que prueban la siembra la piden explícito.
os.environ.setdefault("REMI_SEMBRAR_CONOCIMIENTO", "0")

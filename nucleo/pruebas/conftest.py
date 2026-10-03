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

# Un commit en un repo de prueba (test_boveda_git.py, test_notion_sync.py,
# etc.) no puede disparar el hook global de post-commit (avisar-commit.py):
# con `init.templateDir` apuntando a él en el .gitconfig real, cada `git
# init` de una prueba lo copiaba igual, y terminaba avisándole al núcleo
# real de un commit que no existe (1-oct: cientos de «proyecto sin ficha»
# en la Bandeja real). Un GIT_CONFIG_GLOBAL vacío hace que git ignore el
# .gitconfig de Juan Camilo durante toda la corrida.
_GIT_CONFIG_VACIO = tempfile.NamedTemporaryFile(
    prefix="remi-pruebas-sin-git-config-", suffix=".gitconfig", delete=False
)
_GIT_CONFIG_VACIO.close()
os.environ.setdefault("GIT_CONFIG_GLOBAL", _GIT_CONFIG_VACIO.name)

# Por si acaso el hook corre igual (un .git/hooks/post-commit que ya estaba
# ahí, copiado antes de este fix): un puerto que nadie escucha nunca llega
# al núcleo real.
os.environ.setdefault("REMI_NUCLEO_URL", "http://127.0.0.1:1")


import shutil

import pytest

# F3.5 (plan de cierre): REMI_BOVEDA solo aísla los episodios; los libros, los
# Estados y el git de la bóveda van por REMI_CONOCIMIENTO. Sin aislarlo,
# cada corrida de la suite reescribía el Estado de upvisuals.md real y
# commiteaba en remi-mente (1 y 2 de octubre). Una copia por corrida, sin
# .git (así boveda_git no commitea nada), con el contenido real para las
# pruebas que leen los oficios de verdad.
_BOVEDA_REAL = Path(__file__).resolve().parent.parent.parent / "conocimiento"
_COPIA_DE_LA_BOVEDA = Path(tempfile.mkdtemp(prefix="remi-pruebas-boveda-")) / "boveda"
if _BOVEDA_REAL.is_dir():
    shutil.copytree(_BOVEDA_REAL.resolve(), _COPIA_DE_LA_BOVEDA, ignore=shutil.ignore_patterns(".git", ".obsidian"))
else:
    (_COPIA_DE_LA_BOVEDA / "proyectos").mkdir(parents=True)


@pytest.fixture(autouse=True)
def _base_propia(tmp_path, monkeypatch):
    """Cada prueba, su base. Las que ponen su propio REMI_DB_PATH lo pisan
    después, porque su monkeypatch corre después de este."""
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    # Ni la bóveda real: un episodio de prueba no puede aparecer en remi-mente.
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    # Ni sus libros ni su git: la copia de esta corrida (las que quieren la
    # suya la ponen con monkeypatch y pisan esta).
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(_COPIA_DE_LA_BOVEDA / "proyectos"))

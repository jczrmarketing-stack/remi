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

import httpx
import pytest

# F4.2 (plan de cierre, T5.9): ninguna prueba toca el mundo real. Sin esto,
# las dos pruebas de test_tts que entran al ciclo de vida arrancaban el hilo
# de Telegram con el token de nucleo/.env (2/10: un getUpdates real, 409).
os.environ.setdefault("REMI_TELEGRAM", "0")

# Y una red con guardia: todo pedido de httpx hacia Telegram, Notion o el
# núcleo real (127.0.0.1:4400) se corta y queda anotado; la prueba que lo
# intentó falla al terminar, aunque el código se haya tragado la excepción
# (telegram.py y notion.py atrapan todo, a propósito).
_PROHIBIDOS = (("api.telegram.org", None), ("api.notion.com", None), ("127.0.0.1", 4400), ("localhost", 4400))
_INTENTOS_AL_MUNDO_REAL: list[str] = []


class MundoRealProhibido(httpx.ConnectError):
    pass


def _prohibido(url: httpx.URL) -> bool:
    return any(url.host == host and (puerto is None or url.port == puerto) for host, puerto in _PROHIBIDOS)


def _vigilar(original):  # type: ignore[no-untyped-def]
    def handle_request(self, request):  # type: ignore[no-untyped-def]
        if _prohibido(request.url):
            _INTENTOS_AL_MUNDO_REAL.append(f"{request.method} {request.url.copy_with(path='/…', query=None)}")
            raise MundoRealProhibido("una prueba intentó salir al mundo real", request=request)
        return original(self, request)

    return handle_request


def _vigilar_async(original):  # type: ignore[no-untyped-def]
    async def handle_async_request(self, request):  # type: ignore[no-untyped-def]
        if _prohibido(request.url):
            _INTENTOS_AL_MUNDO_REAL.append(f"{request.method} {request.url.copy_with(path='/…', query=None)}")
            raise MundoRealProhibido("una prueba intentó salir al mundo real", request=request)
        return await original(self, request)

    return handle_async_request


httpx.HTTPTransport.handle_request = _vigilar(httpx.HTTPTransport.handle_request)  # type: ignore[method-assign]
httpx.AsyncHTTPTransport.handle_async_request = _vigilar_async(httpx.AsyncHTTPTransport.handle_async_request)  # type: ignore[method-assign]


def pytest_configure(config):  # type: ignore[no-untyped-def]
    config.addinivalue_line("markers", "mundo_real_esperado: la prueba ejercita la guarda del mundo real a propósito")


@pytest.fixture(autouse=True)
def _sin_mundo_real(request):
    """Falla la prueba que intentó llegar a Telegram, Notion o :4400. Las
    que prueban la guarda misma lo piden con @pytest.mark.mundo_real_esperado."""
    _INTENTOS_AL_MUNDO_REAL.clear()
    yield
    intentos = list(_INTENTOS_AL_MUNDO_REAL)
    _INTENTOS_AL_MUNDO_REAL.clear()
    if intentos and request.node.get_closest_marker("mundo_real_esperado") is None:
        pytest.fail(f"la prueba intentó salir al mundo real: {intentos}", pytrace=False)

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

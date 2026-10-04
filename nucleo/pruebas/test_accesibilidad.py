"""B10.2: accesibilidad de macOS. `leer_ventana_activa_macos` (la real)
no se llama en pytest — nunca depende del permiso para pasar."""
import accesibilidad
from accesibilidad import VentanaActiva


def test_lector_doble_devuelve_ventana_activa():
    def lector_doble() -> VentanaActiva | None:
        return VentanaActiva(app="Chrome", titulo="Bandeja de entrada")

    ventana = lector_doble()
    assert ventana is not None
    assert ventana.app == "Chrome"


def test_leer_ventana_activa_macos_nunca_lanza_sin_permiso(monkeypatch):
    """Sin el permiso de Accesibilidad (o sin `osascript`), `subprocess.run`
    puede fallar o devolver un código de error — nunca debe lanzar."""
    def _run_que_falla(*args, **kwargs):
        raise OSError("osascript no autorizado")

    monkeypatch.setattr(accesibilidad.subprocess, "run", _run_que_falla)
    assert accesibilidad.leer_ventana_activa_macos() is None


def test_leer_ventana_activa_macos_con_salida_vacia_vuelve_none(monkeypatch):
    class _Resultado:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(accesibilidad.subprocess, "run", lambda *a, **k: _Resultado())
    assert accesibilidad.leer_ventana_activa_macos() is None


def test_leer_ventana_activa_macos_parsea_la_salida(monkeypatch):
    class _Resultado:
        returncode = 0
        stdout = "Terminal|||remi — zsh\n"

    monkeypatch.setattr(accesibilidad.subprocess, "run", lambda *a, **k: _Resultado())
    ventana = accesibilidad.leer_ventana_activa_macos()
    assert ventana is not None
    assert ventana.app == "Terminal"
    assert ventana.titulo == "remi — zsh"

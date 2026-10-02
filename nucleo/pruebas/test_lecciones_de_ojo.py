"""T8.7: consultar antes de actuar — hasta tres lecciones de un libro, al
abrir sesión (SessionStart) y al armar un encargo."""
import sys

import experiencia
from experiencia import Leccion


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("trabajo", "experiencia", "episodios", "libros"):
        sys.modules.pop(nombre, None)
    import importlib

    import experiencia as exp
    import trabajo as trab

    importlib.reload(exp)
    importlib.reload(trab)
    return trab


def _leccion(tema="malik", titulo="El 401 de malik"):
    return Leccion(
        titulo=titulo, tema=tema, resumen="r", clase="error", donde="x",
        secciones={
            "Síntoma": "El bot contestaba 401.",
            "Lo que creímos": "",
            "Causa real": "El token había vencido.",
            "Cura": "Se renovó el token.",
            "Cómo verlo antes": "Revisar la fecha de expiración.",
        },
        fuente="claude-code",
    )


def test_sin_lecciones_viene_vacio(tmp_path, monkeypatch):
    trab = _arrancar(tmp_path, monkeypatch)
    assert trab.lecciones_de_ojo("malik") == []


def test_una_leccion_aparece_como_ojo(tmp_path, monkeypatch):
    trab = _arrancar(tmp_path, monkeypatch)
    import experiencia as exp

    exp.escribir(_leccion())

    ojos = trab.lecciones_de_ojo("malik")

    assert len(ojos) == 1
    assert ojos[0].startswith("Ojo:")
    assert "token había vencido" in ojos[0]


def test_nunca_mas_de_tres(tmp_path, monkeypatch):
    trab = _arrancar(tmp_path, monkeypatch)
    import experiencia as exp

    for n in range(5):
        leccion = _leccion(titulo=f"Error {n}")
        leccion = Leccion(
            titulo=f"Error {n}", tema="malik", resumen="r", clase="error", donde="x",
            secciones={**leccion.secciones, "Síntoma": f"Síntoma {n}"},
            fuente="claude-code",
        )
        exp.escribir(leccion)

    assert len(trab.lecciones_de_ojo("malik")) == 3


def test_lecciones_de_otro_libro_no_aparecen(tmp_path, monkeypatch):
    trab = _arrancar(tmp_path, monkeypatch)
    import experiencia as exp

    exp.escribir(_leccion(tema="beam"))

    assert trab.lecciones_de_ojo("malik") == []

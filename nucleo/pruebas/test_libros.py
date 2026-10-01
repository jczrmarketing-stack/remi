"""Proyecto = carpeta. `ruta:` puede ser una o varias, y la más específica gana."""
from pathlib import Path

import libros


def _libro(carpeta: Path, nombre: str, cuerpo: str) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_text(cuerpo)


def test_acepta_una_ruta_o_varias(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    _libro(
        tmp_path,
        "remi.md",
        "---\ntitulo: Remi\ntema: remi\nresumen: La app.\nruta: /Users/juan/proyectos/remi\n---\n\nCuerpo.\n",
    )
    _libro(
        tmp_path,
        "malik.md",
        "---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas.\nruta:\n"
        "  - /Users/juan/projects/malik-gestion\n"
        "  - /Users/juan/proyectos/malik-gestion\n---\n",
    )
    _libro(
        tmp_path,
        "omniway.md",
        "---\ntitulo: Omniway\ntema: omniway\nresumen: La LLC.\nruta:\n---\n",
    )

    encontrados = {libro.tema: libro.rutas for libro in libros.listar()}
    assert encontrados["remi"] == ("/Users/juan/proyectos/remi",)
    assert encontrados["malik"] == (
        "/Users/juan/projects/malik-gestion",
        "/Users/juan/proyectos/malik-gestion",
    )
    assert encontrados["omniway"] == ()


def test_la_carpeta_de_adentro_cae_en_su_libro(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    raiz = tmp_path / "repos"
    (raiz / "remi" / "nucleo").mkdir(parents=True)
    (raiz / "remi-mente").mkdir()
    _libro(
        tmp_path,
        "remi.md",
        f"---\ntitulo: Remi\ntema: remi\nresumen: La app.\nruta: {raiz / 'remi'}\n---\n",
    )

    assert libros.por_ruta(str(raiz / "remi" / "nucleo")).tema == "remi"  # type: ignore[union-attr]
    # El prefijo de texto «remi» no se traga a «remi-mente».
    assert libros.por_ruta(str(raiz / "remi-mente")) is None


def test_gana_la_ruta_mas_especifica(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    raiz = tmp_path / "repos"
    (raiz / "proyectos" / "malik" / "src").mkdir(parents=True)
    _libro(
        tmp_path,
        "todo.md",
        f"---\ntitulo: Todo\ntema: todo\nresumen: Amplio.\nruta: {raiz}\n---\n",
    )
    _libro(
        tmp_path,
        "malik.md",
        f"---\ntitulo: Malik\ntema: malik\nresumen: Justo.\nruta: {raiz / 'proyectos' / 'malik'}\n---\n",
    )

    assert libros.por_ruta(str(raiz / "proyectos" / "malik" / "src")).tema == "malik"  # type: ignore[union-attr]


def test_sin_libro_no_inventa(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    assert libros.por_ruta("/no/existe") is None


def test_tipo_y_fases_del_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    _libro(
        tmp_path,
        "upvisuals.md",
        "---\n"
        "titulo: UpVisuals\n"
        "tema: upvisuals\n"
        "resumen: Plataforma de Alfonso.\n"
        "tipo: cliente\n"
        "fases:\n"
        "  - nombre: Fase 1\n"
        "    alcance: Distribución de contenido\n"
        "    monto: 5000\n"
        "    listo_cuando: Demo aprobada\n"
        "    estado: camino\n"
        "  - nombre: Fase 2\n"
        "    alcance: Generador de imágenes\n"
        "    monto: 3700\n"
        "    listo_cuando: Sin alcance aún\n"
        "    estado: sin_empezar\n"
        "---\n",
    )
    (libro,) = libros.listar()
    assert libro.tipo == "cliente"
    assert len(libro.fases) == 2
    assert libro.fases[0].nombre == "Fase 1"
    assert libro.fases[0].monto == 5000.0
    assert libro.fases[1].estado == "sin_empezar"


def test_sin_tipo_ni_fases_quedan_vacios_no_rompe(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    _libro(tmp_path, "malik.md", "---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas.\n---\n")
    (libro,) = libros.listar()
    assert libro.tipo is None
    assert libro.fases == ()


def test_tipo_invalido_queda_none(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path))
    _libro(tmp_path, "x.md", "---\ntitulo: X\ntema: x\nresumen: Y.\ntipo: inventado\n---\n")
    (libro,) = libros.listar()
    assert libro.tipo is None

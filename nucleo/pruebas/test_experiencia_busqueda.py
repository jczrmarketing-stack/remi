"""T8.6: búsqueda híbrida (FTS5 + vectores) sobre toda la bóveda. El
embedding se simula (determinístico, por hash del texto): esto prueba la
fusión y el reindexado, no si Ollama está arriba (eso ya lo prueba
test_vectores.py)."""
import sqlite3
import sys

import pytest

import experiencia
import vectores


def _embed_falso(texto: str) -> list[float]:
    import hashlib

    valor = int(hashlib.sha256(texto.encode()).hexdigest(), 16) % 1000 / 1000
    return [valor] * vectores.DIMENSIONES


@pytest.fixture(autouse=True)
def _sin_ollama(monkeypatch):
    monkeypatch.setattr(vectores, "embed", _embed_falso)


def _boveda(tmp_path, monkeypatch):
    boveda = tmp_path / "boveda"
    (boveda / "proyectos").mkdir(parents=True)
    (boveda / "experiencia").mkdir(parents=True)
    (boveda / "proyectos" / "malik.md").write_text(
        "---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas del artista.\n---\n\nCuerpo.\n"
    )
    (boveda / "experiencia" / "2026-10-01-malik-401.md").write_text(
        "---\n"
        'titulo: "El 401 de malik"\n'
        "tema: malik\n"
        'resumen: "Token vencido."\n'
        "tipo: leccion\n"
        "clase: error\n"
        "donde: organic-cash-malik/whatsapp.py\n"
        "veces: 1\n"
        "ultima_vez: 2026-10-01\n"
        "vueltas: false\n"
        "fuente: claude-code\n"
        "---\n\n"
        "## Síntoma\n\nEl bot devolvía 401 en cada mensaje, código ERR-401-TOKEN.\n\n"
        "## Causa real\n\nEl token de WhatsApp había vencido.\n\n"
    )
    monkeypatch.setenv("REMI_BOVEDA", str(boveda))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(boveda / "proyectos"))
    for nombre in ("experiencia", "vectores", "episodios", "libros"):
        sys.modules.pop(nombre, None)
    import importlib

    import experiencia as exp
    import vectores as vec

    importlib.reload(vec)
    importlib.reload(exp)
    monkeypatch.setattr(vec, "embed", _embed_falso)
    return exp


def test_reindexar_deja_la_leccion_en_fts_y_en_vectores(tmp_path, monkeypatch):
    exp = _boveda(tmp_path, monkeypatch)
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row

    recalculadas = exp.reindexar(conexion)

    assert recalculadas == 2  # el libro malik.md y la lección
    total = conexion.execute("SELECT COUNT(*) FROM experiencia_fts").fetchone()[0]
    assert total == 2


def test_buscar_un_codigo_exacto_lo_encuentra_por_fts(tmp_path, monkeypatch):
    exp = _boveda(tmp_path, monkeypatch)
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    exp.reindexar(conexion)

    resultados = exp.buscar(conexion, "ERR-401-TOKEN")

    assert any("401" in r.titulo for r in resultados)


def test_buscar_filtra_por_tema(tmp_path, monkeypatch):
    exp = _boveda(tmp_path, monkeypatch)
    (tmp_path / "boveda" / "proyectos" / "beam.md").write_text(
        "---\ntitulo: BeaM\ntema: beam\nresumen: Compartir pantalla.\n---\n\nCuerpo.\n"
    )
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    exp.reindexar(conexion)

    # Por FTS, un código exacto del tema malik no aparece si se filtra por
    # otro tema — el filtro de tema corta la lista de texto exacto; la
    # lista por vectores es una sugerencia blanda y puede seguir trayendo
    # algo del tema pedido, nunca de otro (ver `_vectores_buscar`).
    resultados = exp.buscar(conexion, "ERR-401-TOKEN", tema="beam")

    assert all(r.titulo != "El 401 de malik" for r in resultados)
    assert all(exp._tema_de(__import__("pathlib").Path(r.ruta)) == "beam" for r in resultados)


def test_reindexar_borra_lo_que_ya_no_esta(tmp_path, monkeypatch):
    exp = _boveda(tmp_path, monkeypatch)
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    exp.reindexar(conexion)
    (tmp_path / "boveda" / "experiencia" / "2026-10-01-malik-401.md").unlink()

    exp.reindexar(conexion)

    total = conexion.execute("SELECT COUNT(*) FROM experiencia_fts").fetchone()[0]
    assert total == 1

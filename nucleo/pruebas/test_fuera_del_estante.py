"""Una nota archivada (`estado: archivada`) o fusionada (`fusionado_en:`)
sigue en disco pero ningún lector la cuenta (plan de cierre: limpieza del
2/10/2026 y F3.2). Bóveda temporal; los vectores, falsos (sin Ollama)."""
import sqlite3
from datetime import date
from pathlib import Path

import libros
import noche
import vectores


def _nota(carpeta: Path, nombre: str, titulo: str, extra: str = "") -> Path:
    ruta = carpeta / nombre
    ruta.write_text(f'---\ntitulo: "{titulo}"\ntema: remi\nresumen: "r"\n{extra}---\n\nCuerpo.\n')
    return ruta


def _boveda(tmp_path, monkeypatch) -> Path:
    (tmp_path / "proyectos").mkdir()
    episodios = tmp_path / "episodios"
    episodios.mkdir()
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path))
    _nota(episodios, "2026-10-02-vivo.md", "Vivo")
    _nota(episodios, "2026-10-02-prueba.md", "Prueba", "estado: archivada\n")
    _nota(episodios, "2026-10-02-repetido.md", "Repetido", "fusionado_en: 2026-10-02-vivo.md\n")
    return episodios


def test_fuera_del_estante_reconoce_archivada_y_fusionada(tmp_path, monkeypatch):
    episodios = _boveda(tmp_path, monkeypatch)
    assert not libros.fuera_del_estante(episodios / "2026-10-02-vivo.md")
    assert libros.fuera_del_estante(episodios / "2026-10-02-prueba.md")
    assert libros.fuera_del_estante(episodios / "2026-10-02-repetido.md")
    # Siguen en disco: nunca se borran.
    assert len(list(episodios.glob("*.md"))) == 3


def test_ni_los_vectores_ni_la_noche_las_cuentan(tmp_path, monkeypatch):
    episodios = _boveda(tmp_path, monkeypatch)
    assert [n.titulo.strip('"') for n in vectores.notas() if n.tipo == "episodio"] == ["Vivo"]
    assert noche._episodios_de_hoy(episodios, date(2026, 10, 2)) == [episodios / "2026-10-02-vivo.md"]


def test_asociar_salta_un_vector_viejo_de_una_nota_archivada(tmp_path, monkeypatch):
    episodios = _boveda(tmp_path, monkeypatch)
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    vectores.preparar(conexion)
    uno = [1.0] + [0.0] * (vectores.DIMENSIONES - 1)
    # Las tres con vector (la archivada lo tenía de antes de archivarse).
    for i, (nombre, titulo) in enumerate(
        [("2026-10-02-prueba.md", "Prueba"), ("2026-10-02-repetido.md", "Repetido"), ("2026-10-02-vivo.md", "Vivo")], start=1
    ):
        conexion.execute(
            "INSERT INTO notas_vector (id, ruta, tipo, titulo, hash, actualizado) VALUES (?, ?, 'episodio', ?, 'h', 'x')",
            (i, str(episodios / nombre), titulo),
        )
        conexion.execute("INSERT INTO notas_vector_embed (rowid, embedding) VALUES (?, ?)", (i, vectores._empaquetar(uno)))
    monkeypatch.setattr(vectores, "embed", lambda texto: uno)
    assert vectores.asociar(conexion, "lo que sea", k=2) == ["Vivo"]

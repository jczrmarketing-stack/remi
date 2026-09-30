"""Las claves nunca se inventan: una que no está en el texto no se escribe."""
from pathlib import Path

import claves

LIBRO = """---
titulo: Beam
tema: beam
resumen: App de compartir pantalla con un link, sin instalar nada.
---

- Usa Next.js y Supabase.
"""


def test_filtrar_inventadas_descarta_lo_que_no_esta_en_el_texto():
    candidatas = ["compartir pantalla", "next.js", "inteligencia artificial", "  ", "SUPABASE"]
    filtradas = claves.filtrar_inventadas(
        candidatas,
        titulo="Beam",
        resumen="App de compartir pantalla con un link, sin instalar nada.",
        cuerpo="Usa Next.js y Supabase.",
    )
    assert "compartir pantalla" in filtradas
    assert "next.js" in filtradas
    assert "supabase" in filtradas
    assert "inteligencia artificial" not in filtradas
    assert "" not in filtradas


def test_filtrar_inventadas_ignora_acentos_y_mayusculas():
    filtradas = claves.filtrar_inventadas(
        ["NÚCLEO", "asociación"],
        titulo="Remi",
        resumen="El nucleo local hace la asociacion de libros.",
        cuerpo="",
    )
    assert filtradas == ["núcleo", "asociación"]


def test_agregar_no_escribe_si_no_hay_claves_reales(tmp_path, monkeypatch):
    monkeypatch.setattr(claves, "extraer", lambda t, r, c: None)
    archivo = tmp_path / "beam.md"
    archivo.write_text(LIBRO)
    resultado = claves.agregar(archivo, "libro")
    assert resultado is None
    assert "claves" not in archivo.read_text()


def test_agregar_escribe_las_claves_reales(tmp_path, monkeypatch):
    monkeypatch.setattr(claves, "extraer", lambda t, r, c: ["next.js", "supabase"])
    archivo = tmp_path / "beam.md"
    archivo.write_text(LIBRO)
    resultado = claves.agregar(archivo, "libro")
    assert resultado == ["next.js", "supabase"]
    texto = archivo.read_text()
    assert "claves: [next.js, supabase]" in texto
    assert "titulo: Beam" in texto  # el resto del libro sigue igual


def test_agregar_no_toca_un_archivo_que_ya_tiene_claves(tmp_path, monkeypatch):
    llamado = []
    monkeypatch.setattr(claves, "extraer", lambda t, r, c: llamado.append(1) or ["x"])
    archivo = tmp_path / "beam.md"
    archivo.write_text(LIBRO.replace("---\n\n", "claves: [ya, tenia]\n---\n\n"))
    resultado = claves.agregar(archivo, "libro")
    assert resultado is None
    assert not llamado


def test_tiene_claves(tmp_path):
    con = tmp_path / "con.md"
    con.write_text(LIBRO.replace("---\n\n", "claves: [a, b, c]\n---\n\n"))
    sin = tmp_path / "sin.md"
    sin.write_text(LIBRO)
    assert claves.tiene_claves(con) is True
    assert claves.tiene_claves(sin) is False

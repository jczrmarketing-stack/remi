"""Vectores locales y asociación (Fase C, punto 5 del encargo del 30-sep).

Test real contra Ollama corriendo en esta máquina (nomic-embed-text), sobre
una mente de prueba — no se simula el embedding. Si Ollama no está
arriba, se salta en vez de fallar en rojo por una razón ajena al código.
"""
import sqlite3

import httpx
import pytest

import libros
import vectores


def _ollama_disponible() -> bool:
    try:
        httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_disponible(), reason="Ollama no está corriendo en esta máquina"
)


def test_asociacion_trae_lo_que_toca(tmp_path, monkeypatch) -> None:
    boveda = tmp_path / "boveda"
    notas = {
        "proyectos/shopify.md": ("Software para Shopify de un cliente", "El cliente desconfiaba: quería ver avances antes de pagar el anticipo."),
        "oficios/mantenimiento.md": ("Mantenimiento", "Cómo se vende y se cobra la mensualidad después de entregar."),
        "oficios/claude-code.md": ("Claude Code", "Qué es plan mode, subagentes y qué modelo recomendar."),
        "aprendido/decisiones/agua.md": ("Tomar agua", "Un vaso de agua al cerrar cada bloque largo."),
        "mundo/campo/lluvia.md": ("Clima en Medellín", "Cuántos días llovió este mes."),
    }
    for relativa, (titulo, resumen) in notas.items():
        ruta = boveda / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(f"---\ntitulo: {titulo}\nresumen: {resumen}\n---\n\nnada\n")
    monkeypatch.setattr(libros, "carpeta", lambda: boveda / "proyectos")
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row

    assert vectores.actualizar_todos(conexion) == len(notas)

    assert "Shopify" in vectores.asociar(conexion, "lo del cliente que desconfiaba", k=1)[0]
    assert "Mantenimiento" in vectores.asociar(conexion, "cómo cobro la mensualidad", k=1)[0]
    assert "Claude Code" in vectores.asociar(conexion, "qué es plan mode", k=1)[0]


def test_no_recalcula_si_el_contenido_no_cambio(tmp_path, monkeypatch) -> None:
    boveda = tmp_path / "boveda"
    (boveda / "proyectos").mkdir(parents=True)
    (boveda / "proyectos" / "malik.md").write_text(
        "---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas del artista.\n---\n\nnada\n"
    )
    monkeypatch.setattr(libros, "carpeta", lambda: boveda / "proyectos")

    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row

    primera = vectores.actualizar_todos(conexion)
    segunda = vectores.actualizar_todos(conexion)  # nada cambió

    assert primera == 1
    assert segunda == 0


def test_recalcula_si_la_nota_cambio(tmp_path, monkeypatch) -> None:
    boveda = tmp_path / "boveda"
    (boveda / "proyectos").mkdir(parents=True)
    archivo = boveda / "proyectos" / "malik.md"
    archivo.write_text("---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas.\n---\n\nnada\n")
    monkeypatch.setattr(libros, "carpeta", lambda: boveda / "proyectos")

    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    vectores.actualizar_todos(conexion)

    archivo.write_text("---\ntitulo: Malik\ntema: malik\nresumen: Las cuentas, cambiadas.\n---\n\nnada\n")
    recalculadas = vectores.actualizar_todos(conexion)

    assert recalculadas == 1


def test_sin_notas_asociar_no_revienta() -> None:
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    assert vectores.asociar(conexion, "cualquier cosa") == []

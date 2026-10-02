"""T9.2: sistema_encargo() suma los oficios stack/vibe-coding y las
reglas del proyecto activo, junto a prompting/claude-code."""
import pensar
import precarga

LIBRO_CON_REGLAS = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

## Reglas de este proyecto

- Nunca mandar el pago en el primer mensaje.
"""


def test_suma_stack_y_vibe_coding(monkeypatch):
    monkeypatch.setattr(precarga, "proyecto_activo", lambda: None)
    texto = pensar.sistema_encargo()

    # Contenido real de remi-mente/oficios/stack.md.
    assert "## Oficio: stack" in texto


def test_suma_las_reglas_del_proyecto_activo(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir()
    (carpeta / "malik.md").write_text(LIBRO_CON_REGLAS)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    monkeypatch.setattr(precarga, "proyecto_activo", lambda: ("malik", "ultimo_tocado"))
    monkeypatch.setattr(precarga, "resumen_nivel2", lambda tema: "Malik: resumen.")

    texto = pensar.sistema_encargo()

    assert "## Reglas de este proyecto" in texto
    assert "Nunca mandar el pago en el primer mensaje." in texto


def test_sin_proyecto_activo_no_rompe(monkeypatch):
    monkeypatch.setattr(precarga, "proyecto_activo", lambda: None)
    texto = pensar.sistema_encargo()
    assert "## Reglas de este proyecto" not in texto

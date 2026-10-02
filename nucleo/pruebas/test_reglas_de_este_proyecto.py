"""T9.2: las reglas de este proyecto viajan a SessionStart y al encargo."""
import libros

LIBRO_CON_REGLAS = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

## Reglas de este proyecto

- Nunca mandar el pago en el primer mensaje.
- Responder siempre en la voz de Juan Camilo.

## Notas

Nada que ver.
"""

LIBRO_SIN_REGLAS = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo sin reglas.
"""


def test_lee_las_reglas(tmp_path):
    archivo = tmp_path / "malik.md"
    archivo.write_text(LIBRO_CON_REGLAS)

    reglas = libros.reglas_de_este_proyecto(archivo)

    assert reglas == [
        "Nunca mandar el pago en el primer mensaje.",
        "Responder siempre en la voz de Juan Camilo.",
    ]


def test_sin_la_seccion_viene_vacio(tmp_path):
    archivo = tmp_path / "malik.md"
    archivo.write_text(LIBRO_SIN_REGLAS)

    assert libros.reglas_de_este_proyecto(archivo) == []


def test_no_se_mezcla_con_la_siguiente_seccion(tmp_path):
    archivo = tmp_path / "malik.md"
    archivo.write_text(LIBRO_CON_REGLAS)

    reglas = libros.reglas_de_este_proyecto(archivo)

    assert "Nada que ver." not in reglas

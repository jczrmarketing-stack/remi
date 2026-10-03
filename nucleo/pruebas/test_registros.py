"""F2.5 (plan de cierre): los dos registros son la misma persona.

Trabajo (`sistema_encargo()`): el carácter MÁS los oficios prompting,
claude-code, stack y vibe-coding, las «Reglas de este proyecto» (T9.2) y
hasta tres «Ojo:» (T8.7). Charla (`instrucciones_con_indice()` sin base):
el carácter y el índice, sin oficios."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import db
import pensar
import precarga
import trabajo

LIBRO_CON_REGLAS = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

## Reglas de este proyecto

- Nunca mandar el pago en el primer mensaje.
"""


def test_el_registro_de_trabajo_lleva_el_caracter_los_oficios_las_reglas_y_los_ojos(tmp_path, monkeypatch):
    # Una bóveda de prueba: un libro con reglas y los oficios reales al lado
    # (solo lectura; `carpeta_oficios()` los busca junto a proyectos/).
    carpeta = tmp_path / "proyectos"
    carpeta.mkdir()
    (carpeta / "malik.md").write_text(LIBRO_CON_REGLAS)
    (tmp_path / "oficios").symlink_to(Path(__file__).resolve().parent.parent.parent / "conocimiento" / "oficios")
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    monkeypatch.setattr(precarga, "proyecto_activo", lambda: ("malik", "ultimo_tocado"))
    monkeypatch.setattr(precarga, "resumen_nivel2", lambda tema: "Malik: resumen.")
    monkeypatch.setattr(
        trabajo, "lecciones_de_ojo", lambda tema: ["Ojo: el 401.", "Ojo: el pago.", "Ojo: la pausa."]
    )

    texto = pensar.sistema_encargo()

    # El carácter va primero: es la misma persona que en la charla.
    assert texto.startswith(pensar.caracter()[:60])
    for oficio in ("## Oficio: prompting", "## Oficio: Claude Code", "## Oficio: stack", "## Oficio: vibe-coding"):
        assert oficio in texto, oficio
    assert "## Reglas de este proyecto" in texto and "Nunca mandar el pago en el primer mensaje." in texto
    assert texto.count("Ojo:") == 3
    # Y después del carácter viene la forma del encargo, no antes.
    assert texto.index(pensar.caracter()[:60]) < texto.index("## Oficio: prompting")


def test_el_registro_de_charla_lleva_el_caracter_y_el_indice_pero_no_los_oficios():
    entrada = db.EntradaIndice(
        id=uuid4(), titulo="Malik — las cuentas", resumen="Las cuentas.", tema="malik",
        fecha=datetime(2026, 10, 1, tzinfo=timezone.utc), nivel=1,
    )
    texto = pensar.instrucciones_con_indice([entrada])

    assert texto.startswith(pensar.caracter()[:60])
    assert pensar.ENCABEZADO_INDICE.strip() in texto and "Malik — las cuentas" in texto
    assert "## Oficio:" not in texto

"""Los dos relojes que tienen que estar de acuerdo.

La ventanita corta su fetch a /mensaje por su cuenta, y el núcleo espera a
la CLI por la suya. Si la ventanita corta ANTES, Remi dice «No pude
guardarlo» mientras el núcleo sigue guardando: una culpa por algo que sí
pasó, y si repetís la frase queda duplicada. Eso es lo que prohíbe la ley 3.

Están en lenguajes distintos, así que se leen del archivo.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
SERVIDOR_TS = RAIZ / "apps" / "ventanita" / "src" / "servidor.ts"


def _timeout_de_la_ventanita_ms() -> int:
    texto = SERVIDOR_TS.read_text()
    encontrado = re.search(r"const TIMEOUT_NUCLEO_MS = (\d+);", texto)
    assert encontrado, "no encontré TIMEOUT_NUCLEO_MS en servidor.ts"
    return int(encontrado.group(1))


def test_la_ventanita_espera_mas_que_el_nucleo():
    import pensar

    ventanita_ms = _timeout_de_la_ventanita_ms()
    # El peor caso: Sonnet agota su tiempo y Haiku el suyo.
    nucleo_ms = pensar.PEOR_CASO_SEGUNDOS * 1000
    assert ventanita_ms > nucleo_ms, (
        f"La ventanita corta a los {ventanita_ms / 1000:.0f} s y el núcleo espera "
        f"{nucleo_ms / 1000:.0f} s: Remi diría «No pude guardarlo» mientras el núcleo "
        "todavía está guardando."
    )

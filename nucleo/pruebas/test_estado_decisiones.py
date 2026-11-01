"""El estado vivo trae las decisiones vigentes (≤90 días) y Remi las recibe en pensar.
Corre con pytest o con `python3 nucleo/pruebas/test_estado_decisiones.py`."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import vida  # noqa: E402


def _mente(d: Path) -> None:
    (d / "yo").mkdir(parents=True)
    (d / "yo" / "perfil.md").write_text("---\ntipo: yo\n---\n# Quién es\n- Juan Camilo\n", encoding="utf-8")
    (d / "negocio").mkdir()
    (d / "negocio" / "frentes.md").write_text("---\nactualizado: 2026-11-01\n---\n# Frentes\n- uno\n", encoding="utf-8")


def test_decisiones_vigentes_entran_y_las_viejas_no():
    with tempfile.TemporaryDirectory() as d:
        raiz = Path(d); _mente(raiz)
        vieja, os.environ["REMI_HOY"] = vida.MENTE, "2026-11-01"
        vida.MENTE = raiz
        try:
            vida.anotar("No usar la RAM del Mac para modelos. Detalle largo.", tipo="decision")
            os.environ["REMI_HOY"] = "2026-06-01"
            vida.anotar("Decisión vieja de junio", tipo="decision")
            os.environ["REMI_HOY"] = "2026-11-01"
            estado = vida.construir_estado()
        finally:
            vida.MENTE = vieja
            os.environ.pop("REMI_HOY", None)
        assert "# Decisiones vigentes" in estado
        assert "2026-11-01: No usar la RAM del Mac para modelos" in estado
        bloque = estado.split("# Decisiones vigentes")[1].split("\n\n")[0]
        assert "junio" not in bloque  # la vieja sigue en la mente, pero no en el bloque


def test_pensar_mete_el_estado_en_el_sistema():
    import pensar
    original = pensar._estado_vivo
    pensar._estado_vivo = lambda: "Hoy es 2026-11-01. # Quién es\n- Juan Camilo"
    try:
        texto = pensar.instrucciones_con_indice([], None)
    finally:
        pensar._estado_vivo = original
    assert "QUIÉN ES Y CÓMO ESTÁ HOY" in texto and "Juan Camilo" in texto
    # con un system prompt explícito (encargo) no se mete: ese ya trae lo suyo
    assert "QUIÉN ES" not in pensar.instrucciones_con_indice([], "otro sistema")


def test_sin_estado_remi_sigue():
    import pensar
    original = pensar._estado_vivo
    pensar._estado_vivo = lambda: ""
    try:
        assert "QUIÉN ES" not in pensar.instrucciones_con_indice([], None)
    finally:
        pensar._estado_vivo = original


if __name__ == "__main__":
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith("test_") and callable(f):
            try:
                f(); print("ok  ", nombre)
            except Exception as exc:  # noqa: BLE001
                import traceback; fallos += 1; print("FALLA", nombre, "→", type(exc).__name__, exc); traceback.print_exc()
    sys.exit(1 if fallos else 0)

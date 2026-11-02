"""La noche corre la newsletter sin tumbarse y deja la salida en la mente."""
from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))


def test_sin_boveda_dice_no_disponible():
    import noche
    assert noche.correr_newsletter(Path("/no/existe")) == "bóveda no disponible"


def test_con_boveda_falsa_escribe_el_archivo_y_resume():
    import noche
    import vida
    with tempfile.TemporaryDirectory() as d:
        boveda = Path(d) / "boveda"; (boveda / ".venv" / "bin").mkdir(parents=True)
        (boveda / "newsletter.py").write_text("")
        falso = boveda / ".venv" / "bin" / "python"
        falso.write_text("#!/bin/sh\ncase \"$*\" in *verificar*) echo 'OK    a'; echo 'OK    b'; echo 'FALLA c';; *youtube*) echo 'OK x';; *) echo 'mente/x.md (7 puntos)';; esac\n")
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
        vieja, vida.MENTE = vida.MENTE, Path(d) / "mente"
        try:
            resumen = noche.correr_newsletter(boveda, timeout_s=20)
            archivos = list((vida.MENTE / "mundo" / "newsletter").glob("_noche-*.md"))
        finally:
            vida.MENTE = vieja
        assert "Verificación de feeds: 2 ok, 1 fallan" in resumen and "7 puntos" in resumen
        assert len(archivos) == 1 and "## Diaria" in archivos[0].read_text()


def test_presupuesto_total_corta_los_pasos_que_no_caben_y_pasa_el_plazo():
    """Un solo presupuesto para toda la corrida: sin tiempo, los pasos no corren y quedan para mañana;
    con tiempo, cada paso recibe BOVEDA_PLAZO_FIN."""
    import noche
    import vida
    with tempfile.TemporaryDirectory() as d:
        boveda = Path(d) / "boveda"; (boveda / ".venv" / "bin").mkdir(parents=True)
        (boveda / "newsletter.py").write_text("")
        falso = boveda / ".venv" / "bin" / "python"
        falso.write_text("#!/bin/sh\necho \"plazo=$BOVEDA_PLAZO_FIN\"\n")
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
        vieja, vida.MENTE = vida.MENTE, Path(d) / "mente"
        try:
            sin_tiempo = noche.correr_newsletter(boveda, timeout_s=20, presupuesto_s=0)
            con_tiempo = noche.correr_newsletter(boveda, timeout_s=20, presupuesto_s=600)
            archivo = next((vida.MENTE / "mundo" / "newsletter").glob("_noche-*.md")).read_text()
        finally:
            vida.MENTE = vieja
        assert "sin tiempo" in sin_tiempo and "plazo=" not in sin_tiempo
        assert "plazo=1" in archivo  # un epoch: el paso lo recibió


def test_una_contradiccion_de_la_noche_llega_al_resumen_que_va_a_telegram():
    import noche
    import vida
    with tempfile.TemporaryDirectory() as d:
        boveda = Path(d) / "boveda"; (boveda / ".venv" / "bin").mkdir(parents=True)
        (boveda / "newsletter.py").write_text("")
        falso = boveda / ".venv" / "bin" / "python"
        falso.write_text("#!/bin/sh\ncase \"$*\" in *afirmaciones*) echo 'afirmaciones: 118 en total'; echo 'CONTRADICE: «Pro $35» choca con «Pro $25»';; *) echo ok;; esac\n")
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
        vieja, vida.MENTE = vida.MENTE, Path(d) / "mente"
        try:
            resumen = noche.correr_newsletter(boveda, timeout_s=20)
        finally:
            vida.MENTE = vieja
        assert "Afirmaciones (caducidad y contradicciones): afirmaciones: 118 en total" in resumen
        assert "Esto cambia lo que creías: «Pro $35» choca con «Pro $25»" in resumen


def test_si_la_boveda_no_esta_montada_el_reporte_lo_dice():
    import noche
    assert "no está montada" in noche.mensaje_newsletter("bóveda no disponible")
    assert noche.mensaje_newsletter("x: 1 ok").startswith("Newsletter (de noche): x: 1 ok")


if __name__ == "__main__":
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith("test_") and callable(f):
            try:
                f(); print("ok  ", nombre)
            except Exception as exc:  # noqa: BLE001
                import traceback; fallos += 1; print("FALLA", nombre, "→", type(exc).__name__, exc); traceback.print_exc()
    sys.exit(1 if fallos else 0)

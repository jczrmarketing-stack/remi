"""B3: la bóveda se busca primero en el disco interno; ORGANIC es solo respaldo; las variables mandan."""
from __future__ import annotations

from pathlib import Path

import donde_boveda


def test_el_disco_interno_va_antes_que_organic():
    # (en las pruebas FIJAS se reemplaza por una ruta inexistente; el orden real vive en INTERNA/EXTERNA)
    assert str(donde_boveda.INTERNA).endswith("proyectos/boveda") and str(donde_boveda.EXTERNA) == "/Volumes/ORGANIC/boveda"


def test_la_variable_manda_y_se_exige_la_marca(tmp_path):
    (tmp_path / "newsletter.py").write_text("")
    assert donde_boveda.ubicar(str(tmp_path)) == tmp_path
    otra = tmp_path / "otra"; otra.mkdir()   # una carpeta «boveda» sin la bóveda adentro no cuenta
    assert donde_boveda.ubicar(str(otra), marca="no-existe.py") is None or donde_boveda.ubicar(str(otra), marca="no-existe.py") != otra

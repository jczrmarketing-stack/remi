"""F4.2b: un núcleo de prueba (REMI_DB_PATH fuera de la base de siempre)
no arranca si la bóveda no está aislada también. Es la guarda de lo que pasó
el 2/10/2026: base en una copia, episodios escritos en la bóveda real."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import db
import servidor


def test_el_nucleo_de_verdad_arranca_sin_variables(tmp_path):
    real = tmp_path / "real"
    assert servidor.problema_de_aislamiento({}, real) is None
    assert servidor.problema_de_aislamiento({"REMI_DB_PATH": str(db.RUTA_DB_POR_DEFECTO)}, real) is None


def test_base_de_prueba_sin_boveda_aislada_no_arranca(tmp_path):
    real = tmp_path / "real"
    (real / "proyectos").mkdir(parents=True)
    copia = tmp_path / "copia"
    base = {"REMI_DB_PATH": str(tmp_path / "copia.db")}

    sin_nada = servidor.problema_de_aislamiento(base, real)
    assert sin_nada is not None and sin_nada.startswith("núcleo de prueba apuntando a la bóveda real")
    assert "REMI_CONOCIMIENTO y REMI_BOVEDA" in sin_nada

    a_la_real = servidor.problema_de_aislamiento(
        {**base, "REMI_CONOCIMIENTO": str(real / "proyectos"), "REMI_BOVEDA": str(copia)}, real
    )
    assert a_la_real is not None and "pero REMI_CONOCIMIENTO no está puesta o apunta" in a_la_real

    aislada = {**base, "REMI_CONOCIMIENTO": str(copia / "proyectos"), "REMI_BOVEDA": str(copia)}
    assert servidor.problema_de_aislamiento(aislada, real) is None


def test_un_enlace_a_la_boveda_real_tambien_cuenta_como_real(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    enlace = tmp_path / "conocimiento"
    enlace.symlink_to(real)
    problema = servidor.problema_de_aislamiento(
        {"REMI_DB_PATH": str(tmp_path / "x.db"), "REMI_CONOCIMIENTO": str(enlace / "proyectos"), "REMI_BOVEDA": str(tmp_path / "b")},
        real.resolve(),
    )
    assert problema is not None and "REMI_CONOCIMIENTO" in problema


def test_el_ciclo_de_vida_se_niega_a_arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "copia.db"))
    monkeypatch.delenv("REMI_CONOCIMIENTO", raising=False)
    monkeypatch.delenv("REMI_BOVEDA", raising=False)
    with pytest.raises(RuntimeError, match="núcleo de prueba apuntando a la bóveda real"):
        with TestClient(servidor.app):
            pass

"""Refresco semanal del oficio Claude Code (Biblia Parte VI, Fase S punto 5).

La verificación anti-invento corre contra la fuente real (el changelog
traído), no contra la respuesta del modelo — por eso el test del invento
usa un changelog real de prueba y una respuesta que menciona algo que ese
changelog NO tiene.
"""
import subprocess
from datetime import datetime, timezone

import httpx
import pytest

import estado_libro
import pensar
import refresco_claude_code as refresco


def _git(carpeta, *args):
    return subprocess.run(
        ["git", "-C", str(carpeta), *args], capture_output=True, text=True, check=True
    )


def _preparar_boveda(tmp_path, monkeypatch):
    boveda = tmp_path / "boveda"
    proyectos = boveda / "proyectos"
    oficios = boveda / "oficios"
    proyectos.mkdir(parents=True)
    oficios.mkdir(parents=True)
    (oficios / "claude-code.md").write_text(
        "---\ntitulo: Claude Code\ntema: oficio-claude-code\n"
        "resumen: Qué pieza y qué modelo.\nclaves: [claude code]\ntipo: oficio\n---\n\n"
        "## Las piezas\nPlan mode, subagentes.\n\n## Cambios anotados\n- (vacío)\n"
    )
    subprocess.run(["git", "init", "-q", str(boveda)], check=True)
    subprocess.run(["git", "-C", str(boveda), "config", "user.email", "remi@local"], check=True)
    subprocess.run(["git", "-C", str(boveda), "config", "user.name", "Remi"], check=True)
    subprocess.run(["git", "-C", str(boveda), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(boveda), "commit", "-q", "-m", "inicial"], check=True)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(proyectos))
    monkeypatch.setattr(refresco.boveda_git.libros, "carpeta", lambda: proyectos)
    return boveda, oficios / "claude-code.md"


def _mock_pensado(texto):
    return pensar.Pensado(paso_minimo=texto, tokens_entrada=1, tokens_salida=1, modelo="modelo-de-prueba")


def test_sin_changelog_no_toca_nada(tmp_path, monkeypatch):
    boveda, archivo = _preparar_boveda(tmp_path, monkeypatch)

    def get_falla(*_a, **_k):
        raise httpx.ConnectError("no hay red", request=httpx.Request("GET", refresco.URL_CHANGELOG))

    monkeypatch.setattr(httpx, "get", get_falla)
    antes = archivo.read_text()

    assert refresco.refrescar() == 0
    assert archivo.read_text() == antes
    assert _git(boveda, "log", "--oneline").stdout.count("\n") == 1  # solo el commit inicial


def test_sin_novedades_el_modelo_dice_nada(tmp_path, monkeypatch):
    boveda, archivo = _preparar_boveda(tmp_path, monkeypatch)
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: httpx.Response(200, text="Changelog:\n- 2026-09-01: cosas viejas", request=httpx.Request("GET", refresco.URL_CHANGELOG))
    )
    monkeypatch.setattr(pensar, "_una_llamada_claude", lambda *a, **k: _mock_pensado("NADA"))

    antes = archivo.read_text()
    assert refresco.refrescar() == 0
    assert archivo.read_text() == antes


def test_novedad_real_se_anota_con_commit(tmp_path, monkeypatch):
    boveda, archivo = _preparar_boveda(tmp_path, monkeypatch)
    changelog_real = "Release notes\n\n2026-09-28: Se agregó soporte para Skills en /skill."
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: httpx.Response(
            200, text=changelog_real, request=httpx.Request("GET", refresco.URL_CHANGELOG)
        ),
    )

    def falso_una_llamada(m, pedido, instrucciones, indice):
        assert "Se agregó soporte para Skills" in pedido  # el changelog real viaja en el pedido
        return _mock_pensado("[2026-09-28] Se agregó soporte para Skills en /skill.")

    monkeypatch.setattr(pensar, "_una_llamada_claude", falso_una_llamada)

    n = refresco.refrescar(ahora=datetime(2026, 9, 30, 5, 0, tzinfo=timezone.utc))
    assert n == 1

    contenido = archivo.read_text()
    assert "[2026-09-28] Se agregó soporte para Skills en /skill." in contenido
    assert "(vacío)" not in contenido

    log = _git(boveda, "log", "--oneline").stdout
    assert "novedad" in log


def test_novedad_inventada_se_rechaza_y_no_se_anota(tmp_path, monkeypatch):
    boveda, archivo = _preparar_boveda(tmp_path, monkeypatch)
    changelog_real = "Release notes\n\n2026-09-28: Se agregó soporte para Skills en /skill."
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: httpx.Response(
            200, text=changelog_real, request=httpx.Request("GET", refresco.URL_CHANGELOG)
        ),
    )
    # "N8N" no está en el changelog real: es el tipo exacto de invento del
    # incidente del 30-sep, ahora contra la fuente correcta.
    monkeypatch.setattr(
        pensar, "_una_llamada_claude", lambda *a, **k: _mock_pensado("[2026-09-28] Ahora integra con N8N.")
    )

    antes = archivo.read_text()
    n = refresco.refrescar()
    assert n == 0
    assert archivo.read_text() == antes


def test_lineas_verificadas_filtra_solo_lo_inventado():
    fuente = "2026-09-28: el changelog dice que Claude Code 2.5 agregó /skill"
    salida = "[2026-09-28] Claude Code 2.5 agregó /skill.\n[2026-09-28] Además integra con N8N."
    aceptadas = refresco._lineas_verificadas(salida, fuente)
    assert len(aceptadas) == 1
    assert "N8N" not in aceptadas[0]

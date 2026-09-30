"""La puerta de los prompts (Biblia Parte VI, Fase S punto 2).

Un encargo para Claude Code no sale con una forma inventada en cada
llamada: sale con las seis partes fijas del oficio `prompting`, el oficio
`claude-code` cargado entero (para recomendar modelo y pieza), y el libro
del proyecto activo si hay uno — todo esto entra al system prompt real que
arma `pensar.sistema_encargo()`, sin mockear esa parte (es justo lo que se
prueba). Solo se mockea el límite con Claude (la llamada de red), como en
test_noche.py — un pedido real, con la puerta real.
"""
import importlib
import sys

import pytest

import pensar


PARTES = (
    "QUÉ LEER PRIMERO",
    "DIAGNÓSTICO",
    "PUNTOS",
    "QUÉ NO HACER",
    "LISTO CUANDO",
    "RECOMENDACIÓN",
)


def test_sistema_encargo_trae_las_seis_partes() -> None:
    texto = pensar.sistema_encargo()
    for parte in PARTES:
        assert parte in texto, f"falta «{parte}» en sistema_encargo()"


def test_sistema_encargo_carga_los_oficios_de_verdad(monkeypatch) -> None:
    texto = pensar.sistema_encargo()
    # Contenido real de remi-mente/oficios/prompting.md — si esto no está,
    # el oficio no se cargó, solo el encargo.md genérico.
    assert "Un objetivo por prompt" in texto
    # Contenido real de remi-mente/oficios/claude-code.md.
    assert "Plan mode (Shift+Tab)" in texto


def test_sistema_encargo_sin_oficios_no_se_rompe(monkeypatch, tmp_path) -> None:
    import sembrar_conocimiento

    monkeypatch.setattr(sembrar_conocimiento, "carpeta_oficios", lambda: tmp_path / "no-existe")
    texto = pensar.sistema_encargo()
    assert "QUÉ LEER PRIMERO" in texto  # el encargo.md base sigue estando


def test_sistema_encargo_precarga_el_proyecto_activo(monkeypatch) -> None:
    monkeypatch.setattr(
        pensar.precarga, "proyecto_activo", lambda: ("upvisuals", "bloque_abierto")
    )
    monkeypatch.setattr(
        pensar.precarga, "resumen_nivel2", lambda tema: "UpVisuals: esperando el anticipo de Alfonso."
    )
    texto = pensar.sistema_encargo()
    assert "Proyecto activo" in texto
    assert "UpVisuals: esperando el anticipo de Alfonso." in texto


def test_pedido_real_de_encargo_con_el_limite_mockeado(tmp_path, monkeypatch) -> None:
    """Un pedido real de un encargo (modo=prompt) recibe, del lado del
    núcleo, el system prompt real con las seis partes — solo se mockea la
    llamada de red a Claude, para no gastar tokens en la prueba."""
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor as servidor_mod
    from fastapi.testclient import TestClient

    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    importlib.reload(db)
    importlib.reload(servidor_mod)

    vistos: dict[str, str] = {}

    def falso_pensar(frase, motor=None, modo=None, base=None, **_k):
        vistos["frase"] = frase
        vistos["base"] = base or ""
        return servidor_mod.pensar.Pensado(
            paso_minimo=(
                "QUÉ LEER PRIMERO\n- nucleo/flow-engine\n\nDIAGNÓSTICO\nEl timing "
                "corre fuera de orden.\n\nPUNTOS\n1. Ordenar la cola del executor.\n\n"
                "QUÉ NO HACER\n- nada\n\nLISTO CUANDO\nDos nodos consecutivos "
                "corren en orden.\n\nRECOMENDACIÓN\nSonnet, plan mode: el cambio "
                "toca el orden de ejecución."
            ),
            tokens_entrada=800,
            tokens_salida=120,
            modelo="modelo-de-prueba",
        )

    monkeypatch.setattr(servidor_mod.pensar, "pensar", falso_pensar)
    cliente = TestClient(servidor_mod.app)

    respuesta = cliente.post(
        "/mensaje",
        json={
            "texto": "armame un encargo para arreglar el timing del executor de flujos",
            "modo": "prompt",
            "think": True,
        },
    ).json()

    assert vistos["base"] != ""  # se le pasó el system prompt de la puerta de prompts
    for parte in PARTES:
        assert parte in respuesta["texto"], respuesta["texto"]

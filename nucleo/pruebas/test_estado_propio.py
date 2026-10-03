"""Remi sabe en qué estado está (revisión del 3-oct, R1 #22). El 2-oct dijo
que «el núcleo no arranca» y que «los tests de Notion no pasan»: las dos
falsas. Y «¿estás funcionando bien? ¿qué te falta?» la atrapaba la regla de
las preguntas pendientes. Sin IA: si la frase pregunta por Remi mismo, entra
su estado medido (doctor.sh) y la regla de «qué falta» no la atrapa."""
import pytest

import precarga
import trabajo


@pytest.mark.parametrize(
    "frase",
    [
        "¿estás funcionando bien?",
        "¿cómo estás funcionando?",
        "¿estás completo?",
        "¿funcionas bien, Remi?",
        "¿cumples todo lo de la Biblia?",
        # 3-oct, la frase real: una pregunta personal con «qué te falta» al final.
        "que haces bebe como te sientes te creee te siente vivo te siente bien o que te falta ?",
        "¿cómo te sientes?",
        "¿te sientes vivo?",
    ],
)
def test_reconoce_cuando_le_preguntan_por_si_mismo(frase):
    assert precarga.pregunta_por_remi(frase)


@pytest.mark.parametrize("frase", ["¿qué me falta hoy?", "¿cómo va malik?", "tengo sueño, ¿paro?", "¿qué falta en upvisuals?"])
def test_lo_demas_no(frase):
    assert not precarga.pregunta_por_remi(frase)


def test_que_te_falta_solo_sigue_siendo_la_regla_de_t8():
    # «¿qué te falta?» solo: las preguntas pendientes (T8), sin modelo.
    assert trabajo.es_que_falta("¿qué te falta?")
    assert not precarga.pregunta_por_remi("¿qué te falta?")
    # Con «¿estás funcionando bien?» delante, es una pregunta por Remi.
    assert precarga.pregunta_por_remi("¿estás funcionando bien? ¿qué te falta?")


def test_el_estado_propio_trae_el_doctor_medido(monkeypatch):
    monkeypatch.setattr(
        precarga, "_correr_doctor", lambda: "OK     núcleo (/salud :4400)\nFALLA  disco — 5 GB libres\n\ndoctor: 1 chequeo(s) en FALLA"
    )
    texto = precarga.estado_propio()
    assert "OK     núcleo" in texto and "FALLA  disco" in texto
    assert "medido ahora" in texto
    assert "Preguntas tuyas pendientes" in texto


def test_sin_doctor_lo_dice_y_no_inventa(monkeypatch):
    monkeypatch.setattr(precarga, "_correr_doctor", lambda: None)
    texto = precarga.estado_propio()
    assert "no pude medir" in texto


def test_la_frase_personal_va_al_modelo_y_no_a_la_regla_de_preguntas(tmp_path, monkeypatch):
    import importlib
    import sys

    from fastapi.testclient import TestClient

    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    llamadas = []
    monkeypatch.setattr(
        servidor.pensar, "pensar",
        lambda frase, *a, **k: llamadas.append(frase) or servidor.pensar.Pensado("Bien, con todo en verde.", 1, 1, "haiku"),
    )
    frase = "que haces bebe como te sientes te creee te siente vivo te siente bien o que te falta ?"
    respuesta = TestClient(servidor.app).post("/mensaje", json={"texto": frase, "think": True}).json()

    assert llamadas == [frase]
    assert respuesta["texto"] == "Bien, con todo en verde."

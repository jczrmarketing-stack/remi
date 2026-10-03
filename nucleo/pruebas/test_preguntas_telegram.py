"""T3.6: la misma pregunta por Telegram, una vez al día como mucho."""
import sys
from datetime import datetime, timedelta, timezone

SIN_TIPO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo.
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("db", "preguntas", "telegram"):
        sys.modules.pop(nombre, None)
    import db
    import preguntas
    import telegram

    # El mecanismo se prueba prendido; por defecto está apagado (3-oct).
    monkeypatch.setattr(preguntas, "EN_EL_CHAT", True)
    return db, preguntas, telegram


def test_avisa_la_primera_vez_del_dia(tmp_path, monkeypatch):
    db_mod, preguntas, telegram = _arrancar(tmp_path, monkeypatch)
    enviados = []
    monkeypatch.setattr(telegram, "avisar", lambda cuerpo: enviados.append(cuerpo.texto))
    conexion = db_mod.conectar()
    ahora = datetime.now(timezone.utc)

    pregunta = preguntas.avisar_por_telegram_si_toca(conexion, ahora)

    assert pregunta is not None
    assert enviados == [pregunta.voz]
    # Queda en el aire para Telegram, no para la ventanita (3-oct).
    assert preguntas.en_el_aire(conexion, ahora, "telegram") is not None
    assert preguntas.en_el_aire(conexion, ahora, "ventanita") is None


def test_no_avisa_dos_veces_el_mismo_dia(tmp_path, monkeypatch):
    db_mod, preguntas, telegram = _arrancar(tmp_path, monkeypatch)
    enviados = []
    monkeypatch.setattr(telegram, "avisar", lambda cuerpo: enviados.append(cuerpo.texto))
    conexion = db_mod.conectar()
    # Hora fija: con la real, entre las 22:00 y las 24:00 UTC «dos horas
    # después» ya era otro día y la prueba fallaba (3-oct, 23:16 UTC).
    ahora = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)

    preguntas.avisar_por_telegram_si_toca(conexion, ahora)
    preguntas.avisar_por_telegram_si_toca(conexion, ahora + timedelta(hours=2))

    assert len(enviados) == 1


def test_al_dia_siguiente_vuelve_a_avisar(tmp_path, monkeypatch):
    db_mod, preguntas, telegram = _arrancar(tmp_path, monkeypatch)
    enviados = []
    monkeypatch.setattr(telegram, "avisar", lambda cuerpo: enviados.append(cuerpo.texto))
    conexion = db_mod.conectar()
    ahora = datetime.now(timezone.utc)

    preguntas.avisar_por_telegram_si_toca(conexion, ahora)
    # Responde la primera para que quede una segunda pendiente al día siguiente.
    pregunta = preguntas.en_el_aire(conexion, ahora, "telegram")
    db_mod.actualizar_estado_pregunta(conexion, pregunta.id, "respondida")
    preguntas.borrar_en_el_aire(conexion)

    preguntas.avisar_por_telegram_si_toca(conexion, ahora + timedelta(days=1))

    assert len(enviados) == 2


def test_por_defecto_no_pregunta_por_telegram(tmp_path, monkeypatch):
    db_mod, preguntas, telegram = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(preguntas, "EN_EL_CHAT", False)
    enviados = []
    monkeypatch.setattr(telegram, "avisar", lambda cuerpo: enviados.append(cuerpo.texto))
    conexion = db_mod.conectar()
    assert preguntas.avisar_por_telegram_si_toca(conexion, datetime.now(timezone.utc)) is None
    assert enviados == []

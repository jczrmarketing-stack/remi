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
    assert preguntas.en_el_aire(conexion) is not None


def test_no_avisa_dos_veces_el_mismo_dia(tmp_path, monkeypatch):
    db_mod, preguntas, telegram = _arrancar(tmp_path, monkeypatch)
    enviados = []
    monkeypatch.setattr(telegram, "avisar", lambda cuerpo: enviados.append(cuerpo.texto))
    conexion = db_mod.conectar()
    ahora = datetime.now(timezone.utc)

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
    pregunta = preguntas.en_el_aire(conexion)
    db_mod.actualizar_estado_pregunta(conexion, pregunta.id, "respondida")
    preguntas.borrar_en_el_aire(conexion)

    preguntas.avisar_por_telegram_si_toca(conexion, ahora + timedelta(days=1))

    assert len(enviados) == 2

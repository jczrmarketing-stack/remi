from datetime import datetime, timezone

import estado_crm as e


def _p(que, frente, tipo="Tarea", estado="Bandeja", paso="", notas=""):
    t = lambda v: {"rich_text": [{"plain_text": v}]}
    return {"properties": {
        "Qué": {"title": [{"plain_text": que}]}, "Frente": {"select": {"name": frente}},
        "Tipo": {"select": {"name": tipo}}, "Estado": {"status": {"name": estado}},
        "Paso mínimo": t(paso), "Notas": t(notas)}}


def test_render_agrupa_trunca_y_oculta_salud():
    ahora = datetime(2026, 10, 27, tzinfo=timezone.utc)
    t = e.render([_p("Oferta eltondz", "Fiverr", paso="mirar respuesta", notas="x" * 500),
                  _p("Cita médica", "Salud"), _p("Tomar agua", "Cuerpo"), _p("Arreglar LLC", "LLC y legal")], ahora)
    assert "## Fiverr" in t and "paso: mirar respuesta" in t and "…" in t
    assert "Salud" not in t and "agua" not in t and "## LLC y legal" in t
    assert "actualizado: 2026-10-27" in t


def test_filtro_excluye_hecha_soltada_y_hallazgo():
    f = str(e.filtro())
    assert "Hecha" in f and "Soltada" in f and "Hallazgo" in f


def test_sin_token_no_lanza(monkeypatch):
    import notion
    monkeypatch.setattr(notion, "token", lambda: None)
    assert e.refrescar() == "sin token"

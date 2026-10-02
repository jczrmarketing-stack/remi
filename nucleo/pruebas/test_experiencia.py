"""T8.1-T8.4: lecciones con evidencia, no transcripts. Bóveda temporal
siempre — nunca remi-mente real."""
import sys
from datetime import datetime, timezone

import experiencia
from experiencia import Leccion


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("experiencia", "episodios", "libros"):
        sys.modules.pop(nombre, None)
    import importlib
    import experiencia as exp

    importlib.reload(exp)
    return exp


def _leccion_error(
    *,
    titulo: str = "El 401 de malik por token vencido",
    clase="error",
    vueltas: bool = False,
    secciones: dict[str, str] | None = None,
) -> Leccion:
    return Leccion(
        titulo=titulo,
        tema="malik",
        resumen="El bot devolvía 401 porque el token de WhatsApp había vencido.",
        clase=clase,
        donde="organic-cash-malik/nucleo/whatsapp.py",
        secciones=secciones
        if secciones is not None
        else {
            "Síntoma": "El bot contestaba 401 en cada mensaje.",
            "Lo que creímos": "Se creyó que era un problema de permisos del número.",
            "Causa real": "El token de acceso de WhatsApp había vencido.",
            "Cura": "Se renovó el token y se guardó la fecha de expiración.",
            "Cómo verlo antes": "Revisar la fecha de expiración del token antes de depurar nada más.",
        },
        fuente="claude-code",
        vueltas=vueltas,
    )


def test_una_leccion_completa_valida_sin_errores():
    assert experiencia.validar(_leccion_error()) == []


def test_falta_una_seccion_no_valida():
    leccion = _leccion_error(secciones={**_leccion_error().secciones, "Cura": ""})
    errores = experiencia.validar(leccion)
    assert any("Cura" in e for e in errores)


def test_lo_que_creimos_puede_ir_vacia_sin_vueltas():
    leccion = _leccion_error(secciones={**_leccion_error().secciones, "Lo que creímos": ""})
    assert experiencia.validar(leccion) == []


def test_vueltas_exige_lo_que_creimos():
    leccion = _leccion_error(
        vueltas=True, secciones={**_leccion_error().secciones, "Lo que creímos": ""}
    )
    errores = experiencia.validar(leccion)
    assert any("vueltas" in e for e in errores)


def test_acierto_con_secciones_de_error_no_valida():
    leccion = _leccion_error(clase="acierto")
    errores = experiencia.validar(leccion)
    assert any("no son de un" in e for e in errores)


def test_escribir_crea_el_archivo_con_sus_secciones(tmp_path, monkeypatch):
    exp = _arrancar(tmp_path, monkeypatch)
    ahora = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)

    ruta, es_nueva = exp.escribir(_leccion_error(), ahora)

    assert es_nueva is True
    assert ruta.exists()
    texto = ruta.read_text()
    assert "clase: error" in texto
    assert "veces: 1" in texto
    assert "## Síntoma" in texto
    assert "## Causa real" in texto


def test_una_leccion_sin_completar_no_escribe_nada(tmp_path, monkeypatch):
    exp = _arrancar(tmp_path, monkeypatch)
    incompleta = _leccion_error(secciones={**_leccion_error().secciones, "Causa real": ""})

    try:
        exp.escribir(incompleta)
        assert False, "debería haber lanzado ValueError"
    except ValueError as error:
        assert "Causa real" in str(error)
    assert exp.listar() == []


def test_el_mismo_sintoma_del_mismo_libro_no_se_duplica(tmp_path, monkeypatch):
    exp = _arrancar(tmp_path, monkeypatch)
    ahora = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    exp.escribir(_leccion_error(), ahora)

    ruta, es_nueva = exp.escribir(_leccion_error(), ahora)

    assert es_nueva is False
    assert len(exp.listar()) == 1
    lecciones = exp.listar(tema="malik")
    assert lecciones[0].veces == 2
    assert "volvió a pasar" in ruta.read_text()


def test_un_sintoma_distinto_del_mismo_libro_crea_otra(tmp_path, monkeypatch):
    exp = _arrancar(tmp_path, monkeypatch)
    exp.escribir(_leccion_error())
    distinta = _leccion_error(
        titulo="El panel no cargaba por CORS",
        secciones={**_leccion_error().secciones, "Síntoma": "El panel no cargaba ninguna pantalla."},
    )

    exp.escribir(distinta)

    assert len(exp.listar(tema="malik")) == 2


def test_hay_vueltas_por_rojos_seguidos():
    assert experiencia.hay_vueltas(rojos_seguidos=3)
    assert not experiencia.hay_vueltas(rojos_seguidos=2)


def test_hay_vueltas_por_ediciones_sin_commit():
    assert experiencia.hay_vueltas(ediciones_sin_commit=5)
    assert not experiencia.hay_vueltas(ediciones_sin_commit=4)


def test_hay_vueltas_por_minutos():
    assert experiencia.hay_vueltas(minutos_hasta_el_verde=41)
    assert not experiencia.hay_vueltas(minutos_hasta_el_verde=40)


def test_commit_es_arreglo_reconoce_los_tres_verbos():
    assert experiencia.commit_es_arreglo("fix: el 401 de malik")
    assert experiencia.commit_es_arreglo("arregla el webhook")
    assert experiencia.commit_es_arreglo("corrige el timeout")
    assert not experiencia.commit_es_arreglo("docs: actualiza el plan")


def test_resultado_de_sesion_sin_commits():
    assert experiencia.resultado_de_sesion(hubo_commits=False, pruebas="sin-correr", fix_en_48h=False) == "sin-commit"


def test_resultado_de_sesion_limpio():
    assert experiencia.resultado_de_sesion(hubo_commits=True, pruebas="verde", fix_en_48h=False) == "limpio"


def test_resultado_de_sesion_con_arreglo_por_fix_despues():
    assert experiencia.resultado_de_sesion(hubo_commits=True, pruebas="verde", fix_en_48h=True) == "con-arreglo"


def test_resultado_de_sesion_con_arreglo_por_rojo():
    assert experiencia.resultado_de_sesion(hubo_commits=True, pruebas="rojo", fix_en_48h=False) == "con-arreglo"

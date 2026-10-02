"""T8.5: las herramientas MCP anotar_leccion y buscar_lecciones."""
import sys

SECCIONES = {
    "Síntoma": "El bot contestaba 401 en cada mensaje.",
    "Lo que creímos": "",
    "Causa real": "El token de acceso de WhatsApp había vencido.",
    "Cura": "Se renovó el token.",
    "Cómo verlo antes": "Revisar la fecha de expiración del token.",
}


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("memoria_mcp", "experiencia", "episodios", "libros"):
        sys.modules.pop(nombre, None)
    import memoria_mcp

    return memoria_mcp


def test_anotar_leccion_crea_el_archivo(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)

    respuesta = mcp.anotar_leccion(
        titulo="El 401 de malik por token vencido",
        tema="malik",
        resumen="El bot devolvía 401 porque el token había vencido.",
        clase="error",
        donde="organic-cash-malik/whatsapp.py",
        secciones=SECCIONES,
    )

    assert "Anotada" in respuesta
    assert list((tmp_path / "boveda" / "experiencia").glob("*.md"))


def test_anotar_leccion_repetida_suma_una_vuelta(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)
    kwargs = dict(
        titulo="El 401 de malik por token vencido", tema="malik",
        resumen="r", clase="error", donde="x", secciones=SECCIONES,
    )
    mcp.anotar_leccion(**kwargs)

    respuesta = mcp.anotar_leccion(**kwargs)

    assert "ya había" in respuesta.lower()
    lecciones = [p for p in (tmp_path / "boveda" / "experiencia").glob("*.md") if p.name != "README.md"]
    assert len(lecciones) == 1


def test_anotar_leccion_con_clase_invalida_no_rompe(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)

    respuesta = mcp.anotar_leccion(
        titulo="x", tema="malik", resumen="x", clase="idea", donde="x", secciones={}
    )

    assert "error o acierto" in respuesta


def test_anotar_leccion_incompleta_no_guarda_nada(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)

    respuesta = mcp.anotar_leccion(
        titulo="x", tema="malik", resumen="x", clase="error", donde="x",
        secciones={**SECCIONES, "Cura": ""},
    )

    assert "no me entra" in respuesta.lower()
    assert list((tmp_path / "boveda" / "experiencia").glob("*.md")) == []


def test_buscar_lecciones_sin_nada_lo_dice(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)

    respuesta = mcp.buscar_lecciones(q="401")

    assert "no encontré" in respuesta.lower()


def test_buscar_lecciones_encuentra_lo_anotado(tmp_path, monkeypatch):
    mcp = _arrancar(tmp_path, monkeypatch)
    import vectores

    def _embed_falso(texto: str) -> list[float]:
        return [0.5] * vectores.DIMENSIONES

    monkeypatch.setattr(vectores, "embed", _embed_falso)
    mcp.anotar_leccion(
        titulo="El 401 de malik", tema="malik", resumen="Token vencido.",
        clase="error", donde="x", secciones=SECCIONES,
    )
    import experiencia

    experiencia.reindexar()

    respuesta = mcp.buscar_lecciones(q="401", tema="malik")

    assert "leccion" in respuesta

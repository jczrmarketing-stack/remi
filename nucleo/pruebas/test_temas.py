"""J1 · el tema de una idea (Biblia v3.7): sale del libro que la frase
nombra, sin IA, y ante la duda la idea queda suelta."""
import importlib
import sys

from fastapi.testclient import TestClient

LIBROS = {
    "proyectos/upvisuals.md": "---\ntitulo: UpVisuals — cliente Alfonso\ntema: upvisuals\nresumen: Plataforma de contenido.\n"
    "claves: [upvisuals, alfonso, distribución de contenido, next.js]\n---\n- Cliente: Alfonso.\n",
    "proyectos/organic-cash.md": "---\ntitulo: Organic Cash\ntema: organic-cash\nresumen: Software propio.\n"
    "claves: [software propio, whatsapp, next.js, flujos]\n---\n- Propio.\n",
    "proyectos/omniway.md": "---\ntitulo: Omniway LLC\ntema: omniway\nresumen: La empresa.\n"
    "claves: [omniway llc, wyoming, filings]\n---\n- LLC.\n",
    "areas/aprender.md": "---\ntitulo: Aprender\ntema: aprender\nresumen: Lo que estudio.\n---\n- (Completar.)\n",
}


def _boveda(tmp_path) -> None:
    for relativo, texto in LIBROS.items():
        ruta = tmp_path / relativo
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    for nombre in ("servidor", "bandeja", "db", "modelos", "temas", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_el_tema_sale_del_libro_que_la_frase_nombra(tmp_path, monkeypatch):
    _boveda(tmp_path)
    _arrancar(tmp_path, monkeypatch)
    import temas

    assert temas.tema_de_texto("Automatizar las facturas de Omniway LLC desde las entregas") == "omniway"
    assert temas.tema_de_texto("un router de leads para Organic Cash") == "organic-cash"
    assert temas.tema_de_texto("ALFONSO quiere el generador antes") == "upvisuals"
    # El área también cuenta, por su tema.
    assert temas.tema_de_texto("quiero aprender After Effects") == "aprender"


def test_sin_libro_que_la_nombre_la_idea_queda_suelta(tmp_path, monkeypatch):
    _boveda(tmp_path)
    _arrancar(tmp_path, monkeypatch)
    import temas

    assert temas.tema_de_texto("App de recetas con IA") is None
    assert temas.tema_de_texto("") is None
    # «omniway» adentro de otra palabra no cuenta.
    assert temas.tema_de_texto("los omniwayistas") is None


def test_una_clave_que_comparten_dos_libros_no_decide_y_el_empate_tampoco(tmp_path, monkeypatch):
    _boveda(tmp_path)
    _arrancar(tmp_path, monkeypatch)
    import temas

    # next.js está en las claves de dos libros.
    assert temas.tema_de_texto("migrar todo a next.js 15") is None
    # Una de cada uno: empate, no se elige.
    assert temas.tema_de_texto("lo de Alfonso y lo de wyoming") is None
    # Dos contra una: gana el de dos.
    assert temas.tema_de_texto("Alfonso pidió la distribución de contenido, y de paso lo de wyoming") == "upvisuals"


def test_la_idea_nace_con_su_tema_y_las_viejas_lo_leen_sin_guardarlo(tmp_path, monkeypatch):
    _boveda(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cliente.post("/mensaje", json={"texto": "se me ocurrió automatizar las facturas de Omniway LLC"})
    cliente.post("/mensaje", json={"texto": "se me ocurrió una app de recetas"})
    import db

    conexion = db.conectar()
    try:
        # Una de antes de la v3.7: sin tema guardado.
        conexion.execute(
            "INSERT INTO ideas (id, texto, origen, creada_en, enfria_hasta, estado, problema_vision) "
            "VALUES ('22222222-2222-2222-2222-222222222222', 'pedirle a Alfonso el logo', 'texto', "
            "'2026-09-29T10:00:00+00:00', '2026-10-01T10:00:00+00:00', 'enfriando', NULL)"
        )
        conexion.commit()
    finally:
        conexion.close()

    por_texto = {f["idea"]["texto"]: f["idea"]["tema"] for f in cliente.get("/bandeja").json()}

    assert por_texto["se me ocurrió automatizar las facturas de Omniway LLC"] == "omniway"
    assert por_texto["se me ocurrió una app de recetas"] is None
    assert por_texto["pedirle a Alfonso el logo"] == "upvisuals"

    conexion = db.conectar()
    try:
        guardados = dict(conexion.execute("SELECT texto, tema FROM ideas").fetchall())
    finally:
        conexion.close()
    assert guardados["se me ocurrió automatizar las facturas de Omniway LLC"] == "omniway"
    # La vieja se leyó con tema, pero su fila no se tocó.
    assert guardados["pedirle a Alfonso el logo"] is None


def test_corregir_el_tema_a_mano(tmp_path, monkeypatch):
    _boveda(tmp_path)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/mensaje", json={"texto": "se me ocurrió una app de recetas"})
    idea_id = cliente.get("/bandeja").json()[0]["idea"]["id"]

    puesta = cliente.post(f"/idea/{idea_id}/tema", json={"tema": "aprender"})
    assert puesta.status_code == 200 and puesta.json()["tema"] == "aprender"
    assert cliente.get("/bandeja").json()[0]["idea"]["tema"] == "aprender"

    assert cliente.post(f"/idea/{idea_id}/tema", json={"tema": None}).json()["tema"] is None
    assert cliente.post("/idea/99999999-9999-9999-9999-999999999999/tema", json={"tema": "x"}).status_code == 404

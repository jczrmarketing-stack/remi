"""Ambigüedad: preguntar, no adivinar (encargo del 2-oct, tarea 2). El caso
real, 2-oct 23:36: commits en malik-gestion de otra sesión de Claude Code y
Juan Camilo pregunta en la ventanita «¿esta completo cada paso de la biblia?»
— Remi contestó de Malik. Sin IA: si la frase no tiene tema propio, nombra
algo que existe en más de un libro, y lo último tocado es un commit o una
sesión de hace menos de 15 min, la precarga no decide sola."""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

MALIK = "---\ntitulo: Malik — estrategia de contenido\ntema: malik\nresumen: r\nclaves: [malik, x y reddit]\n---\n\n## Estado\n\nQuedaste: en el 401.\nDecisiones: ninguna.\nPróximo paso: revisar el token.\n"
REMI = "---\ntitulo: Remi — el asistente\ntema: remi\nresumen: r\nclaves: [remi, ventanita flotante]\n---\n\n## Estado\n\nQuedaste: cerrando el plan.\nDecisiones: ninguna.\nPróximo paso: usarla siete días.\n"
AHORA = datetime(2026, 10, 3, 4, 37, tzinfo=timezone.utc)  # 2-oct 23:37 en Bogotá


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    for nombre in ("db", "libros", "temas", "precarga"):
        sys.modules.pop(nombre, None)
    import db
    import precarga

    importlib.reload(db)
    (tmp_path / "proyectos").mkdir(parents=True, exist_ok=True)
    (tmp_path / "proyectos" / "malik.md").write_text(MALIK)
    (tmp_path / "proyectos" / "remi.md").write_text(REMI)
    return precarga, db


def _evento(db, tema, hace, tipo="commit"):
    conexion = db.conectar()
    try:
        conexion.execute(
            "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), tipo, f"/tmp/{tema}", tema, "{}", (AHORA - hace).isoformat()),
        )
        conexion.commit()
    finally:
        conexion.close()


def _caso_real(tmp_path, monkeypatch):
    precarga, db = _arrancar(tmp_path, monkeypatch)
    _evento(db, "remi", timedelta(minutes=5))
    _evento(db, "malik", timedelta(minutes=2))
    _evento(db, "malik", timedelta(minutes=1))
    return precarga, db


def test_el_caso_real_del_2_oct_pregunta_en_vez_de_contestar_de_malik(tmp_path, monkeypatch):
    precarga, _ = _caso_real(tmp_path, monkeypatch)

    dudoso = precarga.tema_dudoso("¿esta completo cada paso de la biblia?", AHORA)

    assert dudoso == ("malik", "remi")
    linea = precarga.linea_de_duda(dudoso)
    assert linea.strip().startswith("No sé si habla de Malik — estrategia de contenido o de Remi — el asistente")
    assert "pregunta cuál en una frase antes de contestar" in linea


def test_con_tema_propio_no_hay_duda(tmp_path, monkeypatch):
    precarga, _ = _caso_real(tmp_path, monkeypatch)
    assert precarga.tema_dudoso("¿cómo va la biblia de malik?", AHORA) is None


def test_sin_algo_que_exista_en_varios_libros_no_hay_duda(tmp_path, monkeypatch):
    precarga, _ = _caso_real(tmp_path, monkeypatch)
    assert precarga.tema_dudoso("tengo sueño, ¿paro?", AHORA) is None


def test_si_lo_ultimo_tocado_es_viejo_decide_como_siempre(tmp_path, monkeypatch):
    precarga, db = _arrancar(tmp_path, monkeypatch)
    _evento(db, "remi", timedelta(minutes=40))
    _evento(db, "malik", timedelta(minutes=20))
    assert precarga.tema_dudoso("¿esta completo cada paso de la biblia?", AHORA) is None


def test_con_un_bloque_abierto_en_la_ventanita_no_hay_duda(tmp_path, monkeypatch):
    precarga, _ = _caso_real(tmp_path, monkeypatch)
    monkeypatch.setattr(precarga, "_tema_de_bloque_abierto", lambda: "remi")
    assert precarga.tema_dudoso("¿esta completo cada paso de la biblia?", AHORA) is None


def test_pensar_con_duda_no_precarga_malik_y_manda_la_linea(tmp_path, monkeypatch):
    precarga, _ = _caso_real(tmp_path, monkeypatch)
    for nombre in ("pensar",):
        sys.modules.pop(nombre, None)
    import pensar

    monkeypatch.setattr(pensar, "_ahora", lambda: AHORA)
    monkeypatch.setattr(pensar, "_indice", lambda: [])
    monkeypatch.setattr(pensar, "_asociados", lambda frase: [])
    monkeypatch.setattr(precarga, "de_referencia", lambda frase: "\n\nDe la Biblia de Remi, lo que toca: LEY 03.\n")
    vistos = []
    monkeypatch.setattr(
        pensar, "_pensar_con_claude",
        lambda mensaje, *a, **k: vistos.append(mensaje) or pensar.Pensado("¿De Remi o de Malik?", 1, 1, "haiku"),
    )

    pensar.pensar("¿esta completo cada paso de la biblia?", "claude", "rapido")

    (mensaje,) = vistos
    assert "No sé si habla de Malik" in mensaje
    assert "en el 401" not in mensaje  # el Estado de Malik no se precarga
    assert "LEY 03" not in mensaje  # ni la Biblia: decidiría por él

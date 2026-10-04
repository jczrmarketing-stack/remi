"""B3.1: mensaje_cliente.libro_nombrado — sin IA, nunca inventa un cliente."""
import sys


def _libros(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(
        "---\ntitulo: UpVisuals\ntema: upvisuals\ncliente: Alfonso\ntipo: cliente\nresumen: x.\n---\n"
    )
    (carpeta / "beam.md").write_text(
        "---\ntitulo: BeaM\ntema: beam\ncliente: Milo\ntipo: cliente\nresumen: x.\n---\n"
    )
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    sys.modules.pop("mensaje_cliente", None)
    sys.modules.pop("libros", None)
    import mensaje_cliente

    return mensaje_cliente


def test_ya_le_mande_el_avance_encuentra_el_cliente(tmp_path, monkeypatch):
    mc = _libros(tmp_path, monkeypatch)
    libro = mc.libro_nombrado("ya le mandé el avance a Alfonso")
    assert libro is not None and libro.tema == "upvisuals"


def test_no_cierra_el_de_otro_cliente(tmp_path, monkeypatch):
    mc = _libros(tmp_path, monkeypatch)
    libro = mc.libro_nombrado("ya le mandé el avance a Alfonso")
    assert libro is not None and libro.tema != "beam"


def test_sin_verbo_de_envio_no_encuentra_nada(tmp_path, monkeypatch):
    mc = _libros(tmp_path, monkeypatch)
    assert mc.libro_nombrado("Alfonso me escribió preguntando por el avance") is None


def test_cliente_que_no_existe_no_encuentra_nada(tmp_path, monkeypatch):
    mc = _libros(tmp_path, monkeypatch)
    assert mc.libro_nombrado("ya le avisé a Roberto") is None


def test_avise_y_entregue_tambien_cuentan(tmp_path, monkeypatch):
    mc = _libros(tmp_path, monkeypatch)
    assert mc.libro_nombrado("ya le avisé a Milo que iba tarde").tema == "beam"
    assert mc.libro_nombrado("ya le entregué el reporte a Milo").tema == "beam"

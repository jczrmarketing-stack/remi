"""trabajo.es_carpeta_de_proyecto / es_ruta_de_pruebas: una carpeta de
pytest nunca es un proyecto, con o sin .git adentro (1-oct)."""
import trabajo


def test_es_carpeta_de_proyecto_con_ruta_pytest_da_false(tmp_path):
    repo = tmp_path / "pytest-of-juancamilo" / "pytest-99" / "test_algo0" / "repo"
    (repo / ".git").mkdir(parents=True)
    assert trabajo.es_carpeta_de_proyecto(str(repo)) is False


def test_es_carpeta_de_proyecto_con_tmp_path_da_false(tmp_path):
    """tmp_path de pytest ya vive bajo /private/var/folders (o $TMPDIR):
    ni hace falta el literal «pytest-of-» para que cuente."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    assert trabajo.es_carpeta_de_proyecto(str(repo)) is False


def test_es_ruta_de_pruebas_reconoce_los_cuatro_patrones():
    assert trabajo.es_ruta_de_pruebas("/cualquier/cosa/pytest-of-juancamilo/x") is True
    assert trabajo.es_ruta_de_pruebas("/tmp/algo") is True
    assert trabajo.es_ruta_de_pruebas("/private/var/folders/hg/x/T/algo") is True
    assert trabajo.es_ruta_de_pruebas("/Users/juancamilo/proyectos/remi") is False


def test_es_ruta_de_pruebas_mira_tmpdir(monkeypatch, tmp_path):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    assert trabajo.es_ruta_de_pruebas(str(tmp_path / "algo" / "repo")) is True

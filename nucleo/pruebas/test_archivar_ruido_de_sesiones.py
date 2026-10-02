"""T11.2: archiva sin borrar las ideas de ruido de sesiones que quedaron
de antes de T8.0."""
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _modulo(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sys.path.insert(0, str(SCRIPTS))
    for mod in ("archivar_ruido_de_sesiones", "db", "trabajo"):
        sys.modules.pop(mod, None)
    return importlib.import_module("archivar_ruido_de_sesiones")


def _idea(modulo, texto, estado="enfriando"):
    from modelos import Idea

    conexion = modulo.db.conectar()
    ahora = datetime.now(timezone.utc)
    idea = Idea(
        id=uuid4(), texto=texto, origen="texto", creada_en=ahora, enfria_hasta=ahora,
        estado=estado, problema_vision=None, tema=None,
    )
    modulo.db.crear_idea(conexion, idea)
    if estado != "enfriando":
        conexion.execute("UPDATE ideas SET estado = ? WHERE id = ?", (estado, str(idea.id)))
        conexion.commit()
    conexion.close()
    return idea.id


def test_dry_run_no_archiva_nada(tmp_path, monkeypatch):
    modulo = _modulo(tmp_path, monkeypatch)
    _idea(modulo, "proyecto sin ficha: /Users/juancamilo/proyectos/remi-mente")
    monkeypatch.setattr(sys, "argv", ["archivar_ruido_de_sesiones.py"])

    codigo = modulo.main()

    assert codigo == 0
    conexion = modulo.db.conectar()
    assert modulo.db.listar_ideas(conexion)[0].estado == "enfriando"


def test_archiva_proyecto_sin_ficha_y_que_te_falta(tmp_path, monkeypatch):
    modulo = _modulo(tmp_path, monkeypatch)
    id_mente = _idea(modulo, "proyecto sin ficha: /Users/juancamilo/proyectos/remi-mente")
    id_nucleo = _idea(modulo, "proyecto sin ficha: /Users/juancamilo/proyectos/remi-nucleo")
    id_falta = _idea(modulo, "que te falta para que estes al 100% listo")
    monkeypatch.setattr(sys, "argv", ["archivar_ruido_de_sesiones.py", "--si"])

    codigo = modulo.main()

    assert codigo == 0
    conexion = modulo.db.conectar()
    por_id = {i.id: i.estado for i in modulo.db.listar_ideas(conexion)}
    assert por_id[id_mente] == "archivada"
    assert por_id[id_nucleo] == "archivada"
    assert por_id[id_falta] == "archivada"


def test_no_toca_una_idea_real_que_solo_menciona_falta(tmp_path, monkeypatch):
    modulo = _modulo(tmp_path, monkeypatch)
    id_real = _idea(
        modulo,
        "para el proyecto de Malik todavía falta decidir qué hacemos con las cuentas suspendidas",
    )
    monkeypatch.setattr(sys, "argv", ["archivar_ruido_de_sesiones.py", "--si"])

    modulo.main()

    conexion = modulo.db.conectar()
    assert modulo.db.listar_ideas(conexion)[0].estado == "enfriando"
    _ = id_real


def test_no_toca_una_idea_ya_revisada(tmp_path, monkeypatch):
    modulo = _modulo(tmp_path, monkeypatch)
    id_vieja = _idea(modulo, "proyecto sin ficha: /tmp/algo", estado="soltada")
    monkeypatch.setattr(sys, "argv", ["archivar_ruido_de_sesiones.py", "--si"])

    modulo.main()

    conexion = modulo.db.conectar()
    assert modulo.db.listar_ideas(conexion)[0].estado == "soltada"
    _ = id_vieja

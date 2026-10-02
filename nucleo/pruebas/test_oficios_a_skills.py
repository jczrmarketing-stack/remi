"""T9.4: oficios <-> skills, una sola fuente."""
import importlib
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _modulo(nombre, tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    sys.path.insert(0, str(SCRIPTS))
    for mod in ("oficios_a_skills", "skill_a_oficio", "sembrar_conocimiento", "boveda_git", "libros"):
        sys.modules.pop(mod, None)
    modulo = importlib.import_module(nombre)
    return modulo


def _oficio(tmp_path, nombre, titulo, resumen, cuerpo="Cuerpo del oficio."):
    carpeta = tmp_path / "boveda" / "oficios"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{nombre}.md").write_text(
        f"---\ntitulo: {titulo}\ntema: oficio-{nombre}\nresumen: {resumen}\ntipo: oficio\n---\n\n{cuerpo}\n"
    )


def test_oficios_a_skills_dry_run_no_escribe_nada(tmp_path, monkeypatch):
    mod = _modulo("oficios_a_skills", tmp_path, monkeypatch)
    _oficio(tmp_path, "stack", "Stack", "El stack de Remi.")
    carpeta_skills = tmp_path / "skills-usuario"
    monkeypatch.setattr(mod, "CARPETA_SKILLS_USUARIO", carpeta_skills)
    monkeypatch.setattr(sys, "argv", ["oficios_a_skills.py"])

    codigo = mod.main()

    assert codigo == 0
    assert not carpeta_skills.exists()


def test_oficios_a_skills_escribir_crea_el_skill_md(tmp_path, monkeypatch):
    mod = _modulo("oficios_a_skills", tmp_path, monkeypatch)
    _oficio(tmp_path, "stack", "Stack", "El stack de Remi.", cuerpo="Python, SQLite, FTS5.")
    carpeta_skills = tmp_path / "skills-usuario"
    monkeypatch.setattr(mod, "CARPETA_SKILLS_USUARIO", carpeta_skills)
    monkeypatch.setattr(sys, "argv", ["oficios_a_skills.py", "--escribir"])

    codigo = mod.main()

    assert codigo == 0
    destino = carpeta_skills / "remi-oficio-stack" / "SKILL.md"
    assert destino.exists()
    texto = destino.read_text()
    assert "name: remi-oficio-stack" in texto
    assert "El stack de Remi." in texto
    assert "Python, SQLite, FTS5." in texto


def test_skill_a_oficio_trae_un_skill_simple(tmp_path, monkeypatch):
    mod = _modulo("skill_a_oficio", tmp_path, monkeypatch)
    carpeta_skill = tmp_path / "mi-skill"
    carpeta_skill.mkdir()
    (carpeta_skill / "SKILL.md").write_text(
        "---\nname: mi-skill\ndescription: Un skill de prueba.\n---\n\nEl cuerpo del skill.\n"
    )
    monkeypatch.setattr(sys, "argv", ["skill_a_oficio.py", str(carpeta_skill)])

    codigo = mod.main()

    assert codigo == 0
    destino = tmp_path / "boveda" / "oficios" / "mi-skill.md"
    assert destino.exists()
    texto = destino.read_text()
    assert "tipo: oficio" in texto
    assert "El cuerpo del skill." in texto


def test_skill_a_oficio_con_scripts_se_niega(tmp_path, monkeypatch):
    mod = _modulo("skill_a_oficio", tmp_path, monkeypatch)
    carpeta_skill = tmp_path / "mi-skill"
    carpeta_skill.mkdir()
    (carpeta_skill / "SKILL.md").write_text("---\nname: mi-skill\ndescription: d\n---\n\nCuerpo.\n")
    (carpeta_skill / "corre.py").write_text("print('hola')\n")
    monkeypatch.setattr(sys, "argv", ["skill_a_oficio.py", str(carpeta_skill)])

    codigo = mod.main()

    assert codigo == 1
    assert not (tmp_path / "boveda" / "oficios" / "mi-skill.md").exists()


def test_skill_a_oficio_nunca_pisa_uno_que_ya_existe(tmp_path, monkeypatch):
    mod = _modulo("skill_a_oficio", tmp_path, monkeypatch)
    _oficio(tmp_path, "mi-skill", "Ya existía", "r")
    carpeta_skill = tmp_path / "mi-skill"
    carpeta_skill.mkdir()
    (carpeta_skill / "SKILL.md").write_text("---\nname: mi-skill\ndescription: d\n---\n\nCuerpo nuevo.\n")
    monkeypatch.setattr(sys, "argv", ["skill_a_oficio.py", str(carpeta_skill)])

    codigo = mod.main()

    assert codigo == 1
    assert "Ya existía" in (tmp_path / "boveda" / "oficios" / "mi-skill.md").read_text()

"""La config de mypy ignora solo los módulos sin tipos, sin apagar mypy en general."""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _mypy() -> dict:
    with (RAIZ / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["tool"]["mypy"]


def test_override_lista_exacta():
    overrides = [o for o in _mypy()["overrides"] if o.get("ignore_missing_imports")]
    assert len(overrides) == 1
    assert sorted(overrides[0]["module"]) == sorted(
        ["kokoro.*", "soundfile.*", "sqlite_vec.*", "sentence_transformers.*", "afirmaciones"]
    )


def test_sin_ignore_global():
    assert "ignore_missing_imports" not in _mypy()


def test_afirmaciones_puente_sigue_revisado():
    modulos = [m for o in _mypy()["overrides"] for m in o["module"]]
    assert "afirmaciones_puente" not in modulos
    assert "afirmaciones.*" not in modulos
    assert "*" not in modulos

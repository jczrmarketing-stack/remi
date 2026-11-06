"""El Portero: hook PreToolUse de cada agente de la fábrica, 0 tokens."""

import importlib.util
import io
import json
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "fabrica" / "portero" / "portero.py"
_spec = importlib.util.spec_from_file_location("portero", RUTA)
assert _spec and _spec.loader
portero = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(portero)


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def escribir(ruta, herramienta="Write"):
    return {"tool_name": herramienta, "tool_input": {"file_path": ruta}}


@pytest.mark.parametrize("cmd", [
    "git push",
    "git push --force origin x",
    "git commit -m x",
    "rm -rf build",
    "rm -r nucleo",
    "git branch -D x",
    "git reset --hard",
    "vercel deploy",
    "npm publish",
    "cd /tmp && echo x > a",
    "echo x > /etc/hosts",
    "git checkout main",
])
def test_niega_bash_peligroso(tmp_path, cmd):
    assert portero.decidir(bash(cmd), tmp_path)


@pytest.mark.parametrize("cmd", [
    "/Users/x/.venv/bin/python -m pytest nucleo/pruebas/test_x.py -q",
    "git status",
    "git diff main",
    "ls",
    "echo hola > nucleo/a.txt",
])
def test_deja_bash_inofensivo(tmp_path, cmd):
    assert portero.decidir(bash(cmd), tmp_path) is None


@pytest.mark.parametrize("ruta", ["/etc/x", "{wt}/../otro/a.py", "~/x", "../../x"])
def test_niega_escribir_fuera_del_worktree(tmp_path, ruta, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert portero.decidir(escribir(ruta.format(wt=tmp_path)), tmp_path)


@pytest.mark.parametrize("ruta", ["{wt}/nucleo/a.py", "nucleo/a.py"])
def test_deja_escribir_dentro_del_worktree(tmp_path, ruta, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert portero.decidir(escribir(ruta.format(wt=tmp_path), "Edit"), tmp_path) is None


def test_lectura_dentro_del_worktree_pasa(tmp_path):
    (tmp_path / "nucleo").mkdir()
    assert portero.decidir({"tool_name": "Read", "tool_input": {"file_path": str(tmp_path / "nucleo" / "x.py")}}, tmp_path) is None
    assert portero.decidir({"tool_name": "Read", "tool_input": {"file_path": "nucleo/x.py"}, "cwd": str(tmp_path)}, tmp_path) is None
    assert portero.decidir({"tool_name": "Grep", "tool_input": {"pattern": "x"}}, tmp_path) is None   # sin path = el cwd


@pytest.mark.parametrize("evento", [
    {"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}},
    {"tool_name": "Read", "tool_input": {"file_path": "../../nucleo/.env"}},
    {"tool_name": "Grep", "tool_input": {"pattern": "TOKEN", "path": "/Users"}},
    {"tool_name": "Glob", "tool_input": {"pattern": "**/*", "path": ".."}},
])
def test_lectura_fuera_del_worktree_se_niega(tmp_path, evento):
    """6-nov: los escenarios ocultos del Tester y el nucleo/.env del checkout principal viven fuera del worktree."""
    motivo = portero.decidir({**evento, "cwd": str(tmp_path)}, tmp_path)
    assert motivo and "Solo se lee dentro del worktree" in motivo


def test_main_imprime_deny_en_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FABRICA_WORKTREE", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(bash("git push --force"))))
    assert portero.main() == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert salida["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def test_main_sin_worktree_niega_lo_que_escribe(monkeypatch, capsys):
    monkeypatch.delenv("FABRICA_WORKTREE", raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(escribir("/tmp/x"))))
    portero.main()
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_deja_pasar_sin_imprimir(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FABRICA_WORKTREE", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(bash("git status"))))
    assert portero.main() == 0
    assert capsys.readouterr().out == ""

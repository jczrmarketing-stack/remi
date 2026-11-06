"""La vitrina de la fábrica en el piso Ingeniería: paso calmado, estaciones y lista, sin IA."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import suite
from fabrica import expediente, vitrina


def _pedido(raiz: Path, idea: str, estado: str, eventos: list[dict] | None = None, noche: int = 0) -> str:
    id_ = expediente.crear(idea, "remi", "origin/main", raiz)
    expediente.cambiar(id_, raiz, estado=estado, noche=noche)
    if eventos:
        ruta = expediente.carpeta(id_, raiz) / "eventos.jsonl"
        ruta.write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")
    return id_


EVS_PR = [{"rol": "linea", "tipo": "estacion", "texto": "spec"}, {"rol": "linea", "tipo": "estacion", "texto": "verificar"},
          {"rol": "revisor", "tipo": "fin", "texto": "cumple"}, {"rol": "linea", "tipo": "estacion", "texto": "pr"},
          {"rol": "linea", "tipo": "fin", "texto": "https://github.com/x/remi/pull/4"}]


def test_repo_principal_sale_del_archivo_git_del_worktree(tmp_path):
    principal = tmp_path / "remi"
    (principal / ".git" / "worktrees" / "fabrica").mkdir(parents=True)
    casa = principal / ".worktrees" / "fabrica"
    casa.mkdir(parents=True)
    (casa / ".git").write_text(f"gitdir: {principal / '.git' / 'worktrees' / 'fabrica'}\n")
    assert expediente.repo_principal(casa) == principal
    assert expediente.repo_principal(principal) == principal   # el principal tiene .git carpeta


def test_sin_pedidos_no_hay_paso_ni_linea(tmp_path):
    r = vitrina.piso(tmp_path)
    assert "paso" not in r and "linea" not in r and r["corriendo"] is False


def test_pr_en_borrador_pide_revision_con_el_link(tmp_path):
    _pedido(tmp_path, "Mandar un documento al bot de Telegram revienta: nucleo/telegram.py:268 llama a algo que no existe", "pr", EVS_PR)
    r = vitrina.piso(tmp_path)
    assert r["paso"]["titulo"] == "Un PR espera tu revisión."
    assert r["paso"]["ruta"] == "https://github.com/x/remi/pull/4"
    assert "Mandar un documento al bot de Telegram revienta" in r["paso"]["contexto"]
    assert [e["estado"] for e in r["linea"]["estaciones"]] == ["hecha"] * 6
    assert r["entra"]["filas"][0][1] == "PR en borrador"


def test_spec_espera_tu_si_con_el_comando(tmp_path):
    id_ = _pedido(tmp_path, "Arreglar algo chico", "spec", [{"rol": "linea", "tipo": "estacion", "texto": "spec"}])
    r = vitrina.piso(tmp_path)
    assert r["paso"]["titulo"] == "Una spec espera tu sí."
    assert f"aprobar {id_}" in r["paso"]["contexto"]
    assert [e["estado"] for e in r["linea"]["estaciones"]] == ["hecha"] + ["por_venir"] * 5


def test_corriendo_marca_la_estacion_activa_y_el_revisor_es_revisar(tmp_path):
    evs = [{"rol": "linea", "tipo": "estacion", "texto": "verificar"}, {"rol": "revisor", "tipo": "herramienta", "texto": "Grep"}]
    _pedido(tmp_path, "Algo", "revisando", evs)
    (tmp_path / ".candado").write_text(str(os.getpid()))
    r = vitrina.piso(tmp_path)
    assert r["corriendo"] is True and r["paso"]["titulo"] == "Nada que hacer: la línea trabaja."
    assert [e["estado"] for e in r["linea"]["estaciones"]] == ["hecha"] * 4 + ["activa", "por_venir"]


def test_candado_de_un_proceso_muerto_no_cuenta(tmp_path):
    _pedido(tmp_path, "Algo", "construyendo", [{"rol": "linea", "tipo": "estacion", "texto": "construir"}])
    (tmp_path / ".candado").write_text("999999")
    assert vitrina.piso(tmp_path)["corriendo"] is False


def test_cola_de_noche_sin_spec_dice_que_la_fabrica_trabaja_de_noche(tmp_path):
    for i in range(3):
        _pedido(tmp_path, f"mypy pedido {i}", "idea", noche=1)
    r = vitrina.piso(tmp_path)
    assert r["paso"]["titulo"] == "Nada que hacer: la fábrica trabaja de noche."
    assert "3 pedidos" in r["paso"]["contexto"]


def test_la_lista_trae_maximo_cinco_y_los_cerrados_al_final(tmp_path):
    _pedido(tmp_path, "viejo cerrado", "cerrado")
    for i in range(6):
        _pedido(tmp_path, f"abierto {i}", "idea", noche=1)
    filas = vitrina.piso(tmp_path)["entra"]["filas"]
    assert len(filas) == 5 and all(f[1] != "cerrado" for f in filas)


def test_la_suite_pone_la_linea_en_ingenieria_y_no_en_otros_pisos(tmp_path):
    fab = {"corriendo": True, "paso": {"titulo": "Nada que hacer: la línea trabaja."}, "linea": {"id": "x", "estaciones": []},
           "entra": {"titulo": "Pedidos de la fábrica", "fuente": "de la cola", "filas": [["x", "construyendo"]]},
           "horario": ["La fábrica, un pedido por noche", "02:30"]}
    r = suite.armar(hoy=date(2026, 11, 6), ficha={}, boveda={"leyendo": False, "agenda": {}}, temas=([], ""), agentes={},
                    cobros=[], pisos_publicados={}, cajones={}, norte={}, fabrica=fab)
    ing = next(p for p in r["pisos"] if p["id"] == "ingenieria")
    assert ing["luz"] is True and ing["linea"]["id"] == "x" and ing["paso"]["titulo"].startswith("Nada que hacer")
    assert ing["entra"][0]["titulo"] == "Pedidos de la fábrica"
    horario = next(e for e in ing["entra"] if e["titulo"] == "Horario automático")
    assert horario["filas"][0] == ["La fábrica, un pedido por noche", "02:30"]
    assert all("linea" not in p for p in r["pisos"] if p["id"] != "ingenieria")


def test_si_la_fabrica_revienta_la_suite_se_pinta_igual(monkeypatch):
    def rota(raiz=None):
        raise RuntimeError("disco raro")
    monkeypatch.setattr(vitrina, "piso", rota)
    assert suite._fabrica() == {}


def test_la_cli_usa_el_remi_db_del_checkout_principal(monkeypatch, tmp_path):
    import fabrica.__main__ as cli

    monkeypatch.delenv("REMI_DB_PATH", raising=False)
    monkeypatch.setattr(expediente, "repo_principal", lambda repo=None: tmp_path)
    monkeypatch.setattr(cli.linea, "noche", lambda mundo=None: ("nada", None))
    cli.main(["noche"])
    assert os.environ["REMI_DB_PATH"] == str(tmp_path / "nucleo" / "remi.db")

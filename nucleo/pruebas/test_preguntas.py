"""T3 (fase Q, Biblia v3.8): Remi pregunta lo que le falta. Bóveda
temporal siempre — nunca contra remi-mente real. Nada de esto llama a un
modelo (sin mensaje.think, sin pensar.py de por medio)."""
import importlib
import sys
from datetime import timedelta

from fastapi.testclient import TestClient

SIN_TIPO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo.
"""

CLIENTE_SIN_CLIENTE = """---
titulo: BeaM
tema: beam
resumen: r
tipo: cliente
---

Cuerpo.
"""

CLIENTE_CON_FASES_Y_RUTA_VACIA = """---
titulo: UpVisuals
tema: upvisuals
resumen: r
tipo: cliente
cliente: Alfonso
ruta:
fases:
  - nombre: Fase 1
    alcance: a
    monto: 5000
    listo_cuando:
    estado: pagando
  - nombre: Fase 2
    alcance: b
    monto: 3700
    listo_cuando: Demo aprobada
    estado: propuesta
---

## Camino

- [ ] Intake
"""

CON_COMPLETAR = """---
titulo: BeaM
tema: beam
resumen: r
---

- (Completar: para quién es, precio, próximo paso.)
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "modelos", "libros", "preguntas", "boveda_git"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor, carpeta


def test_un_libro_sin_tipo_produce_la_pregunta_de_tipo(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    cliente = TestClient(servidor.app)

    preguntas = cliente.get("/preguntas").json()

    assert any(p["campo"] == "tipo" and p["tema"] == "malik" for p in preguntas)
    pregunta = next(p for p in preguntas if p["campo"] == "tipo")
    assert pregunta["voz"] == "¿Malik es de un cliente o es tuyo?"


def test_contestar_de_un_cliente_escribe_tipo_cliente_con_commit(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    cliente = TestClient(servidor.app)
    pregunta = next(p for p in cliente.get("/preguntas").json() if p["campo"] == "tipo")

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "de un cliente"})

    assert respuesta.status_code == 200
    assert respuesta.json()["pregunta"]["estado"] == "respondida"
    assert "tipo: cliente" in (carpeta / "malik.md").read_text()
    # No vuelve a aparecer.
    assert not any(p["campo"] == "tipo" for p in cliente.get("/preguntas").json())


def test_despues_la_saca_hasta_el_dia_siguiente(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    cliente = TestClient(servidor.app)
    pregunta = next(p for p in cliente.get("/preguntas").json() if p["campo"] == "tipo")

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/despues")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "despues"

    assert not any(p["campo"] == "tipo" for p in cliente.get("/preguntas").json())


def test_nunca_hay_mas_de_tres_a_la_vista(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    for letra in "abcde":
        (carpeta / f"{letra}.md").write_text(
            f"---\ntitulo: {letra.upper()}\ntema: {letra}\nresumen: r\n---\n\nCuerpo.\n"
        )
    cliente = TestClient(servidor.app)

    preguntas = cliente.get("/preguntas").json()

    assert len(preguntas) == 3


def test_fase_sin_listo_cuando_pregunta_y_la_respuesta_queda_en_el_archivo(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "upvisuals.md").write_text(CLIENTE_CON_FASES_Y_RUTA_VACIA)
    cliente = TestClient(servidor.app)
    pregunta = next(
        p for p in cliente.get("/preguntas", params={"tema": "upvisuals"}).json()
        if p["campo"] == "fase.1.listo_cuando"
    )

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "Demo aprobada por Alfonso"})

    assert respuesta.status_code == 200
    assert respuesta.json()["pregunta"]["estado"] == "respondida"
    libro = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert libro["fases"][0]["listo_cuando"] == "Demo aprobada por Alfonso"
    assert libro["fases"][1]["listo_cuando"] == "Demo aprobada"  # la otra fase no se tocó


def test_fase_pagando_sin_cobro_pregunta_y_la_respuesta_crea_la_entrega(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "upvisuals.md").write_text(CLIENTE_CON_FASES_Y_RUTA_VACIA)
    cliente = TestClient(servidor.app)
    pregunta = next(
        p for p in cliente.get("/preguntas", params={"tema": "upvisuals"}).json()
        if p["campo"] == "fase.1.cobrado"
    )

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "1500"})

    assert respuesta.status_code == 200
    assert respuesta.json()["pregunta"]["estado"] == "respondida"
    libro = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert libro["fases"][0]["cobrado"] == 1500.0


def test_ruta_vacia_pregunta_y_la_respuesta_agrega_sin_borrar(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "upvisuals.md").write_text(CLIENTE_CON_FASES_Y_RUTA_VACIA)
    cliente = TestClient(servidor.app)
    pregunta = next(
        p for p in cliente.get("/preguntas", params={"tema": "upvisuals"}).json() if p["campo"] == "ruta"
    )

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "~/upvisuals"})

    assert respuesta.status_code == 200
    texto = (carpeta / "upvisuals.md").read_text()
    assert "- " in texto.split("ruta:")[1].split("\n")[1]


def test_completar_cambia_la_linea_por_la_respuesta(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "beam.md").write_text(CON_COMPLETAR)
    cliente = TestClient(servidor.app)
    pregunta = next(p for p in cliente.get("/preguntas").json() if p["campo"].startswith("completar."))

    respuesta = cliente.post(
        f"/preguntas/{pregunta['id']}/respuesta",
        json={"texto": "Es para Alfonso, 500 USD, el próximo paso es el contrato"},
    )

    assert respuesta.status_code == 200
    texto = (carpeta / "beam.md").read_text()
    assert "(Completar:" not in texto
    assert "Es para Alfonso" in texto


def test_respuesta_que_no_se_entiende_no_guarda_nada(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    cliente = TestClient(servidor.app)
    pregunta = next(p for p in cliente.get("/preguntas").json() if p["campo"] == "tipo")

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "no sé"})

    assert respuesta.status_code == 200
    assert respuesta.json()["pregunta"]["estado"] == "pendiente"
    assert "tipo:" not in (carpeta / "malik.md").read_text()
    # Sigue a la vista: no se perdió.
    assert any(p["campo"] == "tipo" for p in cliente.get("/preguntas").json())


def test_pregunta_de_tema_inexistente_404(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    assert cliente.post(
        "/preguntas/99999999-9999-9999-9999-999999999999/respuesta", json={"texto": "x"}
    ).status_code == 404
    assert cliente.post(
        "/preguntas/99999999-9999-9999-9999-999999999999/despues"
    ).status_code == 404

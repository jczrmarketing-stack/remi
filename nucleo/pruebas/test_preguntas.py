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


def test_fase_con_listo_cuando_pero_sin_minutos_estimados_pregunta(tmp_path, monkeypatch):
    """B6.2: solo se pregunta minutos_estimados si la fase YA tiene
    listo_cuando — Fase 1 (sin listo_cuando) no pregunta, Fase 2 sí."""
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "upvisuals.md").write_text(CLIENTE_CON_FASES_Y_RUTA_VACIA)
    cliente = TestClient(servidor.app)
    preguntas = cliente.get("/preguntas", params={"tema": "upvisuals"}).json()
    campos = [p["campo"] for p in preguntas]
    assert "fase.1.minutos_estimados" not in campos
    assert "fase.2.minutos_estimados" in campos

    pregunta = next(p for p in preguntas if p["campo"] == "fase.2.minutos_estimados")
    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "unas 20 horas"})

    assert respuesta.status_code == 200
    assert respuesta.json()["pregunta"]["estado"] == "respondida"
    libro = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert libro["fases"][1]["minutos_estimados"] == 1200
    assert libro["fases"][0]["minutos_estimados"] is None  # la otra fase no se tocó


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
    # Con minutos_estimados ya puesto en la Fase 2: evita competir con
    # «ruta» por los MAXIMO_VISIBLES=3 cupos de este libro (B6.2).
    (carpeta / "upvisuals.md").write_text(
        CLIENTE_CON_FASES_Y_RUTA_VACIA.replace(
            "    listo_cuando: Demo aprobada\n    estado: propuesta",
            "    listo_cuando: Demo aprobada\n    estado: propuesta\n    minutos_estimados: 600",
        )
    )
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


def test_t3_7_la_voz_de_cada_detector_cumple_la_ley(tmp_path, monkeypatch):
    """De tú, 20 palabras como mucho, sin exclamaciones de urgencia."""
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    (carpeta / "beam.md").write_text(CLIENTE_SIN_CLIENTE)
    (carpeta / "upvisuals.md").write_text(CLIENTE_CON_FASES_Y_RUTA_VACIA)
    (carpeta / "malik.md").write_text(SIN_TIPO)
    (carpeta / "x.md").write_text(CON_COMPLETAR)
    import db
    import preguntas

    conexion = db.conectar()
    try:
        detectadas = preguntas.detectar(conexion)
    finally:
        conexion.close()

    assert detectadas
    for detectada in detectadas:
        voz = detectada.voz
        assert len(voz.split()) <= 20, voz
        assert "!" not in voz, voz
        assert "usted" not in voz.lower(), voz


# — F3.3 (plan de cierre): las tres formas de «(Completar …)» de la bóveda —

CON_COMPLETAR_SIN_DOS_PUNTOS = """---
titulo: Mi voz
tema: oficio-mi-voz
resumen: r
---

- (Completar con mensajes reales.)
"""

CON_COMPLETAR_CON_ETIQUETA = """---
titulo: Clientes
tema: oficio-clientes
resumen: r
---

- Piso de precio por fase: (completar; ejemplo real: Fase 1 UpVisuals USD 5.000).
"""

AREA_SALUD = """---
titulo: Cuerpo y salud
tema: salud
resumen: r
---

- (Completar: lo que Remi tiene que saber de esto.)
"""

AREA_APRENDER = AREA_SALUD.replace("Cuerpo y salud", "Aprender").replace("tema: salud", "tema: aprender")


def test_completar_sin_dos_puntos_y_con_etiqueta_tambien_se_detectan(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    oficios = carpeta.parent / "oficios"
    oficios.mkdir()
    (oficios / "mi-voz.md").write_text(CON_COMPLETAR_SIN_DOS_PUNTOS)
    (oficios / "clientes.md").write_text(CON_COMPLETAR_CON_ETIQUETA)
    cliente = TestClient(servidor.app)

    voces = {p["tema"]: p["voz"] for p in cliente.get("/preguntas?tema=oficio-mi-voz").json()}
    assert voces == {"oficio-mi-voz": "¿mensajes reales de Mi voz?"}
    voces = {p["tema"]: p["voz"] for p in cliente.get("/preguntas?tema=oficio-clientes").json()}
    assert voces == {"oficio-clientes": "¿Piso de precio por fase de Clientes?"}


def test_la_respuesta_con_etiqueta_conserva_la_etiqueta(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    oficios = carpeta.parent / "oficios"
    oficios.mkdir()
    (oficios / "clientes.md").write_text(CON_COMPLETAR_CON_ETIQUETA)
    cliente = TestClient(servidor.app)
    pregunta = cliente.get("/preguntas?tema=oficio-clientes").json()[0]

    respuesta = cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "USD 3.000"})

    assert respuesta.status_code == 200
    texto = (oficios / "clientes.md").read_text()
    assert "- Piso de precio por fase: USD 3.000\n" in texto
    assert "completar" not in texto.lower()


def test_la_respuesta_va_al_archivo_del_tema_aunque_otro_tenga_completar_en_la_misma_linea(tmp_path, monkeypatch):
    servidor, carpeta = _arrancar(tmp_path, monkeypatch)
    areas = carpeta.parent / "areas"
    areas.mkdir()
    (areas / "aprender.md").write_text(AREA_APRENDER)
    (areas / "salud.md").write_text(AREA_SALUD)
    cliente = TestClient(servidor.app)
    pregunta = next(p for p in cliente.get("/preguntas?tema=salud").json() if p["campo"].startswith("completar."))

    assert cliente.post(f"/preguntas/{pregunta['id']}/respuesta", json={"texto": "Duermo poco."}).status_code == 200

    assert "Duermo poco." in (areas / "salud.md").read_text()
    assert "(Completar:" in (areas / "aprender.md").read_text()

"""T2.3–T2.7: la plata y la agenda entran por voz. Los «listo cuando» de
docs/PLAN-100.md, uno por uno, nunca contra la base real."""
import importlib
import sys
from datetime import timedelta

from fastapi.testclient import TestClient

LIBRO_UPVISUALS = """---
titulo: UpVisuals
tema: upvisuals
resumen: Plataforma de Alfonso.
tipo: cliente
cliente: Alfonso
claves: [upvisuals, alfonso]
fases:
  - nombre: Fase 1
    alcance: a
    monto: 5000
    listo_cuando:
    estado: pagando
---

Cuerpo.
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_UPVISUALS)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "modelos", "libros", "temas", "cobros", "agenda", "bandeja", "pensar", "clasificar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _dia(servidor, delta: int) -> str:
    return (servidor.hoy_en_bogota() + timedelta(days=delta)).isoformat()


# — T2.3: entrega hablada —


def test_entrega_hablada_cae_en_el_libro_del_cliente(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/mensaje", json={"texto": "entrega para Alfonso el 18 de octubre por 5.000"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] == "entrega"
    entregas_de_upvisuals = cliente.get(
        f"/entregas/de-proyecto/{__import__('entregas')._proyecto_id_de_tema('upvisuals')}"
    ).json()
    assert entregas_de_upvisuals is not None
    assert entregas_de_upvisuals["cliente"] == "Alfonso"


# — T2.4: cobro hablado —


def test_alfonso_pago_1500_llena_la_fase_y_el_mes(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "Alfonso pagó 1500"})

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] == "cobro"
    libro = {l["tema"]: l for l in cliente.get("/libros").json()}["upvisuals"]
    assert libro["fases"][0]["cobrado"] == 1500.0
    assert cliente.get("/plata").json()["mes"]["cobrado"] == 1500.0


def test_un_cobro_sin_de_quien_no_se_adivina(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "me pagaron 1500"})

    assert respuesta.json()["tipo"] != "cobro"


def test_un_cobro_cierra_el_hito_de_pago_abierto(tmp_path, monkeypatch):
    """B3.1: el cobro mismo es la evidencia del hito «Pago antes de
    arrancar» (cierra_con == "cobro") — se cierra solo, sin pedir nada más."""
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(
        LIBRO_UPVISUALS.replace(
            "---\n\nCuerpo.\n",
            "---\n\n## Camino\n\n- [x] Intake\n- [x] Descubrimiento (5 preguntas)\n"
            "- [x] Propuesta por fases\n- [x] Contrato\n- [ ] Pago antes de arrancar\n",
        )
    )
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "modelos", "libros", "temas", "cobros", "agenda", "bandeja", "pensar", "clasificar", "caminos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "Alfonso pagó 1500"})
    assert respuesta.json()["tipo"] == "cobro"

    import caminos
    import libros

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    assert caminos.leer_hitos(libro.archivo)[4].hecho is True
    conexion = db.conectar()
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()
    assert cerrado is not None and cerrado.tipo == "cobro"


def test_un_abono_parcial_no_cierra_pago_antes_de_arrancar(tmp_path, monkeypatch):
    """Revisión de B3: en cuotas, el trabajo empieza cuando el pago está
    COMPLETO (SOP) — un primer abono no puede cerrar el hito solo."""
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(
        LIBRO_UPVISUALS.replace(
            "---\n\nCuerpo.\n",
            "---\n\n## Camino\n\n- [x] Intake\n- [x] Descubrimiento (5 preguntas)\n"
            "- [x] Propuesta por fases\n- [x] Contrato\n- [ ] Pago antes de arrancar\n",
        )
    )
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("servidor", "db", "modelos", "libros", "temas", "cobros", "agenda", "bandeja", "pensar", "clasificar", "caminos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    cliente = TestClient(servidor.app)

    # La segunda cuota, pendiente, registrada antes del primer abono.
    cliente.post("/mensaje", json={"texto": "entrega para Alfonso el 18 de octubre por 2500"})
    respuesta = cliente.post("/mensaje", json={"texto": "Alfonso pagó 1500"})
    assert respuesta.json()["tipo"] == "cobro"

    import caminos
    import libros

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    assert caminos.leer_hitos(libro.archivo)[4].hecho is False
    conexion = db.conectar()
    assert db.hito_cerrado_de(conexion, "upvisuals", 5) is None
    conexion.close()


# — T2.5: agenda hablada —


def test_manana_llamo_al_banco_sale_en_la_agenda_de_manana(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "mañana llamo al banco"})

    assert respuesta.status_code == 200
    assert respuesta.json()["tipo"] == "agenda"
    assert respuesta.json()["sesion"] is None
    agenda = cliente.get("/hoy/agenda").json()
    assert [t["titulo"] for t in agenda["manana"]] == ["llamo al banco"]


def test_se_me_ocurrio_vender_plantillas_manana_sigue_en_la_bandeja(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post("/mensaje", json={"texto": "se me ocurrió vender plantillas mañana"})

    assert respuesta.json()["tipo"] == "idea"
    assert len(cliente.get("/bandeja").json()) == 1


# — T2.7: 15 frases reales, 5 que no deben disparar —

FRASES_QUE_DISPARAN = [
    ("mañana llamo al banco", "agenda"),
    ("pasado mañana entrego el reporte", "agenda"),
    ("a las 3 reunión con Alfonso", "agenda"),
    ("el viernes reviso el contrato", "agenda"),
    ("el 15 de octubre vence el dominio", "agenda"),
    ("vence el 20 de noviembre el hosting", "agenda"),
    ("Alfonso pagó 1500", "cobro"),
    ("me pagaron 1500 de upvisuals", "cobro"),
    ("entrega para Alfonso el 18 de octubre por 5.000", "entrega"),
    ("entrega para Beto el 1 de diciembre por 800", "entrega"),
]

FRASES_QUE_NO_DISPARAN = [
    "se me ocurrió que mañana podría vender algo",
    "quizás mañana miro el curso",
    "hoy no puedo",
    "me pagaron la confianza con esto",
    "entregué el reporte ayer",
]


def test_quince_frases_reales_disparan_lo_que_tienen_que_disparar(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    for texto, tipo_esperado in FRASES_QUE_DISPARAN:
        respuesta = cliente.post("/mensaje", json={"texto": texto})
        assert respuesta.json()["tipo"] == tipo_esperado, texto

    for texto in FRASES_QUE_NO_DISPARAN:
        respuesta = cliente.post("/mensaje", json={"texto": texto})
        assert respuesta.json()["tipo"] not in ("agenda", "cobro", "entrega"), texto

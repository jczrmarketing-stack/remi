"""«Me escribió un cliente» (Biblia Parte VI, Fase S punto 3).

Cuatro partes fijas — lectura, riesgos, respuesta recomendada, límites —
con los oficios `clientes`, `proyectos-sop` y `mi-voz` cargados de verdad.
El guardarraíl es literal: Remi nunca manda nada, solo lo propone.
"""
import importlib
import sys

import pytest

import clasificar
import pensar


@pytest.mark.parametrize(
    "frase",
    [
        "me escribió Alfonso: necesito el generador de imágenes para el viernes",
        "el cliente dice que quiere pagar todo al final",
        "me dijo que la fase 2 le urge",
        "escribió el cliente pidiendo un descuento",
    ],
)
def test_detecta_texto_de_cliente(frase):
    assert clasificar.es_texto_de_cliente(frase)


@pytest.mark.parametrize(
    "frase",
    [
        "voy a llamar al cliente mañana",
        "arranco con el contrato de Alfonso",
        "¿qué tengo pendiente con Alfonso?",
    ],
)
def test_no_confunde_hablar_del_cliente_con_que_el_cliente_escribio(frase):
    assert not clasificar.es_texto_de_cliente(frase)


PARTES = ("LECTURA", "RIESGOS", "RESPUESTA RECOMENDADA", "LÍMITES")


def test_sistema_cliente_trae_las_cuatro_partes_y_el_guardarrail():
    texto = pensar.sistema_cliente()
    for parte in PARTES:
        assert parte in texto, f"falta «{parte}» en sistema_cliente()"
    assert "Esto es un borrador" in texto
    assert "nunca envío nada" in " ".join(texto.split())


def test_sistema_cliente_carga_los_oficios_de_verdad():
    texto = pensar.sistema_cliente()
    # Contenido real de remi-mente/oficios/clientes.md.
    assert "Remi NUNCA envía nada" in texto
    # Contenido real de remi-mente/oficios/mi-voz.md.
    assert "Formal de más" in texto
    # Contenido real de remi-mente/oficios/proyectos-sop.md.
    assert "proyecto propio" in texto.lower() or "cliente nuevo" in texto.lower()


def test_pedido_real_de_lectura_de_cliente_con_el_limite_mockeado(tmp_path, monkeypatch):
    """Un «me escribió Alfonso: …» real recibe la puerta real (system
    prompt con las cuatro partes) — solo se mockea la llamada de red."""
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor as servidor_mod
    from fastapi.testclient import TestClient

    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    importlib.reload(db)
    importlib.reload(servidor_mod)

    vistos: dict[str, str] = {}

    def falso_pensar(frase, motor=None, modo=None, base=None, **_k):
        vistos["base"] = base or ""
        return servidor_mod.pensar.Pensado(
            paso_minimo=(
                "LECTURA\nQuiere el generador de imágenes antes del viernes.\n\n"
                "RIESGOS\nEl alcance de Fase 2 no está cerrado todavía.\n\n"
                "RESPUESTA RECOMENDADA\nHola Alfonso, para el viernes no llego con "
                "el alcance actual; te propongo una primera versión el lunes.\n\n"
                "LÍMITES\nFase 2 no arranca sin el pago de Fase 1 completo.\n\n"
                "Esto es un borrador — vos lo mandás, yo nunca envío nada."
            ),
            tokens_entrada=700,
            tokens_salida=90,
            modelo="modelo-de-prueba",
        )

    monkeypatch.setattr(servidor_mod.pensar, "pensar", falso_pensar)
    cliente = TestClient(servidor_mod.app)

    respuesta = cliente.post(
        "/mensaje",
        json={
            "texto": "me escribió Alfonso: necesito el generador de imágenes para el viernes",
            "think": True,
        },
    ).json()

    assert respuesta["tipo"] == "cliente"
    assert vistos["base"] != ""
    for parte in PARTES:
        assert parte in respuesta["texto"], respuesta["texto"]
    assert "nunca envío nada" in " ".join(respuesta["texto"].split())

    # Nunca se guardó como idea ni abrió un bloque: es una lectura, no un
    # pedido de Juan Camilo.
    conexion = db.conectar()
    try:
        ideas = conexion.execute("select count(*) from ideas").fetchone()[0]
        tareas = conexion.execute("select count(*) from tareas").fetchone()[0]
    finally:
        conexion.close()
    assert ideas == 0
    assert tareas == 0


def test_remi_no_tiene_forma_de_mandar_nada_a_un_cliente():
    """No existe, en ningún módulo del núcleo, una función que envíe un
    mensaje afuera (a WhatsApp, email, o cualquier API de un cliente) — el
    guardarraíl es que Remi no PUEDE enviar, no solo que el prompt se lo
    pide. Fase 4 (espejos) no está construida todavía."""
    import servidor as servidor_mod

    nombres = dir(servidor_mod)
    prohibidos = ("enviar_cliente", "enviar_whatsapp", "enviar_email", "mandar_cliente", "responder_cliente")
    for nombre in prohibidos:
        assert nombre not in nombres

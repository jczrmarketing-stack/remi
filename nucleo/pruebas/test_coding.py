"""Coding: tarea → bóveda → spec → builder → revisor → lección. Sin
llamadas reales: el llamador se inyecta."""
import importlib
import json
import sys

from fastapi.testclient import TestClient

ERROR_401 = {
    "titulo": "El 401 de malik por token vencido",
    "tema": "coding",
    "resumen": "El bot devolvía 401 porque el token de WhatsApp había vencido.",
    "clase": "error",
    "donde": "organic-cash-malik/nucleo/whatsapp.py",
    "secciones": {
        "Síntoma": "El bot contestaba 401 en cada mensaje.",
        "Lo que creímos": "",
        "Causa real": "El token de acceso de WhatsApp había vencido.",
        "Cura": "Se renovó el token.",
        "Cómo verlo antes": "Revisar la fecha de expiración del token.",
    },
    "fuente": "manual",
}


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("servidor", "db", "experiencia", "episodios", "libros", "coding"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    import coding

    return servidor, coding


def _llamador(veredicto, vistos):
    def llamar(etapa, mensaje):
        vistos.append((etapa, mensaje))
        textos = {"spec": "spec corto", "builder": "```diff\n+x\n```", "revisor": json.dumps(veredicto)}
        return __import__("coding").Respuesta(textos[etapa], 10, 5)

    return llamar


def test_la_boveda_viaja_al_spec_y_al_builder(tmp_path, monkeypatch):
    servidor, coding = _arrancar(tmp_path, monkeypatch)
    TestClient(servidor.app).post("/experiencia", json=ERROR_401)
    monkeypatch.setattr(coding.experiencia.vectores, "asociar", lambda *a, **k: [])
    vistos: list = []

    corrida = coding.correr(
        coding.Corrida(id="1", tarea="arreglar el 401 del token de whatsapp"),
        _llamador({"veredicto": "aprobado", "motivo": "ok", "leccion": None}, vistos),
    )

    assert corrida.estado == "aprobado"
    assert corrida.lecciones == [ERROR_401["titulo"]]
    for etapa, mensaje in vistos:
        assert coding.AVISO_BOVEDA in mensaje, etapa
        assert "token de acceso de WhatsApp había vencido" in mensaje
    assert [e for e, _ in vistos] == ["spec", "builder", "revisor"]
    assert corrida.tokens == 45


def test_rechazo_con_error_nuevo_guarda_la_leccion(tmp_path, monkeypatch):
    servidor, coding = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(coding.experiencia.vectores, "asociar", lambda *a, **k: [])
    nueva = {
        "clase": "error",
        "titulo": "Migración sin respaldo",
        "resumen": "El diff borraba una columna sin respaldo previo.",
        "donde": "remi/nucleo/db.py",
        "secciones": {
            "Síntoma": "El diff hace DROP COLUMN directo.",
            "Lo que creímos": "Que la columna no se usaba.",
            "Causa real": "La columna la lee el panel.",
            "Cura": "Respaldar y migrar en dos pasos.",
            "Cómo verlo antes": "Buscar la columna en apps/ antes de borrarla.",
        },
    }

    corrida = coding.correr(
        coding.Corrida(id="2", tarea="quitar la columna vieja"),
        _llamador({"veredicto": "rechazado", "motivo": "borra datos", "leccion": nueva}, []),
    )

    assert corrida.estado == "rechazado"
    assert corrida.leccion_guardada is not None
    guardadas = coding.experiencia.listar(tema="coding")
    assert [l.titulo for l in guardadas] == ["Migración sin respaldo"]


def test_leccion_incompleta_no_se_guarda(tmp_path, monkeypatch):
    _servidor, coding = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(coding.experiencia.vectores, "asociar", lambda *a, **k: [])
    corrida = coding.correr(
        coding.Corrida(id="3", tarea="algo"),
        _llamador({"veredicto": "rechazado", "motivo": "x", "leccion": {"clase": "error", "titulo": "t"}}, []),
    )
    assert corrida.estado == "rechazado"
    assert corrida.leccion_guardada is None


def test_limite_de_max_para_sin_caer_a_otro_motor(tmp_path, monkeypatch):
    _servidor, coding = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(coding.experiencia.vectores, "asociar", lambda *a, **k: [])

    def sin_cupo(etapa, mensaje):
        raise coding.LimiteDeMax(etapa)

    corrida = coding.correr(coding.Corrida(id="4", tarea="algo"), sin_cupo)
    assert corrida.estado == "fallo"
    assert "límite" in (corrida.motivo or "")


def test_el_comando_no_lleva_clave_ni_escritura(tmp_path, monkeypatch):
    _servidor, coding = _arrancar(tmp_path, monkeypatch)
    comando = coding._comando(coding.MANOS["builder"])
    assert comando[:2] == ["claude", "-p"]
    herramientas = comando[comando.index("--tools") + 1]
    assert set(herramientas.split(",")) == {"Read", "Grep", "Glob"}
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert "ANTHROPIC_API_KEY" not in coding.pensar._entorno()


def test_api_estado_y_ultimas_de_coding(tmp_path, monkeypatch):
    servidor, _coding = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    cliente.post("/experiencia", json=ERROR_401)
    cliente.post("/experiencia", json={**ERROR_401, "tema": "malik", "titulo": "Otra cosa"})

    estado = cliente.get("/coding/estado").json()
    assert estado == {"motor": "claude-max", "lecciones_en_boveda": 2, "lecciones_de_coding": 1, "corrida_en_curso": None}
    ultimas = cliente.get("/coding/lecciones").json()
    assert [l["titulo"] for l in ultimas] == [ERROR_401["titulo"]]

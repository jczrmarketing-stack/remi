"""Coding en la charla: siempre Claude (Max), la bóveda delante, y la
lección nueva sale de la respuesta y entra a la bóveda. Sin llamadas
reales: el motor se reemplaza."""
import importlib
import json
import sys


def _pensar(tmp_path, monkeypatch, llamados, respuesta="Listo, el fix va en db.py."):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    monkeypatch.delenv("REMI_CODING_RESPALDO", raising=False)
    for nombre in ("pensar", "coding", "db", "experiencia", "episodios", "libros", "vectores"):
        sys.modules.pop(nombre, None)
    import db
    import pensar

    importlib.reload(db)
    import coding

    monkeypatch.setattr(coding.experiencia.vectores, "asociar", lambda *a, **k: [])
    monkeypatch.setattr(pensar, "_asociados", lambda frase: [])
    monkeypatch.setattr(pensar, "_actualizar_resumen_en_segundo_plano", lambda *a: None)
    monkeypatch.setattr(pensar, "_cerrar_conversaciones_inactivas_en_segundo_plano", lambda: None)

    def motor_falso(elegido, mensaje, *a, **k):
        llamados.append((elegido, mensaje))
        if isinstance(respuesta, Exception):
            raise respuesta
        return pensar.Pensado(respuesta, 1, 1, "sonnet", motor_usado=elegido)

    monkeypatch.setattr(pensar, "_respuesta_entera_del_motor", motor_falso)
    return pensar, coding


def test_detecta_tareas_de_codigo_y_deja_la_charla_suelta(tmp_path, monkeypatch):
    pensar, _ = _pensar(tmp_path, monkeypatch, [])
    assert pensar.es_de_coding("arregla el bug del endpoint /hoy")
    assert pensar.es_de_coding("revisa nucleo/db.py")
    assert not pensar.es_de_coding("¿qué hago hoy con la tarjeta?")


def test_codigo_va_por_claude_aunque_el_chip_diga_venice(tmp_path, monkeypatch):
    llamados = []
    pensar, _ = _pensar(tmp_path, monkeypatch, llamados)
    pensar.pensar("arregla el bug del endpoint /hoy", motor_pedido="venice")
    assert llamados[0][0] == "claude"


def test_charla_normal_respeta_el_chip(tmp_path, monkeypatch):
    llamados = []
    pensar, _ = _pensar(tmp_path, monkeypatch, llamados)
    pensar.pensar("¿qué hago hoy con la tarjeta?", motor_pedido="venice")
    assert llamados[0][0] == "venice"
    assert "LECCION_JSON" not in llamados[0][1]


def test_la_boveda_viaja_antes_de_llamar(tmp_path, monkeypatch):
    llamados = []
    pensar, coding = _pensar(tmp_path, monkeypatch, llamados)
    coding.experiencia.crear_leccion(
        coding.experiencia.LeccionNueva(
            titulo="El endpoint /hoy duplicaba tareas",
            tema="coding",
            resumen="Faltaba un DISTINCT.",
            clase="error",
            donde="remi/nucleo/servidor.py",
            secciones={
                "Síntoma": "El endpoint /hoy mostraba tareas dobles.",
                "Lo que creímos": "",
                "Causa real": "El JOIN con sesiones repetía filas.",
                "Cura": "DISTINCT en la consulta.",
                "Cómo verlo antes": "Contar filas contra tareas.",
            },
        )
    )
    pensar.pensar("arregla el bug del endpoint /hoy")
    mensaje = llamados[0][1]
    assert coding.AVISO_BOVEDA in mensaje
    assert "El JOIN con sesiones repetía filas" in mensaje


def test_la_leccion_nueva_se_guarda_y_no_se_dice(tmp_path, monkeypatch):
    leccion = {
        "clase": "acierto",
        "titulo": "Migrar en dos pasos",
        "resumen": "Respaldar y después borrar la columna.",
        "donde": "remi/nucleo/db.py",
        "secciones": {"Qué funcionó": "Dos migraciones.", "Evidencia": "Pruebas verdes.", "Cuándo usarlo": "Al borrar columnas."},
    }
    respuesta = f"Hazlo en dos migraciones.\nLECCION_JSON: {json.dumps(leccion, ensure_ascii=False)}"
    pensar, coding = _pensar(tmp_path, monkeypatch, [], respuesta)
    pensado = pensar.pensar("cómo borro la columna vieja en db.py")
    assert pensado is not None and pensado.paso_minimo == "Hazlo en dos migraciones."
    assert [l.titulo for l in coding.experiencia.listar(tema="coding")] == ["Migrar en dos pasos"]


def test_limite_de_max_en_codigo_no_cae_a_openrouter(tmp_path, monkeypatch):
    pensar, _ = _pensar(tmp_path, monkeypatch, [], respuesta=None)
    monkeypatch.setattr(pensar, "_respuesta_entera_del_motor", lambda *a, **k: (_ for _ in ()).throw(pensar.LimiteDeClaude("x")))
    respaldos = []
    monkeypatch.setattr(pensar, "_respaldo_de_charla", lambda *a: respaldos.append(a))
    assert pensar.pensar("arregla el bug del endpoint /hoy") is None
    assert respaldos == []


def test_respaldo_explicito_si_se_pide(tmp_path, monkeypatch):
    pensar, _ = _pensar(tmp_path, monkeypatch, [], respuesta=None)
    monkeypatch.setenv("REMI_CODING_RESPALDO", "openrouter")
    monkeypatch.setattr(pensar, "_respuesta_entera_del_motor", lambda *a, **k: (_ for _ in ()).throw(pensar.LimiteDeClaude("x")))
    monkeypatch.setattr(pensar, "_respaldo_de_charla", lambda *a: pensar.Pensado("ok", 1, 1, "deepseek", motor_usado="openrouter"))
    pensado = pensar.pensar("arregla el bug del endpoint /hoy")
    assert pensado is not None and pensado.motor_usado == "openrouter"

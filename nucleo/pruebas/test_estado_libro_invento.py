"""Verificación mecánica: una entidad que Haiku/Ollama inventa se rechaza.

Incidente real del 30-sep (docs/BITACORA.md): la consolidación nocturna pisó
dos veces el Estado de organic-cash.md con contenido inventado («N8N», «WAL»,
«Opción B») aunque SÍ había evidencia real (dos episodios) — la guarda
`sin_evidencia_nueva` no cubre esto, porque la evidencia no estaba vacía. La
instrucción anti-invento en el prompt no bastó: hacía falta una verificación
mecánica después de la respuesta, no solo antes de llamar al modelo.
"""
import estado_libro
import pensar


def test_entidades_sospechosas_encuentra_siglas_numeros_y_archivos():
    texto = "Se tocó webhook.py, con 42 reintentos, como N8N y con WAL activado."
    entidades = estado_libro.entidades_sospechosas(texto)
    assert "N8N" in entidades
    assert "WAL" in entidades
    assert "42" in entidades
    assert "webhook.py" in entidades


def test_entidades_sospechosas_ignora_numeros_de_una_cifra():
    assert estado_libro.entidades_sospechosas("el punto 3 y el 5") == []


def test_invento_detecta_una_sigla_que_no_esta_en_la_fuente():
    fuente = "Proyecto: X\n\nCommits nuevos:\n- arreglé el executor"
    texto = "Quedaste: arreglé el executor, como N8N.\nDecisiones: ninguna.\nPróximo paso: seguir."
    assert estado_libro._invento(texto, fuente) == "N8N"


def test_invento_no_marca_nada_si_todo_esta_en_la_fuente():
    fuente = "Proyecto: X\n\nCommits nuevos:\n- se tocó webhook.py con 42 reintentos"
    texto = "Quedaste: se tocó webhook.py con 42 reintentos.\nDecisiones: ninguna.\nPróximo paso: seguir."
    assert estado_libro._invento(texto, fuente) is None


def _datos(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}], "usage": {}}


def _sin_motores_reales(monkeypatch, tmp_path) -> None:
    """La trastienda cae a la cadena por defecto (groq → openrouter →
    ollama), sin depender del `config/motores.json` real del repo."""
    monkeypatch.setattr(pensar, "RUTA_MOTORES", tmp_path / "no-existe.json")


def test_redactar_rechaza_la_respuesta_de_groq_si_inventa_una_sigla(monkeypatch, tmp_path):
    _sin_motores_reales(monkeypatch, tmp_path)
    pedido = "Proyecto: X\n\nCommits nuevos:\n- arreglé el executor"
    llamados: list[str] = []

    def falsa_llamada(proveedor, modelo, instrucciones, frase):
        llamados.append(proveedor)
        if proveedor == "groq":
            return _datos("Quedaste: arreglé el executor, como N8N.\nDecisiones: ninguna.\nPróximo paso: seguir mañana.")
        return _datos("Quedaste: arreglé el executor.\nDecisiones: ninguna.\nPróximo paso: seguir.")

    monkeypatch.setattr(pensar, "_llamar_proveedor", falsa_llamada)

    resultado = estado_libro.redactar(pedido)
    # Cae al siguiente motor de la trastienda después de rechazar a groq por invento:
    assert resultado == "Quedaste: arreglé el executor.\nDecisiones: ninguna.\nPróximo paso: seguir."
    assert llamados == ["groq", "openrouter"]


def test_redactar_rechaza_todas_las_respuestas_si_todas_inventan(monkeypatch, tmp_path):
    _sin_motores_reales(monkeypatch, tmp_path)
    pedido = "Proyecto: X\n\nCommits nuevos:\n- arreglé el executor"

    monkeypatch.setattr(
        pensar,
        "_llamar_proveedor",
        lambda *a, **k: _datos("Quedaste: arreglé el executor, como N8N.\nDecisiones: ninguna.\nPróximo paso: seguir."),
    )

    assert estado_libro.redactar(pedido) is None


def test_redactar_acepta_una_respuesta_literal(monkeypatch, tmp_path):
    _sin_motores_reales(monkeypatch, tmp_path)
    pedido = "Proyecto: X\n\nCommits nuevos:\n- se tocó webhook.py"

    monkeypatch.setattr(
        pensar,
        "_llamar_proveedor",
        lambda *a, **k: _datos("Quedaste: se tocó webhook.py.\nDecisiones: ninguna.\nPróximo paso: seguir mañana."),
    )
    assert estado_libro.redactar(pedido) == "Quedaste: se tocó webhook.py.\nDecisiones: ninguna.\nPróximo paso: seguir mañana."



# — 3-oct: «Próximo paso: ejecutar pytest 802 y 804» —

def test_un_paso_de_verificacion_interna_no_es_un_proximo_paso():
    assert estado_libro.es_paso_interno("Próximo paso: ejecutar pytest 807, mypy limpio, para verificar la corrección.")
    assert estado_libro.es_paso_interno("Próximo paso: correr las pruebas.")
    assert not estado_libro.es_paso_interno("Próximo paso: probar el pegado con ⌘V en la ventanita, cinco minutos.")
    assert not estado_libro.es_paso_interno("Próximo paso: decidir si la ventanita flota encima.")


def test_redactar_rechaza_un_proximo_paso_de_pytest(monkeypatch, tmp_path):
    _sin_motores_reales(monkeypatch, tmp_path)
    pedido = "Proyecto: X\n\nCommits nuevos:\n- arreglé el executor"

    def falsa_llamada(proveedor, modelo, instrucciones, frase):
        if proveedor == "groq":
            return _datos("Quedaste: arreglé el executor.\nDecisiones: ninguna.\nPróximo paso: correr pytest.")
        return _datos("Quedaste: arreglé el executor.\nDecisiones: ninguna.\nPróximo paso: probarlo en la app.")

    monkeypatch.setattr(pensar, "_llamar_proveedor", falsa_llamada)
    assert estado_libro.redactar(pedido).endswith("Próximo paso: probarlo en la app.")


def test_el_pedido_no_lleva_las_cifras_de_verificacion():
    texto = estado_libro.pedido("X", "", [{"mensaje": "Arreglo el pegado. pytest 807, mypy limpio."}])
    assert "pytest" not in texto and "mypy" not in texto and "Arreglo el pegado." in texto

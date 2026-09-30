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


def _pensado(texto: str) -> pensar.Pensado:
    return pensar.Pensado(paso_minimo=texto, tokens_entrada=1, tokens_salida=1, modelo="x")


def test_redactar_rechaza_la_respuesta_de_haiku_si_inventa_una_sigla(monkeypatch):
    pedido = "Proyecto: X\n\nCommits nuevos:\n- arreglé el executor"

    def falsa_llamada(*args, **kwargs):
        return _pensado(
            "Quedaste: arreglé el executor, como N8N.\nDecisiones: ninguna.\nPróximo paso: seguir mañana."
        )

    llamado_ollama = []
    monkeypatch.setattr(pensar, "_una_llamada_claude", falsa_llamada)
    monkeypatch.setattr(pensar, "_llamar_ollama", lambda *a, **k: llamado_ollama.append(1) or {})
    monkeypatch.setattr(
        pensar,
        "_leer_respuesta_venice",
        lambda *a, **k: _pensado("Quedaste: arreglé el executor.\nDecisiones: ninguna.\nPróximo paso: seguir."),
    )

    resultado = estado_libro.redactar(pedido)
    # Cae a Ollama después de rechazar a Haiku, y esa respuesta sí es literal:
    assert resultado == "Quedaste: arreglé el executor.\nDecisiones: ninguna.\nPróximo paso: seguir."
    assert llamado_ollama  # de verdad cayó a Ollama, no se conformó con lo de Haiku


def test_redactar_rechaza_las_dos_respuestas_si_las_dos_inventan(monkeypatch):
    pedido = "Proyecto: X\n\nCommits nuevos:\n- arreglé el executor"
    inventada = _pensado("Quedaste: arreglé el executor, como N8N.\nDecisiones: ninguna.\nPróximo paso: seguir.")

    monkeypatch.setattr(pensar, "_una_llamada_claude", lambda *a, **k: inventada)
    monkeypatch.setattr(pensar, "_llamar_ollama", lambda *a, **k: {})
    monkeypatch.setattr(pensar, "_leer_respuesta_venice", lambda *a, **k: inventada)

    assert estado_libro.redactar(pedido) is None


def test_redactar_acepta_una_respuesta_literal(monkeypatch):
    pedido = "Proyecto: X\n\nCommits nuevos:\n- se tocó webhook.py"
    buena = _pensado("Quedaste: se tocó webhook.py.\nDecisiones: ninguna.\nPróximo paso: seguir mañana.")

    monkeypatch.setattr(pensar, "_una_llamada_claude", lambda *a, **k: buena)
    assert estado_libro.redactar(pedido) == "Quedaste: se tocó webhook.py.\nDecisiones: ninguna.\nPróximo paso: seguir mañana."

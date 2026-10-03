"""T9.5 (segunda vía): al abrir una conversación nueva, las que quedaron
atrás se revisan en segundo plano — nunca a mitad de un turno."""
import sys
from datetime import datetime, timedelta, timezone


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    # F3.5: sin esto, los libros eran los reales — cada corrida de la suite
    # reescribía el Estado de upvisuals.md y commiteaba en la bóveda real
    # (más de quince commits del 1 y 2 de octubre).
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("pensar", "db", "cierre", "experiencia", "libros"):
        sys.modules.pop(nombre, None)
    import cierre
    import pensar

    monkeypatch.setattr(pensar, "_pensar_con_claude", lambda *a, **k: None)
    # Ni la trastienda: una prueba no llama a un modelo.
    monkeypatch.setattr(cierre, "redactar", lambda pedido: None)
    return pensar


def test_abrir_la_primera_conversacion_dispara_la_revision_en_segundo_plano(tmp_path, monkeypatch):
    pensar = _arrancar(tmp_path, monkeypatch)
    llamadas = []
    monkeypatch.setattr(pensar, "_cerrar_conversaciones_inactivas_en_segundo_plano", lambda: llamadas.append(1))

    pensar.pensar("primera frase")

    assert llamadas == [1]


def test_seguir_la_misma_conversacion_no_dispara_nada(tmp_path, monkeypatch):
    pensar = _arrancar(tmp_path, monkeypatch)
    pensar.pensar("primera frase")  # abre la conversación

    llamadas = []
    monkeypatch.setattr(pensar, "_cerrar_conversaciones_inactivas_en_segundo_plano", lambda: llamadas.append(1))
    pensar.pensar("segunda frase, misma charla")

    assert llamadas == []


def test_al_empezar_de_cero_la_anterior_deja_su_episodio_al_abrir_la_siguiente(tmp_path, monkeypatch):
    import db

    pensar = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    hace_90_min = datetime.now(timezone.utc) - timedelta(minutes=90)
    texto_sustancial = "Hablamos del precio de la Fase 1 de UpVisuals. " * 40
    conversacion_id = db.guardar_turno(conexion, "juan", texto_sustancial, hace_90_min)
    db.guardar_turno(conexion, "remi", "Entendido.", hace_90_min + timedelta(seconds=5))
    # Desde el 3-oct no se corta por tiempo: termina cuando Juan Camilo
    # empieza de cero.
    db.cerrar_conversacion_vigente(conexion, datetime.now(timezone.utc))
    conexion.close()

    # Sin hilo real: que corra ahora mismo, en este test.
    class HiloFalso:
        def __init__(self, target, daemon=False):
            self._objetivo = target

        def start(self) -> None:
            self._objetivo()

    monkeypatch.setattr("threading.Thread", HiloFalso)
    pensar.pensar("una frase nueva, otra conversación")

    conexion = db.conectar()
    fila = conexion.execute(
        "SELECT episodio_hecho FROM conversaciones WHERE id = ?", (conversacion_id,)
    ).fetchone()
    conexion.close()
    assert fila["episodio_hecho"] == 1

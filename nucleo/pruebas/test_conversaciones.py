"""T7: el historial de la ventanita — una sola corriente de conversaciones."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import db
import servidor


def _turnos(*pares, desde=None):
    conexion = db.conectar()
    try:
        ahora = desde or datetime.now(timezone.utc)
        ids = []
        for i, (rol, texto) in enumerate(pares):
            ids.append(db.guardar_turno(conexion, rol, texto, ahora + timedelta(seconds=i)))
        return ids[-1]
    finally:
        conexion.close()


def test_el_titulo_es_el_primer_mensaje_cortado_en_una_palabra():
    largo = "necesito armar el formulario de contacto para la página de UpVisuals hoy mismo"
    titulo = db.titulo_de(largo)
    assert titulo.endswith("…") and len(titulo) <= db.LARGO_MAXIMO_DE_TITULO + 1
    assert db.titulo_de("  hola   remi ") == "hola remi"


def test_la_lista_trae_la_mas_reciente_primero_con_su_titulo():
    viejo = datetime.now(timezone.utc) - timedelta(hours=5)
    _turnos(("juan", "primero de ayer"), ("remi", "dale"), desde=viejo)
    _turnos(("juan", "lo de ahora"), ("remi", "listo"))
    lista = TestClient(servidor.app).get("/conversaciones").json()
    assert [c["titulo"] for c in lista] == ["lo de ahora", "primero de ayer"]
    assert lista[0]["turnos"] == 2


def test_retomar_una_de_antes_la_vuelve_vigente():
    viejo = datetime.now(timezone.utc) - timedelta(hours=5)
    antigua = _turnos(("juan", "la de antes"), ("remi", "ok"), desde=viejo)
    cliente = TestClient(servidor.app)
    assert cliente.get("/conversacion").json() == []
    turnos = cliente.post(f"/conversaciones/{antigua}/retomar").json()
    assert [t["texto"] for t in turnos] == ["la de antes", "ok"]
    assert [t["texto"] for t in cliente.get("/conversacion").json()] == ["la de antes", "ok"]
    _turnos(("juan", "sigo"))
    assert len(cliente.get(f"/conversaciones/{antigua}").json()) == 3


def test_empezar_de_cero_cierra_la_vigente_y_el_siguiente_turno_abre_otra():
    primera = _turnos(("juan", "uno"), ("remi", "dos"))
    cliente = TestClient(servidor.app)
    assert cliente.post("/conversaciones/nueva").status_code == 204
    assert cliente.get("/conversacion").json() == []
    segunda = _turnos(("juan", "otra cosa"))
    assert segunda != primera
    assert len(cliente.get("/conversaciones").json()) == 2


def test_una_conversacion_que_no_existe_da_404():
    cliente = TestClient(servidor.app)
    assert cliente.get("/conversaciones/nada").status_code == 404
    assert cliente.post("/conversaciones/nada/retomar").status_code == 404


def test_el_titulo_queda_en_la_base_desde_el_primer_turno(tmp_path):
    # T11.3 (cierre de T7): no depende de leer «titulo» de la fila — así se
    # ve que de verdad se escribió en el INSERT, no solo en el fallback de
    # /conversaciones.
    conversacion_id = _turnos(("juan", "necesito armar el formulario de contacto para UpVisuals"))
    conexion = db.conectar()
    try:
        fila = conexion.execute(
            "SELECT titulo FROM conversaciones WHERE id = ?", (conversacion_id,)
        ).fetchone()
    finally:
        conexion.close()
    assert fila["titulo"] == db.titulo_de("necesito armar el formulario de contacto para UpVisuals")

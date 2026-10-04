"""B3.1/B3.2/B3.3: un encargo con `hito: <tema>#<n>` cierra ese hito solo
con commit Y pruebas en verde durante la sesión; con evidencia dudosa deja
una Pregunta, nunca un cierre a ciegas. «Listo cuando» del plan final."""
import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

LIBRO_UPVISUALS = """---
titulo: UpVisuals
tema: upvisuals
cliente: UpVisuals
tipo: cliente
resumen: El dashboard.
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [x] Propuesta por fases
- [x] Contrato
- [ ] Entregas medidas
"""

LIBRO_BEAM = """---
titulo: BeaM
tema: beam
cliente: BeaM
tipo: cliente
resumen: El bot.
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [x] Propuesta por fases
- [ ] Contrato
"""


def _libros(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO_UPVISUALS)
    (carpeta / "beam.md").write_text(LIBRO_BEAM)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("trabajo", "caminos", "libros", "db", "avisos"):
        sys.modules.pop(nombre, None)
    import db

    importlib.reload(db)
    import trabajo

    return trabajo


def _abrir_sesion(conexion, session_id: str, tema: str, inicio: datetime) -> None:
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES (?, ?, '', ?, NULL)",
        (session_id, tema, inicio.isoformat()),
    )
    conexion.commit()


def _evento(conexion, tipo: str, tema: str, fecha: datetime, datos: dict | None = None) -> None:
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, '', ?, ?, ?)",
        (str(uuid4()), tipo, tema, json.dumps(datos or {}), fecha.isoformat()),
    )
    conexion.commit()


def test_commit_y_pruebas_en_verde_cierran_el_hito_5(tmp_path, monkeypatch):
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import db

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})
    _evento(conexion, "pruebas", "upvisuals", inicio + timedelta(minutes=20), {"verde": True})

    trabajo.recibir("sesion_fin", "", {"session_id": "s1", "hito": "upvisuals#5"}, fin)

    hitos = __import__("caminos").leer_hitos(next(l for l in __import__("libros").listar() if l.tema == "upvisuals").archivo)
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()

    assert hitos[4].hecho is True
    assert cerrado is not None and cerrado.tipo == "encargo" and cerrado.ref == "s1"


def test_commit_sin_pruebas_verde_deja_una_pregunta_no_cierra(tmp_path, monkeypatch):
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import db
    import libros

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})

    trabajo.recibir("sesion_fin", "", {"session_id": "s1", "hito": "upvisuals#5"}, fin)

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    hitos = __import__("caminos").leer_hitos(libro.archivo)
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    pregunta = db.pregunta_de_tema_campo(conexion, "upvisuals", "hito.5.cierre")
    conexion.close()

    assert hitos[4].hecho is False
    assert cerrado is None
    assert pregunta is not None
    assert pregunta.estado == "pendiente"


def test_sin_header_de_hito_no_hace_nada(tmp_path, monkeypatch):
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import db
    import libros

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})
    _evento(conexion, "pruebas", "upvisuals", inicio + timedelta(minutes=20), {"verde": True})

    trabajo.recibir("sesion_fin", "", {"session_id": "s1"}, fin)

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    hitos = __import__("caminos").leer_hitos(libro.archivo)
    conexion.close()

    assert hitos[4].hecho is False


def test_hito_de_un_tema_no_cierra_el_de_otro(tmp_path, monkeypatch):
    """El header trae tema#n: upvisuals#5 nunca toca el camino de beam."""
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import db
    import libros

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})
    _evento(conexion, "pruebas", "upvisuals", inicio + timedelta(minutes=20), {"verde": True})

    trabajo.recibir("sesion_fin", "", {"session_id": "s1", "hito": "upvisuals#5"}, fin)

    beam = next(l for l in libros.listar() if l.tema == "beam")
    hitos_beam = __import__("caminos").leer_hitos(beam.archivo)
    conexion.close()

    assert all(h.hecho for h in hitos_beam[:3]) and hitos_beam[3].hecho is False


def test_hito_ya_hecho_no_se_reabre_ni_rehace_nada(tmp_path, monkeypatch):
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import db

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})
    _evento(conexion, "pruebas", "upvisuals", inicio + timedelta(minutes=20), {"verde": True})

    # Hito 1 (Intake) ya está hecho en el libro de fixture.
    trabajo.recibir("sesion_fin", "", {"session_id": "s1", "hito": "upvisuals#1"}, fin)

    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 1)
    conexion.close()

    assert cerrado is None


def test_deshacer_devuelve_el_hito(tmp_path, monkeypatch):
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import caminos
    import db
    import libros

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})
    _evento(conexion, "pruebas", "upvisuals", inicio + timedelta(minutes=20), {"verde": True})
    trabajo.recibir("sesion_fin", "", {"session_id": "s1", "hito": "upvisuals#5"}, fin)

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    caminos.marcar_por_indice(libro.archivo, 4, False)
    db.deshacer_hito_cerrado(conexion, "upvisuals", 5)

    hitos = caminos.leer_hitos(libro.archivo)
    cerrado = db.hito_cerrado_de(conexion, "upvisuals", 5)
    conexion.close()

    assert hitos[4].hecho is False
    assert cerrado is None


def test_cerrar_una_sesion_de_encargo_deja_el_aviso_terminal_termino(tmp_path, monkeypatch):
    """B5: terminal_termino nace del evento (sesión con header), no de
    mirar el reloj."""
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import avisos
    import db

    inicio = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)  # 10am Bogotá
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)
    _evento(conexion, "commit", "upvisuals", inicio + timedelta(minutes=10), {"mensaje": "x"})

    trabajo.recibir("sesion_fin", "", {"session_id": "s1", "hito": "upvisuals#5"}, fin)

    avisados = avisos.listar_de_hoy(conexion, fin)
    conexion.close()
    assert [a.tipo for a in avisados] == ["terminal_termino"]


def test_cerrar_una_sesion_sin_header_no_deja_aviso(tmp_path, monkeypatch):
    _libros(tmp_path)
    trabajo = _arrancar(tmp_path, monkeypatch)
    import avisos
    import db

    inicio = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=30)
    conexion = db.conectar()
    _abrir_sesion(conexion, "s1", "upvisuals", inicio)

    trabajo.recibir("sesion_fin", "", {"session_id": "s1"}, fin)

    avisados = avisos.listar_de_hoy(conexion, fin)
    conexion.close()
    assert avisados == []

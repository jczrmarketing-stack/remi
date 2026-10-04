"""B2: Al día (forma J, PLAN-FINAL.md). Línea de tiempo sintética: commit,
pruebas en verde, cierre de sesión, cobro, decisión — contra un libro de
fixture, nunca el remi.db ni la bóveda real."""
import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

LIBRO = """---
titulo: UpVisuals
tema: upvisuals
cliente: UpVisuals
tipo: cliente
resumen: El dashboard.
---

## Camino

- [x] Intake
- [ ] Descubrimiento (5 preguntas)
- [ ] Cobro y cierre
"""


def _libro(tmp_path, cuerpo: str = LIBRO) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(cuerpo)


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    for nombre in ("aldia", "caminos", "libros", "db", "entregas", "modelos"):
        sys.modules.pop(nombre, None)
    import db

    importlib.reload(db)
    import aldia

    return aldia


def _evento(conexion, tipo: str, tema: str | None, fecha: datetime, datos: dict | None = None) -> None:
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, ?, '', ?, ?, ?)",
        (str(uuid4()), tipo, tema, json.dumps(datos or {}), fecha.isoformat()),
    )
    conexion.commit()


def _cobro(conexion, cliente: str, proyecto_id, fecha: datetime, monto: float) -> None:
    conexion.execute(
        "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
        "VALUES (?, ?, ?, ?, ?, 'pagada', 1)",
        (str(uuid4()), cliente, str(proyecto_id), fecha.isoformat(), monto),
    )
    conexion.commit()


def test_lo_ultimo_despues_de_un_commit_y_pruebas_en_verde(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    _evento(conexion, "commit", "upvisuals", ahora - timedelta(minutes=10), {"mensaje": "arreglar el login"})
    _evento(conexion, "pruebas", "upvisuals", ahora - timedelta(minutes=2), {"verde": True})
    anterior = aldia.marcar_visto(conexion, ahora - timedelta(minutes=30))

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.lo_ultimo is not None
    assert forma.lo_ultimo.evidencia.tipo == "pruebas"
    assert forma.lo_ultimo.hace_min == 2


def test_estamos_en_y_sigue_con_el_libro_activo(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    _evento(conexion, "commit", "upvisuals", ahora - timedelta(minutes=5), {"mensaje": "x"})
    anterior = aldia.marcar_visto(conexion, ahora)

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.estamos_en is not None
    assert forma.estamos_en.tema == "upvisuals"
    assert forma.estamos_en.paso == "Descubrimiento (5 preguntas)"
    assert forma.sigue is not None
    assert forma.sigue.texto == "Descubrimiento (5 preguntas)"
    assert forma.sigue.borrador is None  # este hito no avisa a un cliente


def test_sigue_trae_borrador_en_un_hito_de_aviso(tmp_path, monkeypatch):
    libro_en_cobro = LIBRO.replace(
        "- [x] Intake\n- [ ] Descubrimiento (5 preguntas)\n- [ ] Cobro y cierre",
        "- [x] Intake\n- [x] Descubrimiento (5 preguntas)\n- [ ] Cobro y cierre",
    )
    _libro(tmp_path, libro_en_cobro)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    _evento(conexion, "commit", "upvisuals", ahora - timedelta(minutes=5), {"mensaje": "x"})
    aldia.guardar_borrador(conexion, "upvisuals", "Cobro y cierre", "Te mando la factura de esta fase.")
    anterior = aldia.marcar_visto(conexion, ahora)

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.sigue.texto == "Cobro y cierre"
    assert forma.sigue.borrador == "Te mando la factura de esta fase."


def test_mientras_no_estabas_trae_cobro_y_decision(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db
    import entregas
    import memoria_mcp

    # memoria_mcp.guardar siempre fecha con datetime.now(): `ahora` tiene
    # que ser el reloj real para que la decisión caiga dentro de la
    # ventana, no una fecha sintética de otro año.
    hace_3h = datetime.now(timezone.utc) - timedelta(hours=3)
    conexion = db.conectar()
    _evento(conexion, "sesion_fin", "upvisuals", hace_3h + timedelta(minutes=5), {"session_id": "s1"})
    _cobro(conexion, "UpVisuals", entregas._proyecto_id_de_tema("upvisuals"), hace_3h + timedelta(minutes=10), 500)
    conexion.close()
    memoria_mcp.guardar("Fase 2 en noviembre", "Se deja para noviembre", "detalle", "upvisuals", tipo="decision")
    # memoria_mcp.guardar fecha con su propio datetime.now(): `ahora` tiene
    # que quedar después de eso, nunca capturado antes.
    ahora = datetime.now(timezone.utc) + timedelta(seconds=5)

    conexion = db.conectar()
    anterior = aldia.marcar_visto(conexion, hace_3h)
    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    tipos = {e.evidencia.tipo for e in forma.mientras_no_estabas}
    assert {"sesion", "cobro", "decision"} <= tipos
    assert len(forma.mientras_no_estabas) <= 5


def test_mientras_no_estabas_vacio_si_fue_hace_menos_de_dos_horas(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    _evento(conexion, "commit", "upvisuals", ahora - timedelta(minutes=50), {"mensaje": "x"})
    anterior = aldia.marcar_visto(conexion, ahora - timedelta(hours=1))

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.mientras_no_estabas == []


def test_sin_eventos_todo_queda_vacio_sin_romper(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    anterior = aldia.marcar_visto(conexion, ahora)
    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.estamos_en is None
    assert forma.lo_ultimo is None
    assert forma.sigue is None
    assert forma.mientras_no_estabas == []


def test_marcar_visto_la_primera_vez_devuelve_ahora(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    anterior = aldia.marcar_visto(conexion, ahora)
    conexion.close()

    assert anterior == ahora


def test_sesion_abierta_gana_como_lo_ultimo_y_pone_el_estamos_en(tmp_path, monkeypatch):
    """B2.2: «terminal trabajando» — una sesión de Claude Code abierta
    cuenta aunque todavía no haya ni un commit."""
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES ('s1', 'upvisuals', '', ?, NULL)",
        ((ahora - timedelta(minutes=12)).isoformat(),),
    )
    conexion.commit()
    anterior = aldia.marcar_visto(conexion, ahora)

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.lo_ultimo.texto == "La terminal está en esto desde hace 12 min."
    assert forma.lo_ultimo.evidencia == aldia.Evidencia("sesion", "s1")
    assert forma.estamos_en.tema == "upvisuals"
    assert forma.estamos_en.paso == "Descubrimiento (5 preguntas)"


def test_un_commit_durante_la_sesion_gana_sobre_terminal_trabajando(tmp_path, monkeypatch):
    """Hallazgo de la revisión de B2: si ya hubo un commit con pruebas en
    verde DESPUÉS de que la sesión abrió, eso es más fresco que «sigo en
    esto desde que empecé» — nunca se tapa un logro real con un «trabajando»
    genérico."""
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES ('s1', 'upvisuals', '', ?, NULL)",
        ((ahora - timedelta(minutes=20)).isoformat(),),
    )
    _evento(conexion, "commit", "upvisuals", ahora - timedelta(minutes=10), {"mensaje": "x"})
    _evento(conexion, "pruebas", "upvisuals", ahora - timedelta(minutes=2), {"verde": True})
    anterior = aldia.marcar_visto(conexion, ahora - timedelta(minutes=30))

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.lo_ultimo.evidencia.tipo == "pruebas"
    assert forma.lo_ultimo.hace_min == 2


def test_sesion_cerrada_no_cuenta_como_abierta(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    ahora = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES ('s1', 'upvisuals', '', ?, ?)",
        ((ahora - timedelta(minutes=30)).isoformat(), (ahora - timedelta(minutes=20)).isoformat()),
    )
    conexion.commit()
    anterior = aldia.marcar_visto(conexion, ahora)

    forma = aldia.calcular(conexion, ahora, anterior)
    conexion.close()

    assert forma.lo_ultimo is None
    assert forma.estamos_en is None


def test_marcar_visto_la_segunda_vez_devuelve_la_anterior(tmp_path, monkeypatch):
    _libro(tmp_path)
    aldia = _arrancar(tmp_path, monkeypatch)
    import db

    t1 = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    aldia.marcar_visto(conexion, t1)
    anterior = aldia.marcar_visto(conexion, t2)
    conexion.close()

    assert anterior == t1

"""B6.3/B6.4: lo_que_paso, lo_acordado y atento_a — sin IA."""
import json
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

LIBRO = """---
titulo: UpVisuals
tema: upvisuals
cliente: Alfonso
tipo: cliente
resumen: El dashboard.
fases:
  - nombre: Fase 1
    alcance: a
    monto: 5000
    listo_cuando: Demo
    estado: pagando
    minutos_estimados: 60
  - nombre: Fase 2
    alcance: b
    monto: 3000
    listo_cuando: Otra demo
    estado: propuesta
---

## Camino

- [x] Intake
- [ ] Descubrimiento (5 preguntas)
"""


def _arrancar(tmp_path, monkeypatch):
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(LIBRO)
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(carpeta))
    for nombre in ("db", "ficha", "aldia", "caminos", "libros", "entregas", "trabajo"):
        sys.modules.pop(nombre, None)
    import db

    import ficha

    return ficha, db


def test_lo_que_paso_trae_eventos_de_ese_tema_mas_nuevo_primero(tmp_path, monkeypatch):
    ficha, db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'commit', '', 'upvisuals', ?, ?)",
        (str(uuid4()), json.dumps({"mensaje": "algo"}), (ahora - timedelta(minutes=30)).isoformat()),
    )
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'pruebas', '', 'upvisuals', ?, ?)",
        (str(uuid4()), json.dumps({"verde": True}), (ahora - timedelta(minutes=5)).isoformat()),
    )
    conexion.commit()
    lineas = ficha.lo_que_paso(conexion, "upvisuals", ahora)
    conexion.close()
    assert lineas[0].origen == "pruebas"
    assert lineas[1].origen == "commit"


def test_lo_que_paso_corta_en_seis_y_no_mezcla_otro_tema(tmp_path, monkeypatch):
    ficha, db = _arrancar(tmp_path, monkeypatch)
    conexion = db.conectar()
    ahora = datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)
    for i in range(8):
        conexion.execute(
            "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'commit', '', 'upvisuals', ?, ?)",
            (str(uuid4()), json.dumps({"mensaje": f"c{i}"}), (ahora - timedelta(minutes=70 - i)).isoformat()),
        )
    conexion.execute(
        "INSERT INTO trabajo_eventos (id, tipo, ruta, tema, datos, fecha) VALUES (?, 'commit', '', 'beam', ?, ?)",
        (str(uuid4()), json.dumps({"mensaje": "de otro proyecto"}), (ahora - timedelta(minutes=1)).isoformat()),
    )
    conexion.commit()
    lineas = ficha.lo_que_paso(conexion, "upvisuals", ahora)
    conexion.close()
    assert len(lineas) == 6
    assert all("otro proyecto" not in l.texto for l in lineas)


def test_lo_acordado_trae_decisiones_y_entregas_futuras(tmp_path, monkeypatch):
    ficha, db = _arrancar(tmp_path, monkeypatch)
    import entregas
    import memoria_mcp

    memoria_mcp.guardar("Fase 2 en noviembre", "Se deja para noviembre", "detalle", "upvisuals", tipo="decision")
    conexion = db.conectar()
    ahora = datetime.now(timezone.utc)
    entregas.crear_entrega(
        conexion,
        __import__("modelos").Entrega(
            id=uuid4(), cliente="Alfonso", proyecto_id=entregas._proyecto_id_de_tema("upvisuals"),
            fecha=ahora + timedelta(days=5), monto=2000.0, estado="camino", compartible=True, linea=None,
        ),
    )
    acordado = ficha.lo_acordado(conexion, "upvisuals", ahora + timedelta(seconds=5))
    conexion.close()
    assert acordado.decisiones == ["Se deja para noviembre"]
    assert len(acordado.entregas_futuras) == 1
    assert "Alfonso: 2000" in acordado.entregas_futuras[0]


def test_atento_a_avisa_cuando_se_pasa_del_estimado(tmp_path, monkeypatch):
    ficha, db = _arrancar(tmp_path, monkeypatch)
    import libros

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    lineas = ficha.atento_a(libro, minutos_total=90)  # estimado: 60
    assert any("30 min más" in l for l in lineas)


def test_atento_a_dice_cuantos_hitos_quedan(tmp_path, monkeypatch):
    ficha, db = _arrancar(tmp_path, monkeypatch)
    import libros

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    lineas = ficha.atento_a(libro, minutos_total=10)
    assert any("1 paso" in l for l in lineas)


def test_atento_a_sin_pasarse_del_estimado_no_avisa_nada_de_horas(tmp_path, monkeypatch):
    ficha, db = _arrancar(tmp_path, monkeypatch)
    import libros

    libro = next(l for l in libros.listar() if l.tema == "upvisuals")
    lineas = ficha.atento_a(libro, minutos_total=30)
    assert not any("más de lo estimado" in l for l in lineas)

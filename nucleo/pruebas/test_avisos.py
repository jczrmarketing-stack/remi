"""B5: avisos que jalan la atención. El «listo cuando» del plan final,
con un reloj falso — nunca datetime.now()."""
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

BOGOTA_OFFSET = timedelta(hours=-5)  # America/Bogota, sin horario de verano


def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    sys.modules.pop("db", None)
    sys.modules.pop("avisos", None)
    import db

    db.inicializar_esquema()
    import avisos

    return avisos


def _conexion(avisos):
    import db

    return db.conectar()


def test_seis_avisos_el_mismo_dia_salen_cinco(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc)  # 8am Bogotá
    salieron = 0
    for i in range(6):
        aviso = avisos.registrar(conexion, "foco_25", f"aviso {i}", "ventanita", ahora + timedelta(minutes=50 * i))
        if aviso is not None:
            salieron += 1
    conexion.close()
    assert salieron == 5


def test_un_aviso_a_las_2330_no_sale(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    # 23:30 Bogotá = 04:30 UTC del día siguiente.
    ahora = datetime(2026, 10, 5, 4, 30, tzinfo=timezone.utc)
    aviso = avisos.registrar(conexion, "foco_25", "tarde", "ventanita", ahora)
    conexion.close()
    assert aviso is None


def test_dos_avisos_con_20_min_de_diferencia_sale_uno(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)  # 9am Bogotá
    primero = avisos.registrar(conexion, "foco_25", "uno", "ventanita", ahora)
    segundo = avisos.registrar(conexion, "foco_25", "dos", "ventanita", ahora + timedelta(minutes=20))
    conexion.close()
    assert primero is not None
    assert segundo is None


def test_ahora_no_al_desvio_lo_calla_el_resto_del_dia(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)  # 9am Bogotá
    aviso = avisos.registrar(conexion, "desvio", "te desviaste", "ventanita", ahora)
    assert aviso is not None
    avisos.responder(conexion, aviso.id, "ahora_no")

    mas_tarde = avisos.registrar(conexion, "desvio", "te desviaste otra vez", "ventanita", ahora + timedelta(hours=3))
    conexion.close()
    assert mas_tarde is None


def test_ahora_no_solo_calla_ese_tipo(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    aviso = avisos.registrar(conexion, "desvio", "te desviaste", "ventanita", ahora)
    avisos.responder(conexion, aviso.id, "ahora_no")

    # entre_min (45) sigue aplicando entre tipos distintos: se corre 1h.
    otro = avisos.registrar(conexion, "foco_25", "foco", "ventanita", ahora + timedelta(hours=1))
    conexion.close()
    assert otro is not None


def test_silenciado_ayer_no_sigue_silenciado_hoy(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ayer = datetime(2026, 10, 4, 14, 0, tzinfo=timezone.utc)
    aviso = avisos.registrar(conexion, "desvio", "ayer", "ventanita", ayer)
    avisos.responder(conexion, aviso.id, "ahora_no")

    hoy = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    nuevo = avisos.registrar(conexion, "desvio", "hoy", "ventanita", hoy)
    conexion.close()
    assert nuevo is not None


def test_un_tipo_fuera_de_suenan_nunca_sale(tmp_path, monkeypatch):
    ruta = tmp_path / "avisos.json"
    ruta.write_text('{"suenan": ["foco_25"], "max_dia": 5, "entre_min": 45, "noche": [23, 7], "telegram": true}')
    monkeypatch.setenv("REMI_AVISOS", str(ruta))
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    aviso = avisos.registrar(conexion, "desvio", "no debería salir", "ventanita", ahora)
    conexion.close()
    assert aviso is None


def test_listar_de_hoy_trae_solo_los_de_hoy(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ayer = datetime(2026, 10, 4, 14, 0, tzinfo=timezone.utc)
    hoy = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    avisos.registrar(conexion, "foco_25", "ayer", "ventanita", ayer)
    avisos.registrar(conexion, "foco_25", "hoy", "ventanita", hoy)
    lista = avisos.listar_de_hoy(conexion, hoy)
    conexion.close()
    assert [a.texto for a in lista] == ["hoy"]


def test_pendiente_es_el_ultimo_sin_respuesta(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    avisos.registrar(conexion, "foco_25", "primero", "ventanita", ahora)
    segundo = avisos.registrar(conexion, "desvio", "segundo", "ventanita", ahora + timedelta(minutes=50))
    pendiente = avisos.pendiente(conexion)
    conexion.close()
    assert pendiente is not None and pendiente.id == segundo.id


def test_regla_foco_25_con_bloque_de_25_min(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    import db

    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    tarea_id = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible) "
        "VALUES (?, 'x', NULL, 'hoy', 'paso', NULL, NULL, 0)",
        (tarea_id,),
    )
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, NULL, 0, 'upvisuals')",
        (str(uuid4()), tarea_id, (ahora - timedelta(minutes=26)).isoformat()),
    )
    conexion.commit()
    aviso = avisos.evaluar(conexion, ahora)
    conexion.close()
    assert aviso is not None and aviso.tipo == "foco_25"


def test_regla_desvio_con_sesion_claude_en_otro_tema(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    tarea_id = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible, fecha_limite) "
        "VALUES (?, 'x', NULL, 'hoy', 'paso', NULL, NULL, 0, ?)",
        (tarea_id, ahora.isoformat()),
    )
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, NULL, 0, 'upvisuals')",
        (str(uuid4()), tarea_id, (ahora - timedelta(minutes=5)).isoformat()),
    )
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES ('s1', 'beam', '', ?, NULL)",
        ((ahora - timedelta(minutes=35)).isoformat(),),
    )
    conexion.commit()
    aviso = avisos.evaluar(conexion, ahora)
    conexion.close()
    assert aviso is not None and aviso.tipo == "desvio"


def test_sin_bloque_abierto_evaluar_no_rompe(tmp_path, monkeypatch):
    avisos = _db(tmp_path, monkeypatch)
    conexion = _conexion(avisos)
    ahora = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    aviso = avisos.evaluar(conexion, ahora)
    conexion.close()
    assert aviso is None

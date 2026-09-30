"""El motor de iniciativa (Fase 3, tarea 2): reglas sin IA + presupuesto.

Todas las pruebas inyectan `ahora`: nada acá corre contra el reloj real.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import iniciativa

BOGOTA = iniciativa.BOGOTA


def _conexion(tmp_path):
    import db

    return db.conectar(tmp_path / "remi.db")


def _abrir_sesion(conexion, inicio: datetime, tema: str | None = "remi") -> None:
    tarea_id = str(uuid4())
    conexion.execute(
        "INSERT INTO tareas (id, titulo, proyecto_id, estado, paso_minimo, estimado_min, real_min, compartible) "
        "VALUES (?, 'x', NULL, 'hoy', 'paso', NULL, NULL, 0)",
        (tarea_id,),
    )
    conexion.execute(
        "INSERT INTO sesiones (id, tarea_id, inicio, fin, real_min, app_contexto) VALUES (?, ?, ?, NULL, 0, ?)",
        (str(uuid4()), tarea_id, inicio.isoformat(), tema),
    )
    conexion.commit()


def _entrega(conexion, fecha: datetime, tema: str, cliente: str = "Alfonso", estado: str = "camino") -> None:
    conexion.execute(
        "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
        "VALUES (?, ?, ?, ?, NULL, ?, 1)",
        (str(uuid4()), cliente, tema, fecha.isoformat(), estado),
    )
    conexion.commit()


def _idea(conexion, ahora: datetime, fria: bool) -> None:
    from modelos import Idea

    import db

    creada = ahora - timedelta(hours=1)
    enfria_hasta = ahora - timedelta(hours=1) if fria else ahora + timedelta(hours=1)
    db.crear_idea(
        conexion,
        Idea(id=uuid4(), texto="algo", origen="texto", creada_en=creada, enfria_hasta=enfria_hasta, estado="enfriando", problema_vision=None),
    )


# — Regla cuerpo —


def test_cuerpo_no_suena_antes_de_90_min(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=89))
    assert iniciativa.evaluar(conexion, ahora) is None


def test_cuerpo_suena_pasados_90_min(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=91), tema="malik")
    candidato = iniciativa.evaluar(conexion, ahora)
    assert candidato is not None
    assert candidato.tipo == "cuerpo"
    assert "malik" in candidato.voz
    assert "1 h 31" in candidato.voz


# — Regla ritual —


def test_ritual_no_suena_sin_ideas_frias(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _idea(conexion, ahora, fria=False)
    assert iniciativa.evaluar(conexion, ahora) is None


def test_ritual_suena_con_ideas_frias(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _idea(conexion, ahora, fria=True)
    _idea(conexion, ahora, fria=True)
    candidato = iniciativa.evaluar(conexion, ahora)
    assert candidato is not None
    assert candidato.tipo == "ritual"
    assert "2 ideas frías" in candidato.voz


def test_ritual_no_se_repite_el_mismo_dia(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _idea(conexion, ahora, fria=True)
    primero = iniciativa.evaluar(conexion, ahora)
    assert primero is not None
    iniciativa.registrar(conexion, uuid4(), "ritual", ahora)

    despues = ahora + timedelta(hours=1)
    assert iniciativa.evaluar(conexion, despues) is None


# — Regla encoger —


def test_encoger_no_suena_antes_de_las_22(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 21, 59, tzinfo=BOGOTA).astimezone(timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=5))
    assert iniciativa.evaluar(conexion, ahora) is None


def test_encoger_suena_de_noche_con_bloque_abierto(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 22, 30, tzinfo=BOGOTA).astimezone(timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=5))
    candidato = iniciativa.evaluar(conexion, ahora)
    assert candidato is not None
    assert candidato.tipo == "encoger"


def test_encoger_no_suena_sin_bloque_abierto(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 22, 30, tzinfo=BOGOTA).astimezone(timezone.utc)
    assert iniciativa.evaluar(conexion, ahora) is None


# — Regla rumbo —


def test_rumbo_suena_con_entrega_cerca_y_otro_tema_abierto(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=10), tema="remi")
    _entrega(conexion, ahora + timedelta(hours=10), tema="malik", cliente="Alfonso")
    candidato = iniciativa.evaluar(conexion, ahora)
    assert candidato is not None
    assert candidato.tipo == "rumbo"
    assert "Alfonso" in candidato.voz
    assert "remi" in candidato.voz


def test_rumbo_no_suena_si_es_el_mismo_tema(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=10), tema="malik")
    _entrega(conexion, ahora + timedelta(hours=10), tema="malik", cliente="Alfonso")
    assert iniciativa.evaluar(conexion, ahora) is None


def test_rumbo_no_suena_si_la_entrega_esta_a_mas_de_24_horas(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=10), tema="remi")
    _entrega(conexion, ahora + timedelta(hours=25), tema="malik", cliente="Alfonso")
    assert iniciativa.evaluar(conexion, ahora) is None


def test_rumbo_ignora_una_sesion_de_claude_code_abierta(tmp_path):
    """«Salvo rumbo»: es la única regla que interrumpe con Claude Code abierto."""
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=10), tema="remi")
    _entrega(conexion, ahora + timedelta(hours=10), tema="malik", cliente="Alfonso")
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES (?, 'remi', '/x', ?, NULL)",
        (str(uuid4()), ahora.isoformat()),
    )
    conexion.commit()
    candidato = iniciativa.evaluar(conexion, ahora)
    assert candidato is not None
    assert candidato.tipo == "rumbo"


def test_cuerpo_no_suena_con_claude_code_abierto(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _abrir_sesion(conexion, ahora - timedelta(minutes=91), tema="malik")
    conexion.execute(
        "INSERT INTO trabajo_claude (session_id, tema, ruta, inicio, fin) VALUES (?, 'malik', '/x', ?, NULL)",
        (str(uuid4()), ahora.isoformat()),
    )
    conexion.commit()
    assert iniciativa.evaluar(conexion, ahora) is None


# — El presupuesto de silencio —


def test_maximo_cinco_nudges_por_dia(tmp_path):
    conexion = _conexion(tmp_path)
    base = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)
    for i in range(5):
        iniciativa.registrar(conexion, uuid4(), "encoger", base + timedelta(hours=i))
    ahora = base + timedelta(hours=6)
    _abrir_sesion(conexion, ahora - timedelta(minutes=91), tema="malik")
    assert iniciativa.evaluar(conexion, ahora) is None


def test_45_minutos_entre_dos_nudges(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    iniciativa.registrar(conexion, uuid4(), "encoger", ahora - timedelta(minutes=44))
    _abrir_sesion(conexion, ahora - timedelta(minutes=91), tema="malik")
    assert iniciativa.evaluar(conexion, ahora) is None


def test_pasados_45_minutos_si_puede_sonar(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    iniciativa.registrar(conexion, uuid4(), "encoger", ahora - timedelta(minutes=46))
    _abrir_sesion(conexion, ahora - timedelta(minutes=91), tema="malik")
    candidato = iniciativa.evaluar(conexion, ahora)
    assert candidato is not None
    assert candidato.tipo == "cuerpo"


def test_ahora_no_silencia_esa_regla_dos_horas(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    iniciativa.silenciar(conexion, "cuerpo", ahora)
    _abrir_sesion(conexion, ahora - timedelta(minutes=91), tema="malik")

    assert iniciativa.evaluar(conexion, ahora + timedelta(hours=1)) is None
    candidato = iniciativa.evaluar(conexion, ahora + timedelta(hours=3))
    assert candidato is not None
    assert candidato.tipo == "cuerpo"


def test_la_voz_nunca_pasa_de_25_palabras(tmp_path):
    conexion = _conexion(tmp_path)
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    larga = iniciativa._recortar(" ".join(["palabra"] * 40))
    assert len(larga.split()) <= iniciativa.MAX_PALABRAS_VOZ

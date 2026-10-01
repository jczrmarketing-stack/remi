"""GET /plata (Panel · Metas): solo números, ningún texto que regañe.

`calcular()` toma `ahora` como parámetro — nada acá llama a
`datetime.now()`, para que las pruebas controlen el reloj del todo.
"""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import plata

BOGOTA = plata.BOGOTA


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "plata", "entregas", "db", "modelos"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _entrega(conexion, fecha: datetime, monto: float | None, estado: str, cliente: str = "Alfonso") -> None:
    conexion.execute(
        "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
        "VALUES (?, ?, ?, ?, ?, ?, 1)",
        (str(uuid4()), cliente, str(uuid4()), fecha.isoformat(), monto, estado),
    )
    conexion.commit()


def test_sin_entregas_cobrado_es_cero_nunca_error(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.get("/plata")
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["semana"]["cobrado"] == 0
    assert cuerpo["mes"]["cobrado"] == 0
    assert cuerpo["mes"]["faltan"] == cuerpo["mes"]["meta"]
    assert cuerpo["proximo"] is None


def test_meta_semanal_es_la_mensual_sobre_4_33(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/plata").json()
    assert cuerpo["semana"]["meta_semanal"] == 2400 / 4.33
    assert cuerpo["mes"]["meta"] == 2400


def test_cobrado_de_la_semana_solo_cuenta_pagadas_de_esta_semana(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    lunes = plata._lunes(ahora)

    _entrega(conexion, lunes, 500, "pagada")  # de esta semana
    _entrega(conexion, lunes - timedelta(days=1), 900, "pagada")  # semana pasada
    _entrega(conexion, ahora, 300, "camino")  # no cobrada
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.semana.cobrado == 500


def test_cobrado_del_mes_suma_todas_las_pagadas_del_mes(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    primero = plata._primero_del_mes(ahora)

    _entrega(conexion, primero, 500, "pagada")
    _entrega(conexion, ahora, 300, "pagada")
    _entrega(conexion, primero - timedelta(days=1), 999, "pagada")  # mes pasado
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.mes.cobrado == 800
    assert resultado.mes.faltan == 2400 - 800


def test_faltan_nunca_es_negativo_si_ya_se_supero_la_meta(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _entrega(conexion, ahora, 5000, "pagada")
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.mes.faltan == 0


def test_proximo_es_la_entrega_con_dinero_mas_cercana_sin_cobrar(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    _entrega(conexion, ahora + timedelta(days=10), 1000, "camino", cliente="Lejano")
    _entrega(conexion, ahora + timedelta(days=2), 500, "entregada", cliente="Cercano")
    _entrega(conexion, ahora - timedelta(days=1), 200, "camino", cliente="Pasado")  # ya pasó
    _entrega(conexion, ahora + timedelta(days=1), None, "camino", cliente="SinMonto")  # sin monto
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    assert resultado.proximo is not None
    assert resultado.proximo.cliente == "Cercano"
    assert resultado.proximo.monto == 500


def test_mes_entregas_lista_una_linea_por_pagada_del_mes(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    primero = plata._primero_del_mes(ahora)

    _entrega(conexion, primero, 500, "pagada", cliente="Alfonso")
    _entrega(conexion, ahora, 300, "pagada", cliente="Beto")
    _entrega(conexion, primero - timedelta(days=1), 999, "pagada", cliente="MesPasado")
    _entrega(conexion, ahora, 700, "camino", cliente="NoPagada")
    conexion.close()

    resultado = plata.calcular(db.conectar(), ahora)
    clientes = [e.cliente for e in resultado.mes.entregas]
    assert clientes == ["Alfonso", "Beto"]
    assert [e.monto for e in resultado.mes.entregas] == [500, 300]


def test_nunca_hay_texto_que_regane(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/plata").json()
    for valor in _valores_string(cuerpo):
        for palabra in ("atrasa", "deber", "fall", "urgen", "mal"):
            assert palabra not in valor.lower()


def _valores_string(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _valores_string(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _valores_string(v)
    elif isinstance(obj, str):
        yield obj


# — J1 (Biblia v3.7): metas con nombre, la segunda dormida, revisión en frío —


def _config(tmp_path, monkeypatch, contenido: dict) -> None:
    import json

    ruta = tmp_path / "plata.json"
    ruta.write_text(json.dumps(contenido))
    monkeypatch.setattr(plata, "RUTA_CONFIG", ruta)


CONFIG_CON_METAS = {
    "meta_mensual": 2400,
    "moneda": "USD",
    "metas": [
        {"nombre": "Vivir solo", "horizonte_meses": 12},
        {"nombre": "Carro", "horizonte_meses": 18, "monto_mes": 1100, "activa_desde_pct": 50},
    ],
    "lineas": [
        {"id": "software", "nombre": "Software (clientes)", "temas": ["upvisuals", "beam"]},
        {"id": "malik", "nombre": "Malik (contenido)", "temas": ["malik"]},
    ],
    "revision_fria": {"dia": "viernes", "hora": "16:30", "minutos": 10},
}


def test_la_primera_meta_lleva_nombre_y_el_numero_de_meta_mensual(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, CONFIG_CON_METAS)
    import db

    resultado = plata.calcular(db.conectar(), datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc))

    primera = resultado.metas[0]
    assert (primera.nombre, primera.horizonte_meses, primera.monto_mes, primera.activa) == ("Vivir solo", 12, 2400, True)


def test_la_segunda_meta_duerme_hasta_que_la_primera_pasa_de_la_mitad(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, CONFIG_CON_METAS)
    import db

    ahora = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    conexion = db.conectar()
    _entrega(conexion, ahora - timedelta(days=2), 1000, "pagada")  # 41 % de 2.400

    dormida = plata.calcular(conexion, ahora).metas[1]
    assert (dormida.nombre, dormida.monto_mes, dormida.activa, dormida.activa_desde_pct) == ("Carro", 1100, False, 50)

    _entrega(conexion, ahora - timedelta(days=1), 300, "pagada")  # 54 %
    assert plata.calcular(conexion, ahora).metas[1].activa is True


def test_sin_metas_en_la_config_queda_la_mensual_de_siempre(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, {"meta_mensual": 2400, "moneda": "USD"})
    import db

    resultado = plata.calcular(db.conectar(), datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc))

    assert [(m.nombre, m.monto_mes, m.activa) for m in resultado.metas] == [("Meta mensual", 2400, True)]
    assert resultado.revision_fria is None


def test_una_meta_mal_escrita_se_salta_y_no_rompe_plata(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    _config(
        tmp_path,
        monkeypatch,
        {"meta_mensual": 2400, "metas": [{"nombre": "Vivir solo"}, {"nombre": "Sin monto"}, "texto suelto", {"monto_mes": 5}]},
    )
    import db

    resultado = plata.calcular(db.conectar(), datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc))

    assert [m.nombre for m in resultado.metas] == ["Vivir solo"]


def test_la_revision_en_frio_sale_de_la_config(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, CONFIG_CON_METAS)
    import db

    revision = plata.calcular(db.conectar(), datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)).revision_fria

    assert revision is not None
    assert (revision.dia, revision.hora, revision.minutos) == ("viernes", "16:30", 10)


def test_la_linea_de_un_libro_sale_de_la_config(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    _config(tmp_path, monkeypatch, CONFIG_CON_METAS)

    assert plata.linea_de_tema("upvisuals") == "software"
    assert plata.linea_de_tema("malik") == "malik"
    # Remi y Omniway no son una línea de ingreso.
    assert plata.linea_de_tema("remi") is None
    assert plata.linea_de_tema(None) is None


def test_la_config_real_del_repo_trae_metas_lineas_y_revision(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    cuerpo = cliente.get("/plata").json()

    assert cuerpo["metas"][0]["monto_mes"] == cuerpo["mes"]["meta"]
    assert all(set(m) == {"nombre", "horizonte_meses", "monto_mes", "activa", "activa_desde_pct"} for m in cuerpo["metas"])
    assert cuerpo["revision_fria"] is None or set(cuerpo["revision_fria"]) == {"dia", "hora", "minutos"}

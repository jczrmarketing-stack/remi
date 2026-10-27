"""Puente Notion → Ventanita: avisos de «Remi · CRM de vida».
Reloj falso y cliente de Notion falso; nunca red ni datetime.now()."""
import sys
from datetime import datetime, timedelta, timezone

import httpx

BASE = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)  # 10:00 en Bogotá
NOCHE = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)  # 03:00 en Bogotá


def _modulo(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("db", "avisos", "notion", "notion_avisos"):
        sys.modules.pop(nombre, None)
    import db

    db.inicializar_esquema()
    import notion_avisos

    return notion_avisos, db.conectar()


def _pagina(pid, que, vence, paso="Un paso pequeño", frente="Clientes", notas=""):
    return {
        "id": pid,
        "properties": {
            "Qué": {"title": [{"plain_text": que}]},
            "Paso mínimo": {"rich_text": [{"plain_text": paso}]},
            "Frente": {"select": {"name": frente}},
            "Notas": {"rich_text": [{"plain_text": notas}]},
            "Avisar el": {"date": {"start": vence} if vence else None},
        },
    }


class FalsoNotion:
    def __init__(self, paginas):
        self.paginas = paginas
        self.hechas = []
        self.falla = False
        self.ultimo_filtro = None

    def consultar_fuente(self, fuente_id, filtro):
        self.ultimo_filtro = filtro
        return self.paginas

    def actualizar_pagina(self, pagina_id, propiedades, *, version=None):
        if self.falla:
            raise httpx.ConnectError("sin red")
        self.hechas.append((pagina_id, propiedades, version))


def test_solo_guarda_las_vencidas_y_filtra_en_notion(tmp_path, monkeypatch):
    na, conexion = _modulo(tmp_path, monkeypatch)
    cliente = FalsoNotion([
        _pagina("a", "Ya venció", "2026-10-15T09:00:00.000-05:00"),
        _pagina("b", "Aún no", "2026-10-15T20:00:00.000-05:00"),
        _pagina("c", "Solo día", "2026-10-15"),
        _pagina("d", "Sin fecha", None),
    ])
    assert na.sondear(conexion, cliente, BASE) == 2
    guardadas = {f["pagina_id"] for f in conexion.execute("SELECT pagina_id FROM avisos_notion")}
    assert guardadas == {"a", "c"}
    y = cliente.ultimo_filtro["and"]
    assert {"property": "Tipo", "select": {"equals": "Aviso"}} in y
    assert {"property": "Estado", "status": {"does_not_equal": "Hecha"}} in y
    assert {"property": "Estado", "status": {"does_not_equal": "Soltada"}} in y
    assert {"property": "Avisar el", "date": {"on_or_before": "2026-10-16"}} in y


def test_ahora_no_vuelve_en_dos_horas_y_sale_encogido(tmp_path, monkeypatch):
    na, conexion = _modulo(tmp_path, monkeypatch)
    cliente = FalsoNotion([_pagina("a", "Llamar a Alfonso", "2026-10-15T09:00:00-05:00", paso="Abrir el chat")])
    na.sondear(conexion, cliente, BASE)

    primero = na.pendiente(conexion, BASE)
    assert (primero.que, primero.paso_minimo, primero.encogido) == ("Llamar a Alfonso", "Abrir el chat", False)
    assert na.pendiente(conexion, BASE + timedelta(minutes=1)).id == "a"  # sigue en pantalla, no es otra salida

    assert na.responder(conexion, "a", "ahora_no", BASE + timedelta(minutes=2), cliente)
    assert na.pendiente(conexion, BASE + timedelta(minutes=2 + 119)) is None
    segundo = na.pendiente(conexion, BASE + timedelta(minutes=2 + 120))
    assert segundo is not None and segundo.encogido is True
    assert cliente.hechas == []  # «Ahora no» no toca Notion ni deja marca de fallo


def test_listo_pasa_a_hecha_y_reintenta_si_no_hay_red(tmp_path, monkeypatch):
    na, conexion = _modulo(tmp_path, monkeypatch)
    cliente = FalsoNotion([_pagina("a", "Cobrar", "2026-10-15T09:00:00-05:00")])
    na.sondear(conexion, cliente, BASE)
    na.pendiente(conexion, BASE)

    cliente.falla = True
    assert na.responder(conexion, "a", "listo", BASE, cliente)
    assert na.pendiente(conexion, BASE + timedelta(hours=5)) is None  # no vuelve a salir
    assert conexion.execute("SELECT hecha_pendiente FROM avisos_notion WHERE pagina_id='a'").fetchone()[0] == 1

    cliente.falla = False
    na.sondear(conexion, cliente, BASE + timedelta(minutes=5))
    assert cliente.hechas == [("a", {"Estado": {"status": {"name": "Hecha"}}}, "2025-09-03")]
    assert conexion.execute("SELECT hecha_pendiente FROM avisos_notion WHERE pagina_id='a'").fetchone()[0] == 0


def test_cinco_al_dia_y_noventa_minutos_entre_ellos(tmp_path, monkeypatch):
    na, conexion = _modulo(tmp_path, monkeypatch)
    cliente = FalsoNotion([_pagina(f"p{i}", f"Tarea {i}", "2026-10-15T08:00:00-05:00") for i in range(7)])
    na.sondear(conexion, cliente, BASE)

    primero = na.pendiente(conexion, BASE)
    na.responder(conexion, primero.id, "listo", BASE, cliente)
    assert na.pendiente(conexion, BASE + timedelta(minutes=89)) is None  # falta para los 90

    salieron = 1
    for i in range(1, 7):
        aviso = na.pendiente(conexion, BASE + timedelta(minutes=91 * i))
        if aviso is not None:
            salieron += 1
            na.responder(conexion, aviso.id, "listo", BASE + timedelta(minutes=91 * i), cliente)
    assert salieron == 5


def test_de_noche_no_sale_salvo_fiverr_24h(tmp_path, monkeypatch):
    na, conexion = _modulo(tmp_path, monkeypatch)
    cliente = FalsoNotion([
        _pagina("normal", "Normal", "2026-10-14T20:00:00-05:00"),
        _pagina("nota", "24h pero otro frente", "2026-10-14T20:00:00-05:00", notas="24h"),
    ])
    na.sondear(conexion, cliente, NOCHE)
    assert na.pendiente(conexion, NOCHE) is None

    cliente.paginas.append(_pagina("fiverr", "Cliente de Fiverr", "2026-10-14T20:00:00-05:00", frente="Fiverr", notas="Responder en 24H"))
    na.sondear(conexion, cliente, NOCHE)
    fiverr = na.pendiente(conexion, NOCHE)
    assert fiverr is not None and fiverr.id == "fiverr"
    na.responder(conexion, "fiverr", "listo", NOCHE, cliente)

    # Fuera de presupuesto: a las 10:00 un aviso normal sale aunque el de Fiverr saliera de madrugada.
    assert na.pendiente(conexion, BASE).id in {"normal", "nota"}


def test_lo_que_ya_no_esta_abierto_en_notion_se_borra_salvo_un_listo_sin_escribir(tmp_path, monkeypatch):
    na, conexion = _modulo(tmp_path, monkeypatch)
    cliente = FalsoNotion([_pagina("a", "Uno", "2026-10-15T09:00:00-05:00"), _pagina("b", "Dos", "2026-10-15T09:00:00-05:00")])
    na.sondear(conexion, cliente, BASE)
    na.pendiente(conexion, BASE)
    cliente.falla = True
    na.responder(conexion, "a", "listo", BASE, cliente)  # a queda con la escritura pendiente

    cliente.paginas = []  # en Notion ya nada está abierto
    cliente.falla = True  # y tampoco hay red para reintentar
    na.sondear(conexion, cliente, BASE + timedelta(minutes=5))
    quedan = {f["pagina_id"] for f in conexion.execute("SELECT pagina_id FROM avisos_notion")}
    assert quedan == {"a"}

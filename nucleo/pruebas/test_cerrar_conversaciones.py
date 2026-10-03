"""T9.5: lo que se habla con Remi también queda — una conversación de la
ventanita/Telegram, 60 min sin turnos, con sustancia, deja su episodio."""
import sys
from datetime import datetime, timedelta, timezone

import db

TEXTO_SUSTANCIAL = "Hablamos del precio de la Fase 1 de UpVisuals. " * 40  # > LARGO_MINIMO


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "boveda" / "proyectos"))
    for nombre in ("db", "cierre", "episodios", "libros", "temas"):
        sys.modules.pop(nombre, None)
    import importlib

    import cierre as c
    import db as d

    importlib.reload(d)
    importlib.reload(c)
    # Sin modelo: el resumen plano. Una prueba no llama a la trastienda.
    monkeypatch.setattr(c, "redactar", lambda pedido: None)
    return d, c


def _conversacion_con_turnos(db_mod, texto_juan: str, hace: timedelta) -> str:
    conexion = db_mod.conectar()
    try:
        ahora = datetime.now(timezone.utc) - hace
        conversacion_id = db_mod.guardar_turno(conexion, "juan", texto_juan, ahora)
        db_mod.guardar_turno(conexion, "remi", "Entendido.", ahora + timedelta(seconds=5))
        # Desde el 3-oct una conversación termina cuando Juan Camilo la cambia,
        # no por tiempo: las «viejas» de estas pruebas son las que él cerró.
        if hace >= timedelta(minutes=60):
            db_mod.cerrar_conversacion_vigente(conexion, datetime.now(timezone.utc))
    finally:
        conexion.close()
    return conversacion_id


def test_una_conversacion_activa_no_se_toca(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=5))

    cerradas = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert cerradas == 0


def test_una_conversacion_inactiva_sustancial_deja_episodio(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    conversacion_id = _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))

    cerradas = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert cerradas == 1
    episodios = list((tmp_path / "boveda" / "episodios").glob("*charla*.md"))
    assert len(episodios) == 1

    conexion = db_mod.conectar()
    try:
        fila = conexion.execute(
            "SELECT titulo, episodio_hecho FROM conversaciones WHERE id = ?", (conversacion_id,)
        ).fetchone()
    finally:
        conexion.close()
    assert fila["episodio_hecho"] == 1
    assert fila["titulo"]


def test_una_conversacion_trivial_no_deja_episodio_pero_se_marca(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    conversacion_id = _conversacion_con_turnos(db_mod, "hola", hace=timedelta(minutes=90))

    cerradas = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert cerradas == 0
    assert list((tmp_path / "boveda" / "episodios").glob("*.md")) == []
    conexion = db_mod.conectar()
    try:
        fila = conexion.execute(
            "SELECT episodio_hecho FROM conversaciones WHERE id = ?", (conversacion_id,)
        ).fetchone()
    finally:
        conexion.close()
    assert fila["episodio_hecho"] == 1


def test_no_se_revisa_dos_veces(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))

    cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))
    segunda = cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert segunda == 0
    assert len(list((tmp_path / "boveda" / "episodios").glob("*.md"))) == 1


# — F3.5 (plan de cierre): la misma conversación se cerraba una y otra vez —


def _libro_upvisuals(tmp_path):
    proyectos = tmp_path / "boveda" / "proyectos"
    proyectos.mkdir(parents=True, exist_ok=True)
    (proyectos / "upvisuals.md").write_text(
        "---\ntitulo: UpVisuals\ntema: upvisuals\nresumen: r\nclaves: [upvisuals]\n---\n\n## Estado\n\nQuedaste: nada\n"
    )
    return proyectos / "upvisuals.md"


def test_a_cerrar_dos_veces_deja_un_episodio_y_un_solo_cambio_de_estado(tmp_path, monkeypatch):
    libro = _libro_upvisuals(tmp_path)
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))
    escritos = []
    original = cierre.estado_libro.escribir_estado
    monkeypatch.setattr(cierre.estado_libro, "escribir_estado", lambda a, t: (escritos.append(a), original(a, t)))

    assert cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc)) == 1
    assert cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc)) == 0

    assert len(list((tmp_path / "boveda" / "episodios").glob("*.md"))) == 1
    assert escritos == [libro]


def test_b_episodio_hecho_queda_en_1_aunque_escribir_el_episodio_falle(tmp_path, monkeypatch):
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    conversacion_id = _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))

    def falla(*a, **k):
        raise OSError("disco lleno")

    monkeypatch.setattr(cierre, "_escribir_episodio_de_conversacion", falla)
    assert cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc)) == 0

    conexion = db_mod.conectar()
    try:
        fila = conexion.execute("SELECT episodio_hecho FROM conversaciones WHERE id = ?", (conversacion_id,)).fetchone()
    finally:
        conexion.close()
    assert fila["episodio_hecho"] == 1


def test_c_el_commit_nunca_nombra_un_episodio_que_no_quedo_en_la_boveda(tmp_path, monkeypatch):
    """Lo que pasaba en la suite: REMI_BOVEDA en una carpeta y la bóveda que
    commitea (la de los libros) en otra. El episodio caía fuera y el commit
    lo nombraba igual."""
    _libro_upvisuals(tmp_path)
    db_mod, cierre = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "otra-boveda"))
    _conversacion_con_turnos(db_mod, TEXTO_SUSTANCIAL, hace=timedelta(minutes=90))
    mensajes = []
    monkeypatch.setattr(cierre.boveda_git, "snapshot_despues", mensajes.append)

    cierre.cerrar_conversaciones_inactivas(datetime.now(timezone.utc))

    assert mensajes, "algo se escribió: tiene que quedar dicho"
    for mensaje in mensajes:
        assert "episodio 2026" not in mensaje and ".md al cerrar" not in mensaje, mensaje
    assert any("fuera de esta bóveda" in m for m in mensajes), mensajes

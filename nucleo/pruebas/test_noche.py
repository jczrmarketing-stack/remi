"""Consolidación nocturna: solo toca lo que tiene evidencia real del día."""
import importlib
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

LIBRO = """---
titulo: Malik
tema: malik
resumen: Las cuentas de WhatsApp.
ruta: {ruta}
---

## Estado

Quedaste: nada todavía.
Decisiones: ninguna.
Próximo paso: arrancar.
"""

EPISODIO = """---
titulo: {titulo}
tema: malik
resumen: {resumen}
---

## Qué se hizo

{cuerpo}
"""


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    for nombre in ("db", "libros", "noche", "sembrar_conocimiento", "vectores", "estado_libro"):
        sys.modules.pop(nombre, None)
    import db
    import libros
    import noche
    import sembrar_conocimiento

    importlib.reload(db)
    importlib.reload(libros)
    importlib.reload(sembrar_conocimiento)
    importlib.reload(noche)
    (tmp_path / "proyectos").mkdir(parents=True, exist_ok=True)
    (tmp_path / "episodios").mkdir(parents=True, exist_ok=True)
    return noche, db, sembrar_conocimiento


def _libro(tmp_path, ruta_proyecto="/tmp/malik"):
    (tmp_path / "proyectos" / "malik.md").write_text(LIBRO.format(ruta=ruta_proyecto))


def _git(tmp_path, *args):
    return subprocess.run(["git", "-C", str(tmp_path), *args], capture_output=True, text=True, check=True)


def _iniciar_repo_git(tmp_path):
    """Bóveda de prueba, nunca la remi-mente real: `git init` en el tmpdir
    del test, con un commit inicial ya hecho por quien llama."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "remi@example.com")
    _git(tmp_path, "config", "user.name", "Remi de prueba")


def _commit(tmp_path, mensaje):
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", mensaje)


def _episodio(tmp_path, nombre, titulo, resumen, cuerpo, hoy: date):
    (tmp_path / "episodios" / f"{hoy.isoformat()}-{nombre}.md").write_text(
        EPISODIO.format(titulo=titulo, resumen=resumen, cuerpo=cuerpo)
    )


def test_actualiza_el_estado_solo_del_libro_con_episodios_de_hoy(tmp_path, monkeypatch):
    noche, db, _ = _arrancar(tmp_path, monkeypatch)
    _libro(tmp_path)
    hoy = date.today()
    _episodio(tmp_path, "a", "Se arregló el webhook", "El webhook fallaba por timeout", "Detalle.", hoy)
    # T5.6: el orden de escritura real (y la resolución del mtime del
    # filesystem) no alcanza para garantizar que el episodio quede más
    # nuevo que el libro — se fija a mano.
    ahora = datetime.now(timezone.utc).timestamp()
    os.utime(tmp_path / "proyectos" / "malik.md", (ahora - 60, ahora - 60))
    os.utime(tmp_path / "episodios" / f"{hoy.isoformat()}-a.md", (ahora, ahora))

    pedidos_vistos = []

    def redactar_falso(pedido: str) -> str:
        pedidos_vistos.append(pedido)
        return "Quedaste: se arregló el webhook.\nDecisiones: ninguna.\nProximo paso: seguir mañana."

    import estado_libro
    monkeypatch.setattr(estado_libro, "redactar", redactar_falso)
    monkeypatch.setattr(noche, "estado_libro", estado_libro)

    resultado = noche.actualizar_estados_del_dia(hoy)
    assert resultado == {"malik": "actualizado"}
    assert len(pedidos_vistos) == 1
    assert "Commits nuevos:" in pedidos_vistos[0]
    assert "Se arregló el webhook" in pedidos_vistos[0]
    texto = (tmp_path / "proyectos" / "malik.md").read_text()
    assert "se arregló el webhook" in texto.lower()


def test_la_consolidacion_pasa_de_verdad_por_la_verificacion_mecanica_anti_invento(tmp_path, monkeypatch):
    """Integración de punta a punta del incidente real: sin monkeypatchear
    `estado_libro.redactar` (para no esconder su lógica interna), solo el
    límite con el modelo (`pensar._llamar_proveedor`, la trastienda de
    `config/motores.json`), igual que lo probaría un caso real. Si el modelo
    devuelve una sigla que no está en los episodios de hoy, la consolidación
    tiene que rechazarla y no tocar el libro."""
    noche, db, _ = _arrancar(tmp_path, monkeypatch)
    _libro(tmp_path)
    hoy = date.today()
    _episodio(tmp_path, "a", "Se arregló el webhook", "El webhook fallaba por timeout", "Detalle.", hoy)
    antes = (tmp_path / "proyectos" / "malik.md").read_text()

    import estado_libro
    import pensar

    datos_inventados = {
        "choices": [
            {
                "message": {
                    "content": (
                        "Quedaste: arreglaste el webhook con N8N.\n"
                        "Decisiones: ninguna.\nPróximo paso: seguir mañana."
                    )
                }
            }
        ],
        "usage": {},
    }
    monkeypatch.setattr(pensar, "RUTA_MOTORES", tmp_path / "no-existe.json")
    monkeypatch.setattr(pensar, "_llamar_proveedor", lambda *a, **k: datos_inventados)
    monkeypatch.setattr(noche, "estado_libro", estado_libro)

    resultado = noche.actualizar_estados_del_dia(hoy)
    assert resultado == {"malik": "rechazado_o_sin_respuesta"}  # redactar() rechazó el invento
    assert (tmp_path / "proyectos" / "malik.md").read_text() == antes


def test_no_toca_un_episodio_mas_viejo_que_la_ultima_escritura_del_estado(tmp_path, monkeypatch):
    """El incidente real del 30-sep (docs/BITACORA.md): dos corridas seguidas
    de la consolidación pisaron dos veces un «Próximo paso» que Juan Camilo
    ya había confirmado a mano ese mismo día, re-derivándolo de los mismos
    episodios viejos — y la segunda vez, inventando datos que no estaban en
    ninguna fuente. Un episodio solo es evidencia si es más nuevo que la
    última escritura del Estado."""
    noche, db, _ = _arrancar(tmp_path, monkeypatch)
    hoy = date.today()
    _episodio(tmp_path, "a", "Se arregló el webhook", "El webhook fallaba por timeout", "Detalle.", hoy)
    _libro(tmp_path)  # el libro se escribe DESPUÉS del episodio: es más nuevo
    # T5.6: fijado a mano — el orden de escritura real no garantiza por sí
    # solo la diferencia de mtime que este caso necesita probar.
    ahora = datetime.now(timezone.utc).timestamp()
    os.utime(tmp_path / "episodios" / f"{hoy.isoformat()}-a.md", (ahora - 60, ahora - 60))
    os.utime(tmp_path / "proyectos" / "malik.md", (ahora, ahora))

    llamado = []
    import estado_libro
    monkeypatch.setattr(estado_libro, "redactar", lambda p: llamado.append(1) or "no debería llegar aquí")
    monkeypatch.setattr(noche, "estado_libro", estado_libro)

    resultado = noche.actualizar_estados_del_dia(hoy)
    assert resultado == {"malik": "sin_evidencia_nueva"}
    assert not llamado


def test_no_toca_ni_llama_al_modelo_sin_episodios_de_hoy(tmp_path, monkeypatch):
    noche, db, _ = _arrancar(tmp_path, monkeypatch)
    _libro(tmp_path)
    original = (tmp_path / "proyectos" / "malik.md").read_text()

    llamado = []
    import estado_libro
    monkeypatch.setattr(estado_libro, "redactar", lambda p: llamado.append(1) or "no debería llegar aquí")
    monkeypatch.setattr(noche, "estado_libro", estado_libro)

    resultado = noche.actualizar_estados_del_dia(date.today())
    assert resultado == {}
    assert not llamado
    assert (tmp_path / "proyectos" / "malik.md").read_text() == original


def test_fusiona_episodios_repetidos_del_mismo_dia_y_libro(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    hoy = date.today()
    _episodio(tmp_path, "a", "Primero", "Se resolvió el mismo bug de siempre", "Versión corta.", hoy)
    _episodio(tmp_path, "b", "Segundo", "Se resolvió el mismo bug de siempre", "Versión con más detalle.", hoy)

    fusiones = noche.fusionar_episodios_del_dia(hoy)
    assert len(fusiones) == 1
    mantenido, fusionado = fusiones[0]
    assert mantenido == f"{hoy.isoformat()}-a.md"
    assert fusionado == f"{hoy.isoformat()}-b.md"
    # Nunca se borra (regla del plan de cierre): queda con fusionado_en.
    repetido = tmp_path / "episodios" / fusionado
    assert repetido.exists()
    assert f"fusionado_en: {mantenido}" in repetido.read_text()
    import libros

    assert libros.fuera_del_estante(repetido)
    # Correr la noche otra vez no lo vuelve a fusionar.
    assert noche.fusionar_episodios_del_dia(hoy) == []
    texto = (tmp_path / "episodios" / mantenido).read_text()
    assert "Versión corta." in texto
    assert "Versión con más detalle." in texto


def test_no_fusiona_episodios_con_resumen_distinto(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    hoy = date.today()
    _episodio(tmp_path, "a", "Uno", "Se resolvió el bug del login", "x", hoy)
    _episodio(tmp_path, "b", "Dos", "Se armó el nuevo flujo de pagos", "y", hoy)

    fusiones = noche.fusionar_episodios_del_dia(hoy)
    assert fusiones == []
    assert (tmp_path / "episodios" / f"{hoy.isoformat()}-a.md").exists()
    assert (tmp_path / "episodios" / f"{hoy.isoformat()}-b.md").exists()


def test_reordenar_mente_baja_de_nivel_lo_que_no_se_toco_en_una_semana(tmp_path, monkeypatch):
    noche, db, sembrar_conocimiento = _arrancar(tmp_path, monkeypatch)
    _libro(tmp_path)
    (tmp_path / "proyectos" / "viejo.md").write_text(
        LIBRO.format(ruta="/tmp/viejo").replace("titulo: Malik", "titulo: Viejo").replace("tema: malik", "tema: viejo")
    )
    hace_diez_dias = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(tmp_path / "proyectos" / "viejo.md", (hace_diez_dias, hace_diez_dias))

    cuenta = noche.reordenar_mente()
    assert cuenta["creadas"] == 2

    conexion = db.conectar()
    try:
        nuevo = db.memorias_por_tema(conexion, "malik")[0]
        viejo = db.memorias_por_tema(conexion, "viejo")[0]
    finally:
        conexion.close()
    assert nuevo.nivel == 1
    assert viejo.nivel == 2


# — reporte de la noche: diff de git de lo que cambió esta corrida —


def test_diff_de_la_noche_sin_referencia_devuelve_vacio(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    assert noche.diff_de_la_noche(None) == []


def test_head_git_none_si_la_boveda_no_es_repo(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    assert noche._head_git() is None


def test_diff_de_la_noche_reporta_el_libro_que_cambio(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    _iniciar_repo_git(tmp_path)
    _libro(tmp_path)
    _commit(tmp_path, "estado inicial de malik")

    referencia = noche._head_git()
    assert referencia is not None

    (tmp_path / "proyectos" / "malik.md").write_text(
        LIBRO.format(ruta="/tmp/malik").replace(
            "Próximo paso: arrancar.", "Próximo paso: seguir con el webhook."
        )
    )
    _commit(tmp_path, "consolidación nocturna: Estado de malik.md")

    cambios = noche.diff_de_la_noche(referencia)
    assert len(cambios) == 1
    titulo, diff = cambios[0]
    assert titulo == "Malik"
    assert "seguir con el webhook" in diff


def test_diff_de_la_noche_no_reporta_libros_que_no_cambiaron(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    _iniciar_repo_git(tmp_path)
    _libro(tmp_path)
    _commit(tmp_path, "estado inicial")
    referencia = noche._head_git()

    # nada cambia después de la referencia
    assert noche.diff_de_la_noche(referencia) == []


def test_diff_de_la_noche_recorta_a_max_lineas(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    _iniciar_repo_git(tmp_path)
    _libro(tmp_path)
    _commit(tmp_path, "estado inicial")
    referencia = noche._head_git()

    lineas_nuevas = "\n".join(f"Línea {i}" for i in range(30))
    (tmp_path / "proyectos" / "malik.md").write_text(
        LIBRO.format(ruta="/tmp/malik") + "\n" + lineas_nuevas
    )
    _commit(tmp_path, "agranda el libro")

    cambios = noche.diff_de_la_noche(referencia, max_lineas=8)
    assert len(cambios) == 1
    _, diff = cambios[0]
    assert len(diff.splitlines()) <= 8


def test_diff_de_la_noche_usa_el_nombre_de_archivo_si_el_libro_ya_no_se_puede_leer(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    _iniciar_repo_git(tmp_path)
    _libro(tmp_path)
    _commit(tmp_path, "estado inicial")
    referencia = noche._head_git()

    (tmp_path / "proyectos" / "malik.md").unlink()
    _commit(tmp_path, "borra malik")

    cambios = noche.diff_de_la_noche(referencia)
    assert len(cambios) == 1
    assert cambios[0][0] == "malik"


# — reporte de la noche: POST a /telegram/avisar —


def test_enviar_reporte_de_la_noche_postea_el_texto_armado(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(noche, "_url_avisar", lambda: "http://127.0.0.1:4400/telegram/avisar")
    posteado = {}

    def post_falso(url, json, timeout):
        posteado["url"] = url
        posteado["json"] = json

    monkeypatch.setattr(noche.httpx, "post", post_falso)

    noche.enviar_reporte_de_la_noche([("Malik", "diff corto")])

    assert posteado["url"] == "http://127.0.0.1:4400/telegram/avisar"
    assert posteado["json"]["texto"].startswith("Anoche cambié 1 libro")
    assert posteado["json"]["urgente"] is True  # si no, avisar() lo descarta en silencio (4:00 cae en 23:00–7:00)


def test_enviar_reporte_de_la_noche_sin_cambios_manda_no_toque_nada(tmp_path, monkeypatch):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(noche, "_url_avisar", lambda: "http://127.0.0.1:4400/telegram/avisar")
    posteado = {}
    monkeypatch.setattr(
        noche.httpx, "post", lambda url, json, timeout: posteado.update(url=url, json=json)
    )

    noche.enviar_reporte_de_la_noche([])

    assert posteado["json"]["texto"] == "Anoche no toqué nada"


def test_enviar_reporte_de_la_noche_no_revienta_si_falla_el_post(tmp_path, monkeypatch, capsys):
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    monkeypatch.setattr(noche, "_url_avisar", lambda: "http://127.0.0.1:4400/telegram/avisar")

    def post_roto(url, json, timeout):
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(noche.httpx, "post", post_roto)

    noche.enviar_reporte_de_la_noche([("Malik", "diff")])  # no revienta
    assert "sin conexión" in capsys.readouterr().err


def test_correr_manda_el_reporte_de_la_noche(tmp_path, monkeypatch):
    """Integración de punta a punta de `correr()`: sin bóveda git, no hay
    cambios que reportar y el mensaje es «Anoche no toqué nada»."""
    noche, _, _ = _arrancar(tmp_path, monkeypatch)
    enviados = []
    monkeypatch.setattr(noche, "enviar_reporte_de_la_noche", lambda cambios: enviados.append(cambios))
    monkeypatch.setattr(noche, "recalcular_vectores", lambda: 0)

    noche.correr(date.today())

    assert enviados == [[]]

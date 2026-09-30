"""Consolidación nocturna: solo toca lo que tiene evidencia real del día."""
import importlib
import os
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


def _episodio(tmp_path, nombre, titulo, resumen, cuerpo, hoy: date):
    (tmp_path / "episodios" / f"{hoy.isoformat()}-{nombre}.md").write_text(
        EPISODIO.format(titulo=titulo, resumen=resumen, cuerpo=cuerpo)
    )


def test_actualiza_el_estado_solo_del_libro_con_episodios_de_hoy(tmp_path, monkeypatch):
    noche, db, _ = _arrancar(tmp_path, monkeypatch)
    _libro(tmp_path)
    hoy = date.today()
    _episodio(tmp_path, "a", "Se arregló el webhook", "El webhook fallaba por timeout", "Detalle.", hoy)

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
    assert not (tmp_path / "episodios" / fusionado).exists()
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

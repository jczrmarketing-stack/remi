"""Un commit reescribe ## Estado. Dentro de 10 min, los siguientes esperan."""
import importlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import estado_libro


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_ESTADO", "1")
    monkeypatch.setenv("REMI_TRABAJO_EN_LINEA", "1")
    for nombre in ("servidor", "db", "trabajo", "libros"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _libro(tmp_path, cuerpo: str) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(cuerpo)


LIBRO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
ruta: {repo}
---

- Prioridad baja.

## Notas

Nada de borrar esto.
"""


def _falso(vistos: list[str]):
    def redactar(pedido: str) -> str:
        vistos.append(pedido)
        return (
            "Quedaste: en el mosaico.\n"
            "Decisiones: ninguna nueva.\n"
            "Próximo paso: abrir la ficha, cinco minutos."
        )

    return redactar


def test_el_primer_commit_cambia_el_estado_y_deja_el_resto(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    vistos: list[str] = []
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", _falso(vistos))
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/evento",
        json={
            "tipo": "commit",
            "ruta": str(repo),
            "datos": {"mensaje": "el mosaico", "rama": "main", "archivos": ["a.ts"]},
        },
    )

    assert respuesta.status_code == 200
    texto = (tmp_path / "libros" / "malik.md").read_text()
    assert "Prioridad baja." in texto
    assert "## Notas" in texto
    assert "Nada de borrar esto." in texto
    assert "## Estado" in texto
    assert "Quedaste: en el mosaico." in texto
    assert "Próximo paso: abrir la ficha, cinco minutos." in texto
    assert len(vistos) == 1
    assert "el mosaico" in vistos[0]


def test_dentro_de_diez_minutos_no_redacta_de_nuevo(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    vistos: list[str] = []
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", _falso(vistos))
    cliente = TestClient(servidor.app)
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "primero", "rama": "main", "archivos": []}},
    )
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "segundo", "rama": "main", "archivos": []}},
    )

    assert len(vistos) == 1
    assert "segundo" not in (tmp_path / "libros" / "malik.md").read_text()


def test_la_tanda_siguiente_incluye_los_que_esperaron(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    vistos: list[str] = []
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", _falso(vistos))
    cliente = TestClient(servidor.app)
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "primero", "rama": "main", "archivos": []}},
    )
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "segundo", "rama": "main", "archivos": []}},
    )
    import db

    hace = datetime.now(timezone.utc) - timedelta(minutes=11)
    conexion = db.conectar()
    try:
        conexion.execute("UPDATE trabajo_estado_en SET fecha = ? WHERE tema = 'malik'", (hace.isoformat(),))
        conexion.commit()
    finally:
        conexion.close()
    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "tercero", "rama": "main", "archivos": []}},
    )

    assert len(vistos) == 2
    assert "segundo" in vistos[1]
    assert "tercero" in vistos[1]
    assert "primero" not in vistos[1]


def test_sin_modelo_el_libro_igual_cambia(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, LIBRO.format(repo=repo))
    servidor = _arrancar(tmp_path, monkeypatch)
    import trabajo

    monkeypatch.setattr(trabajo.estado_libro, "redactar", lambda _pedido: None)
    cliente = TestClient(servidor.app)

    cliente.post(
        "/evento",
        json={"tipo": "commit", "ruta": str(repo), "datos": {"mensaje": "el mosaico", "rama": "main", "archivos": []}},
    )

    texto = (tmp_path / "libros" / "malik.md").read_text()
    assert "Quedaste en «el mosaico», rama main." in texto
    assert "Próximo paso: retomar desde ese commit, cinco minutos." in texto


def test_normalizar_acepta_las_tres_lineas() -> None:
    assert estado_libro.normalizar(
        "Quedaste: ahí.\nDecisiones: ninguna nueva.\nPróximo paso: la ficha."
    ) == ("Quedaste: ahí.\nDecisiones: ninguna nueva.\nPróximo paso: la ficha.")
    assert estado_libro.normalizar("solo una frase") is None


def test_sin_evidencia_nueva_redactar_no_llama_a_ningun_modelo(monkeypatch) -> None:
    """El incidente del 30-sep: un pedido con la bandeja de commits vacía no
    puede terminar en una llamada al modelo — ahí es donde inventa."""
    llamados: list[str] = []

    def _falso_claude(*_args, **_kwargs):
        llamados.append("claude")
        raise AssertionError("no debía llamarse a Claude sin evidencia nueva")

    def _falso_ollama(*_args, **_kwargs):
        llamados.append("ollama")
        raise AssertionError("no debía llamarse a Ollama sin evidencia nueva")

    monkeypatch.setattr(estado_libro.pensar, "_una_llamada_claude", _falso_claude)
    monkeypatch.setattr(estado_libro.pensar, "_llamar_ollama", _falso_ollama)

    pedido_vacio = estado_libro.pedido("Malik", "Quedaste: ahí.\nDecisiones: ninguna.\nPróximo paso: seguir.", [])

    assert estado_libro.sin_evidencia_nueva(pedido_vacio) is True
    assert estado_libro.redactar(pedido_vacio) is None
    assert llamados == []


def test_con_evidencia_el_pedido_no_esta_vacio() -> None:
    pedido_con_commit = estado_libro.pedido(
        "Malik", "", [{"mensaje": "el mosaico", "rama": "main", "archivos": ["a.ts"]}]
    )
    assert estado_libro.sin_evidencia_nueva(pedido_con_commit) is False


def test_las_instrucciones_prohiben_inventar_fuera_de_la_fuente() -> None:
    """Defensa en profundidad además de `sin_evidencia_nueva`: aunque sí haya
    commits, la instrucción al modelo tiene que decirle que no complete con
    hechos que no estén en la fuente."""
    baja = estado_libro.INSTRUCCIONES.lower()
    assert "no inventes" in baja
    assert "estado anterior" in baja and "commits" in baja


def test_redactar_manda_la_instruccion_anti_invento_al_modelo(monkeypatch) -> None:
    vistos: dict[str, str] = {}

    class _Pensado:
        paso_minimo = "Quedaste: ahí.\nDecisiones: ninguna nueva.\nPróximo paso: seguir."

    def _capturar_claude(_modo, _pedido, instrucciones, _herramientas):
        vistos["instrucciones"] = instrucciones
        return _Pensado()

    monkeypatch.setattr(estado_libro.pensar, "_una_llamada_claude", _capturar_claude)

    pedido_con_commit = estado_libro.pedido(
        "Malik", "", [{"mensaje": "el mosaico", "rama": "main", "archivos": ["a.ts"]}]
    )
    resultado = estado_libro.redactar(pedido_con_commit)

    assert resultado is not None
    assert "no inventes" in vistos["instrucciones"].lower()

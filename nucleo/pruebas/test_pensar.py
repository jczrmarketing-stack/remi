import importlib
import sys

from fastapi.testclient import TestClient


def _arrancar_servidor():
    for nombre in ("servidor", "db", "modelos", "pensar"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def test_sin_think_no_toca_a_claude(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()

    def explota(_frase):
        raise AssertionError("no debía pensar con Claude")

    monkeypatch.setattr(servidor.pensar, "pensar", explota)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Llamar al banco"}).json()
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["voz"] == "Hoy solo esto: Llamar al banco."
    assert creada["tokens"] is None


def test_con_think_el_paso_minimo_lo_ordena_claude(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    llamadas = []

    def falso_pensar(frase):
        llamadas.append(frase)
        return servidor.pensar.Pensado(
            paso_minimo="Abre la app del banco y busca el teléfono.",
            tokens_entrada=120,
            tokens_salida=14,
            modelo="modelo-de-prueba",
        )

    monkeypatch.setattr(servidor.pensar, "pensar", falso_pensar)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Llamar al banco", "think": True}).json()
    assert llamadas == ["Llamar al banco"]
    assert creada["tarea"]["paso_minimo"] == "Abre la app del banco y busca el teléfono."
    assert creada["voz"] == "Abre la app del banco y busca el teléfono."
    assert creada["tokens"] == {"entrada": 120, "salida": 14, "modelo": "modelo-de-prueba"}
    # Se guarda con el paso de Claude, no con el universal.
    hoy = cliente.get("/hoy").json()
    assert hoy[0]["tarea"]["paso_minimo"] == "Abre la app del banco y busca el teléfono."


def test_con_think_pero_claude_no_puede_sigue_sin_ia(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    monkeypatch.setattr(servidor.pensar, "pensar", lambda _frase: None)
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "Llamar al banco", "think": True}).json()
    assert creada["tarea"]["paso_minimo"] == servidor.PASO_MINIMO_INICIAL
    assert creada["voz"] == "Hoy solo esto: Llamar al banco."
    assert creada["tokens"] is None


def test_la_voz_de_claude_tambien_se_recorta_a_20_palabras(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    servidor = _arrancar_servidor()
    largo = " ".join(f"p{i}" for i in range(30))
    monkeypatch.setattr(
        servidor.pensar,
        "pensar",
        lambda _frase: servidor.pensar.Pensado(largo, 1, 1, "m"),
    )
    cliente = TestClient(servidor.app)

    creada = cliente.post("/mensaje", json={"texto": "x", "think": True}).json()
    assert len(creada["voz"].split()) <= servidor.MAX_PALABRAS_VOZ


def test_sin_clave_pensar_devuelve_none(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sys.modules.pop("pensar", None)
    import pensar

    monkeypatch.setattr(pensar, "RUTA_ENV", tmp_path / ".env")
    assert pensar.pensar("algo") is None


def test_leer_env_tolera_comillas_y_comentarios(tmp_path):
    sys.modules.pop("pensar", None)
    import pensar

    ruta = tmp_path / ".env"
    ruta.write_text('# clave\nANTHROPIC_API_KEY="sk-prueba"\nREMI_CLAUDE_MODELO=modelo-x\n\n')
    valores = pensar._leer_env(ruta)
    assert valores == {"ANTHROPIC_API_KEY": "sk-prueba", "REMI_CLAUDE_MODELO": "modelo-x"}

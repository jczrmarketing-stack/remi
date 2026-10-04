"""GET /libros: la constelación de proyectos para el panel, un resumen por
libro — nunca el cuerpo completo. Contra una bóveda falsa, nunca remi-mente."""
from fastapi.testclient import TestClient

import servidor

CON_ESTADO_Y_CAMINO = """---
titulo: Upvisuals
tema: upvisuals
resumen: Distribución de contenido.
compartible: true
---

## Estado

Quedaste: armando el contrato.
Decisiones: ninguna nueva.
Próximo paso: mandar la propuesta.

## Camino

- [x] Contrato firmado
- [ ] Distribución
"""

SIN_ESTADO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
---

Cuerpo sin ## Estado ni ## Camino todavía.
"""


def _boveda(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(CON_ESTADO_Y_CAMINO)
    (carpeta / "malik.md").write_text(SIN_ESTADO)


def _cliente(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    return TestClient(servidor.app)


def test_libros_devuelve_los_dos_con_estado_y_camino(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.get("/libros")

    assert respuesta.status_code == 200
    por_tema = {l["tema"]: l for l in respuesta.json()}
    assert set(por_tema) == {"upvisuals", "malik"}

    upvisuals = por_tema["upvisuals"]
    assert upvisuals["titulo"] == "Upvisuals"
    assert upvisuals["resumen"] == "Distribución de contenido."
    assert upvisuals["compartible"] is True
    assert upvisuals["quedaste"] == "armando el contrato."
    assert upvisuals["proximo_paso"] == "mandar la propuesta."
    assert upvisuals["hitos"] == [
        {"texto": "Contrato firmado", "hecho": True, "detalle": "", "cerrado_por": None},
        {"texto": "Distribución", "hecho": False, "detalle": "", "cerrado_por": None},
    ]


def test_libro_sin_estado_ni_camino_viene_vacio_no_ausente(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.get("/libros")

    por_tema = {l["tema"]: l for l in respuesta.json()}
    malik = por_tema["malik"]
    assert malik["compartible"] is False
    assert malik["quedaste"] == ""
    assert malik["proximo_paso"] == ""
    assert malik["hitos"] == []
    # Nunca el cuerpo completo del libro.
    assert "Cuerpo sin ## Estado" not in respuesta.text


def test_libros_trae_la_entrega_cercana_y_el_mtime(tmp_path, monkeypatch):
    _boveda(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    import db
    import entregas
    from datetime import datetime, timezone
    from uuid import uuid4

    conexion = db.conectar()
    conexion.execute(
        "INSERT INTO entregas (id, cliente, proyecto_id, fecha, monto, estado, compartible) "
        "VALUES (?, ?, ?, ?, ?, 'camino', 1)",
        (
            str(uuid4()),
            "Alfonso",
            str(entregas._proyecto_id_de_tema("upvisuals")),
            datetime(2026, 10, 18, tzinfo=timezone.utc).isoformat(),
            5000,
        ),
    )
    conexion.commit()
    conexion.close()

    respuesta = cliente.get("/libros")
    por_tema = {l["tema"]: l for l in respuesta.json()}

    upvisuals = por_tema["upvisuals"]
    assert upvisuals["entrega_cercana"]["cliente"] == "Alfonso"
    assert upvisuals["entrega_cercana"]["monto"] == 5000
    assert upvisuals["ultimo_estado_en"]  # un ISO no vacío

    assert por_tema["malik"]["entrega_cercana"] is None


def test_libros_vacio_sin_bitacora(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "no-existe"))
    cliente = TestClient(servidor.app)
    respuesta = cliente.get("/libros")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


# — Encargo H: el camino sale del SOP —

CLIENTE_10_PASOS = """---
titulo: UpVisuals
tema: upvisuals
resumen: Plataforma de Alfonso.
tipo: cliente
fases:
  - nombre: Fase 1
    alcance: Distribución de contenido + seguridad crítica
    monto: 5000
    listo_cuando: Demo aprobada por Alfonso
    estado: camino
---

## Camino

- [x] Intake
- [x] Descubrimiento (5 preguntas)
- [ ] Propuesta por fases
- [ ] Contrato
- [ ] Pago antes de arrancar
- [ ] Entregas medidas
- [ ] Cobro y cierre
- [ ] Producción
- [ ] Entrega y capacitación
- [ ] Mensualidad
"""


def _boveda_upvisuals_10_pasos(tmp_path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "upvisuals.md").write_text(CLIENTE_10_PASOS)


def test_libros_trae_tipo_fases_hito_actual_siguientes_y_paso_remi(tmp_path, monkeypatch):
    _boveda_upvisuals_10_pasos(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.get("/libros")
    (upvisuals,) = respuesta.json()

    assert upvisuals["tipo"] == "cliente"
    assert len(upvisuals["hitos"]) == 10
    assert upvisuals["fases"] == [
        {
            "nombre": "Fase 1",
            "alcance": "Distribución de contenido + seguridad crítica",
            "monto": 5000.0,
            "listo_cuando": "Demo aprobada por Alfonso",
            "estado": "camino",
            "cobrado": 0.0,
        }
    ]
    assert upvisuals["hito_actual"]["texto"] == "Propuesta por fases"
    assert upvisuals["hito_actual"]["detalle"] == (
        "Cada fase con alcance, monto y «listo cuando». Fase 1 pequeña y cobrable."
    )
    assert [h["texto"] for h in upvisuals["siguientes"]] == [
        "Contrato", "Pago antes de arrancar", "Entregas medidas",
    ]
    assert upvisuals["paso_remi"] == "Escribe el borrador en la voz de Juan Camilo."


def test_libro_detalle_trae_estado_completo_y_ultimo_episodio(tmp_path, monkeypatch):
    _boveda_upvisuals_10_pasos(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    # episodios.carpeta_episodios() lee REMI_BOVEDA, no REMI_CONOCIMIENTO —
    # en producción los dos viven bajo la misma bóveda (conocimiento/
    # proyectos y conocimiento/episodios), así que acá también.
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "libros"))
    episodios_dir = tmp_path / "libros" / "episodios"
    episodios_dir.mkdir(parents=True)
    (episodios_dir / "2026-09-20-primero.md").write_text(
        '---\ntitulo: "Primero"\ntema: upvisuals\nresumen: "Viejo."\n---\n\nCuerpo viejo.\n'
    )
    (episodios_dir / "2026-09-30-segundo.md").write_text(
        '---\ntitulo: "Segundo"\ntema: upvisuals\nresumen: "Nuevo."\n---\n\nCuerpo nuevo, no debe salir.\n'
    )

    respuesta = cliente.get("/libros/upvisuals")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["tipo"] == "cliente"
    assert "## Camino" not in cuerpo["estado_completo"]  # estado_completo es solo ## Estado
    assert cuerpo["ultimo_episodio"]["titulo"] == "Segundo"
    assert cuerpo["ultimo_episodio"]["archivo"] == "2026-09-30-segundo.md"
    assert "Cuerpo nuevo" not in respuesta.text  # nunca el cuerpo del episodio


def test_libro_detalle_de_tema_inexistente_es_404(tmp_path, monkeypatch):
    _boveda_upvisuals_10_pasos(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.get("/libros/no-existe")
    assert respuesta.status_code == 404


def test_marcar_hito_cambia_el_archivo_y_commitea_la_boveda(tmp_path, monkeypatch):
    _boveda_upvisuals_10_pasos(tmp_path)
    # boveda_git.raiz() = libros.carpeta().parent: el repo git es la carpeta
    # QUE CONTIENE "libros" (REMI_CONOCIMIENTO), no "libros" en sí misma —
    # igual que en producción, conocimiento/ es la bóveda y proyectos/ vive
    # adentro.
    archivo_libro = tmp_path / "libros" / "upvisuals.md"
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "inicial"], cwd=tmp_path, check=True)

    cliente = _cliente(tmp_path, monkeypatch)

    respuesta = cliente.post("/libros/upvisuals/camino/3", json={"hecho": True})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["hitos"][2] == {"texto": "Propuesta por fases", "hecho": True}
    assert cuerpo["siguiente"] == {"texto": "Contrato", "hecho": False}

    texto = archivo_libro.read_text()
    assert "- [x] Propuesta por fases" in texto

    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert "hito 3" in log.stdout


def test_marcar_hito_fuera_de_rango_es_404(tmp_path, monkeypatch):
    _boveda_upvisuals_10_pasos(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.post("/libros/upvisuals/camino/99", json={"hecho": True})
    assert respuesta.status_code == 404


def test_marcar_hito_de_tema_inexistente_es_404(tmp_path, monkeypatch):
    _boveda_upvisuals_10_pasos(tmp_path)
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.post("/libros/no-existe/camino/1", json={"hecho": True})
    assert respuesta.status_code == 404

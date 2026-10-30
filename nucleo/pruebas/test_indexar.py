"""El índice único (F1.2). Corre sobre una copia de `_archivo/ejemplos/` de la
bóveda más notas escritas aquí, nunca sobre 03_oro/ ni sobre la mente real.
El embedding es falso salvo donde se dice: lo que se prueba es la tubería.
"""
import hashlib
import shutil
from pathlib import Path

import httpx
import pytest

import indexar
import remi_mcp
import vectores
import vida

EJEMPLOS = Path("/Volumes/ORGANIC/boveda/_archivo/ejemplos")
SECRETO = "cuerpoquenuncasale"
_EMBED_REAL = vectores.embed


def _nota(raiz: Path, relativa: str, titulo: str, resumen: str, extra: str = "") -> None:
    ruta = raiz / relativa
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(f"---\ntitulo: \"{titulo}\"\nresumen: \"{resumen}\"\n{extra}---\n\n{SECRETO} agenda de citas\n")


def _embed_falso(texto: str) -> list[float]:
    semilla = hashlib.sha256(texto.encode()).digest()
    return [semilla[i % 32] / 255 for i in range(vectores.DIMENSIONES)]


@pytest.fixture
def mente(tmp_path, monkeypatch):
    if not EJEMPLOS.is_dir():
        pytest.skip("el disco ORGANIC no está montado")
    raiz = tmp_path / "mente"
    (raiz / "mundo" / "fuentes").mkdir(parents=True)
    for ejemplo in EJEMPLOS.glob("*.md"):
        if ejemplo.name != "README.md":
            shutil.copy(ejemplo, raiz / "mundo" / "fuentes" / ejemplo.name)
    _nota(raiz, "aprendido/lecciones/2026-10-01-citas.md", "Lección de citas", "Agendar citas falla sin confirmar.", "ultima_vez: 2026-10-01\n")
    _nota(raiz, "mundo/campo/2026-10-02-citas.md", "Campo de citas", "12 ofertas sobre citas.", "fecha: 2026-10-02\nnivel: T1\n")
    _nota(raiz, "aprendido/decisiones/2026-10-03-citas.md", "Decisión de citas", "Cobrar la cita antes.", "fecha: 2026-10-03\nestatus: decidido\nconfianza: media\n")
    _nota(raiz, "plantillas/decision.md", "Plantilla de citas", "No debe salir.")
    monkeypatch.setattr(vida, "MENTE", raiz)
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "sin-boveda"))
    monkeypatch.setattr(vida, "_boveda", lambda: None)
    monkeypatch.setattr(vectores, "embed", _embed_falso)
    return raiz


def test_una_consulta_cruza_leccion_campo_decision_y_fuente(mente):
    conexion = indexar.conectar()
    indexar.actualizar(conexion)
    # «agendar» y «cita» están en la investigación de ejemplo y en las tres notas.
    tipos = [h.tipo for h in indexar.buscar(conexion, "agendar citas o una cita", n=8)]
    assert {"leccion", "campo", "decision", "fuente"} <= set(tipos)
    assert tipos.count("fuente") <= 3  # los ejemplos no tapan a los otros tipos


def test_preguntar_da_resumen_fecha_estatus_y_confianza_nunca_el_cuerpo(mente):
    salida = remi_mcp.preguntar("citas")
    assert "aprendido/decisiones/2026-10-03-citas.md" in salida
    assert "2026-10-03 · estatus: decidido · confianza: media" in salida
    assert "Cobrar la cita antes." in salida
    assert SECRETO not in salida
    assert "Plantilla" not in salida


def test_lo_que_no_tiene_estatus_dice_sin_dato(mente):
    salida = remi_mcp.preguntar("Lección de citas")
    assert "2026-10-01 · estatus: sin dato · confianza: sin dato" in salida


def test_sin_resumen_toma_el_primer_texto_y_no_el_titulo(mente):
    ruta = mente / "yo" / "metas.md"
    ruta.parent.mkdir()
    ruta.write_text("---\ntipo: yo\n---\n# Qué busca\n- Vender a EE. UU.\n")
    assert "metas: - Vender a EE. UU." in remi_mcp.preguntar("Vender")


def test_una_nota_sin_verificar_lo_dice(mente):
    _nota(mente, "mundo/fuentes/reel.md", "Reel de citas", "Dudoso.", "estatus: hipotesis\nsin_verificar: true\n")
    assert "estatus: sin_verificar" in remi_mcp.preguntar("Reel de citas")


def test_leer_trae_el_cuerpo_solo_por_id(mente):
    remi_mcp.preguntar("citas")
    assert SECRETO in remi_mcp.leer("aprendido/lecciones/2026-10-01-citas.md")
    assert "No hay ninguna nota" in remi_mcp.leer("../../../etc/hosts")


def test_por_hash_solo_recalcula_lo_que_cambio_y_quita_lo_borrado(mente, monkeypatch):
    conexion = indexar.conectar()
    primera = indexar.actualizar(conexion)
    assert primera["cambiadas"] == primera["notas"] == primera["vectores"] > 3

    llamadas = []
    monkeypatch.setattr(vectores, "embed", lambda t: llamadas.append(t) or _embed_falso(t))
    assert indexar.actualizar(conexion) == {"notas": primera["notas"], "cambiadas": 0, "borradas": 0, "vectores": 0}
    assert llamadas == []

    _nota(mente, "aprendido/lecciones/2026-10-01-citas.md", "Lección de citas", "Ahora dice otra cosa.")
    (mente / "mundo/campo/2026-10-02-citas.md").unlink()
    segunda = indexar.actualizar(conexion)
    assert (segunda["cambiadas"], segunda["borradas"], segunda["vectores"]) == (1, 1, 1)
    assert indexar.buscar(conexion, "Campo de citas", n=20)[0].tipo != "campo"


def test_el_indice_se_reconstruye_igual_si_se_borra(mente):
    conexion = indexar.conectar()
    indexar.actualizar(conexion)
    antes = [h.id for h in indexar.buscar(conexion, "citas", n=20)]
    conexion.close()
    indexar.ruta_indice().unlink()
    conexion = indexar.conectar()
    indexar.actualizar(conexion)
    assert [h.id for h in indexar.buscar(conexion, "citas", n=20)] == antes


def test_sin_ollama_responde_por_texto_y_retoma_luego(mente, monkeypatch):
    def caido(_texto):
        raise httpx.ConnectError("sin ollama")

    monkeypatch.setattr(vectores, "embed", caido)
    conexion = indexar.conectar()
    assert indexar.actualizar(conexion)["vectores"] == 0
    assert indexar.buscar(conexion, "Decisión de citas")[0].tipo == "decision"

    monkeypatch.setattr(vectores, "embed", _embed_falso)
    assert indexar.actualizar(conexion)["vectores"] > 3


def test_la_boveda_ausente_no_borra_sus_notas(mente, tmp_path, monkeypatch):
    boveda = tmp_path / "boveda-prueba"
    _nota(boveda, "03_oro/campo/x.md", "Campo en bóveda", "Conteo.")
    _nota(boveda, "memoria/entradas/ejemplo-x.md", "Ejemplo sembrado", "No debe salir.")
    monkeypatch.setattr(vida, "_boveda", lambda: boveda)
    conexion = indexar.conectar()
    indexar.actualizar(conexion)
    hallado = indexar.buscar(conexion, "Campo en bóveda")[0]
    assert (hallado.id, hallado.tipo) == ("boveda/03_oro/campo/x.md", "campo")
    assert not any("ejemplo-x" in h.id for h in indexar.buscar(conexion, "Ejemplo sembrado", n=20))

    monkeypatch.setattr(vida, "_boveda", lambda: None)
    assert indexar.actualizar(conexion)["borradas"] == 0
    assert indexar.buscar(conexion, "Campo en bóveda")[0].id == "boveda/03_oro/campo/x.md"


def test_vectores_de_verdad_encuentran_sin_palabras_en_comun(mente, monkeypatch):
    # Sin simular: Ollama real, si está arriba.
    monkeypatch.setattr(vectores, "embed", _EMBED_REAL)
    try:
        httpx.get(f"{vectores.OLLAMA_BASE}/api/tags", timeout=1.0)
    except httpx.HTTPError:
        pytest.skip("Ollama no está corriendo")
    _nota(mente, "aprendido/lecciones/2026-10-04-perros.md", "Perros y gatos", "Vacunas en el veterinario.")
    conexion = indexar.conectar()
    indexar.actualizar(conexion)
    # La palabra no está en ninguna nota: solo el vector la puede traer.
    assert indexar._por_texto(conexion, "mascotas", 50) == []
    assert "aprendido/lecciones/2026-10-04-perros.md" in [h.id for h in indexar.buscar(conexion, "mascotas", n=3)]

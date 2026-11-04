"""El Vendedor: decide una acción con datos reales, deja borradores, nunca envía y nunca inventa cifras."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

for _var in ("REMI_ESTADO_AGENTES", "REMI_ESTADO_PISOS"):   # la Suite: nunca el estado real
    os.environ.setdefault(_var, tempfile.mkdtemp())
os.environ.setdefault("REMI_MENTE", tempfile.mkdtemp())
os.environ.setdefault("REMI_DB_PATH", str(Path(tempfile.mkdtemp()) / "remi.db"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vendedor  # noqa: E402

HOY = date(2026, 11, 4)
FRENTES = """---
tipo: negocio
---
# Frentes
Regla: los leads no cuentan. Solo clientes. Hoy hace unos US$3.000 al mes; el escalón es US$5.000.

## UpVisuals (Alfonso): lo más cercano a plata
- Fase 1 (US$5.000): Alfonso pagó US$3.000. Falta terminar el trabajo; entrega en ~1 semana (hacia el 9-nov) y ahí cobra el resto (US$2.000).
- Fase 2 (US$3.700, generador de imágenes): después de la Fase 1.

## Fiverr
- Nivel 2. Los clientes llegan muy de vez en cuando.
"""
CRM = """# Abierto en el CRM
## Fiverr
- Fiverr: eltondz (México) pidió FletApp; oferta de $1.700 → paso: Revisar si eltondz respondió · enviada el 22-oct.
## LLC y legal
- Arreglar la LLC → paso: Anotar qué falta
"""


def _mente(crm: bool = True, frentes: str = FRENTES) -> Path:
    m = Path(tempfile.mkdtemp())
    (m / "negocio").mkdir()
    (m / "negocio" / "frentes.md").write_text(frentes, encoding="utf-8")
    if crm:
        (m / "negocio" / "crm.md").write_text(CRM, encoding="utf-8")
    return m


def _db(filas) -> Path:
    ruta = Path(tempfile.mkdtemp()) / "remi.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE entregas (id TEXT, cliente TEXT, proyecto_id TEXT, fecha TEXT, monto REAL, estado TEXT, compartible INTEGER, linea TEXT)")
    for i, (cliente, fecha, monto, estado) in enumerate(filas):
        con.execute("INSERT INTO entregas VALUES (?,?,?,?,?,?,1,'software')", (str(i), cliente, "p", fecha, monto, estado))
    con.commit(); con.close()
    return ruta


def _sin_db() -> Path:
    return Path(tempfile.mkdtemp()) / "no-existe.db"


RESPUESTA = json.dumps({
    "paso": {"titulo": "Dejar listo el cobro de US$2.000 a Alfonso.", "contexto": "Se cobra al entregar la Fase 1.", "accion": "Revisar el mensaje"},
    "seguimiento": [{"cliente": "Alfonso", "paso": "Cobrar el saldo al entregar", "fecha": "2026-11-09"}],
    "borradores": [{"cliente": "Alfonso", "para": "Cobro al entregar la Fase 1", "texto": "Hola Alfonso, queda el saldo de US$2.000. ¿Te paso los datos?\n\nJuan Camilo"}],
    "ultimo": "Dejó listo el cobro a Alfonso"})


def test_reglas_leen_el_saldo_de_frentes():
    saldos = vendedor.saldos_en_frentes(FRENTES, HOY)
    assert saldos == [{"cliente": "Alfonso", "proyecto": "UpVisuals", "fase": "Fase 1", "saldo": 2000, "total": 5000, "fecha": date(2026, 11, 9)}]


def test_por_reglas_prepara_el_cobro_cercano_sin_inventar():
    situacion = vendedor.juntar(HOY, _mente(), _sin_db())
    d = vendedor.por_reglas(situacion, HOY)
    assert "US$2.000" in d["paso"]["titulo"] and "Alfonso" in d["paso"]["titulo"] and "en 5 días" in d["paso"]["contexto"]
    texto = d["borradores"][0]["texto"]
    assert "Fase 1 de UpVisuals" in texto and "US$2.000" in texto and "US$5.000" in texto and texto.rstrip().endswith("Juan Camilo")
    assert not any(p in texto.lower() for p in ("pero", "lamentablemente", "cobro", "no puedo"))
    assert d["ultimo"] == "Dejó listo el cobro a Alfonso" and any(s["cliente"] == "Fiverr: eltondz" for s in d["seguimiento"])
    assert not any("LLC" in s["cliente"] for s in d["seguimiento"])


def test_las_entregas_de_remi_mandan_sobre_frentes():
    db = _db([("Alfonso", "2026-10-01", 3000, "pagada"), ("Beatriz", "2026-11-06T00:00:00+00:00", 800, "camino")])
    d = vendedor.por_reglas(vendedor.juntar(HOY, _mente(), db), HOY)
    assert "Beatriz" in d["paso"]["titulo"] and "US$800" in d["paso"]["titulo"]
    assert [s["cliente"] for s in d["seguimiento"]][0] == "Beatriz"


def test_sin_saldo_cercano_va_al_crm_y_sin_nada_no_inventa():
    lejos = FRENTES.replace("9-nov", "20-dic")
    d = vendedor.por_reglas(vendedor.juntar(HOY, _mente(frentes=lejos), _sin_db()), HOY)
    assert d["paso"]["titulo"].startswith("Revisar si eltondz") and d["borradores"] == []
    vacio = vendedor.por_reglas(vendedor.juntar(HOY, _mente(crm=False, frentes="# nada"), _sin_db()), HOY)
    assert vacio["borradores"] == [] and vacio["seguimiento"] == [] and "No encontré" in vacio["paso"]["contexto"]


def test_rechaza_cifras_que_no_estan_en_los_datos():
    situacion = vendedor.juntar(HOY, _mente(), _sin_db())
    assert vendedor.leer_respuesta(f"```json\n{RESPUESTA}\n```", situacion)["borradores"][0]["cliente"] == "Alfonso"
    try:
        vendedor.leer_respuesta(RESPUESTA.replace("saldo de US$2.000", "saldo de US$2.500"), situacion)
        raise AssertionError("debió rechazar US$2.500")
    except ValueError as exc:
        assert "2500" in str(exc)


def test_corrida_con_ia_publica_guarda_borrador_y_reporta():
    mente, publicados = _mente(), []
    texto = vendedor.correr(HOY, claude=lambda s, m: RESPUESTA, mente=mente, db=_sin_db(),
                            publicar=lambda piso, agente, paso, entra: publicados.append((piso, agente, paso, entra)))
    piso, agente, paso, entra = publicados[0]
    assert (piso, agente) == ("ventas", "vendedor") and paso["accion"] == "Revisar el mensaje"
    assert [e["titulo"] for e in entra] == ["Seguimiento", "Borradores listos"] and "Entregas y cobros" not in [e["titulo"] for e in entra]
    borrador = (mente / "negocio" / "borradores" / "2026-11-04-alfonso.md").read_text(encoding="utf-8")
    assert "estado: sin enviar" in borrador and "autor: vendedor (IA)" in borrador and "US$2.000" in borrador and "IA" in texto
    estado = json.loads((Path(os.environ["REMI_ESTADO_AGENTES"]) / "vendedor.json").read_text(encoding="utf-8"))
    assert estado["estado"] == "durmiendo" and estado["ultimo"] == "Dejó listo el cobro a Alfonso"


def test_no_pisa_un_borrador_que_jc_ya_edito():
    mente = _mente()
    ruta = vendedor.ruta_borrador(HOY, "Alfonso", mente)
    ruta.parent.mkdir(parents=True)
    ruta.write_text("editado por JC", encoding="utf-8")
    vendedor.correr(HOY, claude=lambda s, m: RESPUESTA, mente=mente, db=_sin_db(), publicar=lambda *a, **k: None)
    assert ruta.read_text(encoding="utf-8") == "editado por JC"


def test_si_la_ia_falla_sale_por_reglas_y_avisa_una_vez():
    avisos, mente, publicados = [], _mente(), []
    def falla(s, m):
        raise RuntimeError("límite de uso")
    vendedor.correr(HOY, claude=falla, avisar=avisos.append, mente=mente, db=_sin_db(),
                    publicar=lambda piso, agente, paso, entra: publicados.append(paso))
    assert len(avisos) == 1 and "versión por reglas" in avisos[0] and "US$2.000" in publicados[0]["titulo"]
    assert "autor: vendedor (reglas)" in (mente / "negocio" / "borradores" / "2026-11-04-alfonso.md").read_text(encoding="utf-8")


def test_probar_no_escribe_nada():
    mente, avisos = _mente(), []
    antes = (Path(os.environ["REMI_ESTADO_AGENTES"]) / "vendedor.json").read_text(encoding="utf-8") if (Path(os.environ["REMI_ESTADO_AGENTES"]) / "vendedor.json").exists() else None
    texto = vendedor.correr(HOY, probar=True, claude=lambda s, m: (_ for _ in ()).throw(RuntimeError("x")), avisar=avisos.append,
                            mente=mente, db=_sin_db(), publicar=lambda *a, **k: (_ for _ in ()).throw(AssertionError("publicó")))
    assert "prueba, no escribió nada" in texto and "Hola Alfonso" in texto and avisos == []
    assert not (mente / "negocio" / "borradores").exists()
    despues = (Path(os.environ["REMI_ESTADO_AGENTES"]) / "vendedor.json").read_text(encoding="utf-8") if (Path(os.environ["REMI_ESTADO_AGENTES"]) / "vendedor.json").exists() else None
    assert antes == despues


def test_la_cli_va_sin_llaves_de_api_y_sin_herramientas():
    visto = {}
    class R:
        stdout = json.dumps({"result": "{}"})
    def correr(comando, **kw):
        visto.update(comando=comando, env=kw["env"]); return R()
    os.environ["ANTHROPIC_API_KEY"] = "no"
    try:
        vendedor.llamar_claude("s", "m", correr=correr, binario="/x/claude")
    finally:
        del os.environ["ANTHROPIC_API_KEY"]
    assert "ANTHROPIC_API_KEY" not in visto["env"] and visto["comando"][visto["comando"].index("--tools") + 1] == ""


def test_publicar_piso_real_en_carpeta_temporal():
    import agentes_estado
    vendedor.correr(HOY, claude=lambda s, m: RESPUESTA, mente=_mente(), db=_sin_db())
    piso = agentes_estado.leer_piso("ventas")
    assert piso["por"]["paso"] == "vendedor" and "Borradores listos" in piso["entra"]
    assert str(agentes_estado.PISOS_RAIZ).startswith(tempfile.gettempdir())

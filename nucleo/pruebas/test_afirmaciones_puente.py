"""El puente a las afirmaciones: solo lee, y sin bóveda o sin base no rompe `preguntar`."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))


def _boveda() -> Path | None:
    for c in (os.environ.get("BOVEDA_RAIZ"), "/Volumes/ORGANIC/boveda"):
        if c and (Path(c) / "afirmaciones.py").exists():
            return Path(c)
    return None


def _preparar(d: Path):
    """Mente falsa con dos notas que chocan, y la db armada con el módulo real de la bóveda."""
    boveda = _boveda()
    sys.path.insert(0, str(boveda))
    import afirmaciones as af
    for nombre, fecha, precio in (("vieja", "2026-09-20", "$25"), ("nueva", "2026-10-25", "$35")):
        p = d / "mundo" / "fuentes" / "web" / f"{nombre}.md"; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f'---\nfuente: "web"\nurl: "https://x.com/{nombre}"\nfecha_ingesta: {fecha}\n---\n# t\n<!-- enriquecido:inicio -->\n\n## Resumen\n\n'
                     f"- El plan Pro de Supabase cuesta {precio} por mes con base de datos incluida («c»)\n\n<!-- enriquecido:fin -->\n", encoding="utf-8")
    con = af.abrir(d / "afirmaciones.db"); af.sincronizar(con, d, date(2026, 11, 2)); af.detectar_contradicciones(con, date(2026, 11, 2)); con.close()


def test_estado_y_contradice_leen_la_db_de_la_bobeda():
    if _boveda() is None:
        return  # sin bóveda montada no hay nada que probar aquí
    import afirmaciones_puente as pu
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); _preparar(d)
        e = pu.estado_de("mundo/fuentes/web/vieja.md", mente=d)
        assert e.startswith("afirmaciones: ") and "contradicha" in e
        assert "vigente" in pu.estado_de("mundo/fuentes/web/nueva.md", mente=d) or "por verificar" in pu.estado_de("mundo/fuentes/web/nueva.md", mente=d)
        r = pu.contradice("El plan Pro de Supabase cuesta $50 por mes con base de datos incluida", mente=d)
        assert r.startswith("Choca con") and "$35" in r
        assert "Nada vigente" in pu.contradice("Receta de arepas con queso y mantequilla dorada", mente=d)


def test_sin_base_o_sin_boveda_no_rompe():
    import afirmaciones_puente as pu
    with tempfile.TemporaryDirectory() as t:
        assert pu.estado_de("x.md", mente=Path(t)) == ""
        assert "Todavía no hay" in pu.contradice("algo", mente=Path(t)) or "no está montada" in pu.contradice("algo", mente=Path(t))
    vieja = os.environ.get("BOVEDA_RAIZ")
    os.environ["BOVEDA_RAIZ"] = "/no/existe"
    try:
        orig, pu._raiz_boveda = pu._raiz_boveda, lambda: None
        assert pu.estado_de("x.md", mente=Path("/no")) == "" and "no está montada" in pu.contradice("algo", mente=Path("/no"))
        pu._raiz_boveda = orig
    finally:
        if vieja is None: os.environ.pop("BOVEDA_RAIZ", None)
        else: os.environ["BOVEDA_RAIZ"] = vieja


if __name__ == "__main__":
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith("test_") and callable(f):
            try:
                f(); print("ok  ", nombre)
            except Exception as exc:  # noqa: BLE001
                import traceback; fallos += 1; print("FALLA", nombre, "→", type(exc).__name__, exc); traceback.print_exc()
    sys.exit(1 if fallos else 0)

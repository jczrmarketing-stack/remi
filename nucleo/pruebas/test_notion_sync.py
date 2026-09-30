"""Ida y vuelta con Notion (Fase 4) — contra un Notion falso, nunca la API
real. Cubre: se salta sin token, empuja un proyecto/entrega nuevo, trae
«Próxima acción» y el estado de una entrega desde Notion, y el conflicto
(cambió en los dos lados) queda anotado en la bitácora."""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import notion
import notion_sync


class NotionFalso:
    """Mismos métodos que `notion.Notion`, todo en memoria."""

    def __init__(self) -> None:
        self.bases: dict[str, str] = {}
        self.paginas: dict[str, dict] = {}
        self._contador = 0

    def _id(self, prefijo: str) -> str:
        self._contador += 1
        return f"{prefijo}-{self._contador}"

    def buscar_base(self, padre_id, nombre):
        return self.bases.get(nombre)

    def crear_base(self, padre_id, nombre, propiedades):
        base_id = self._id("base")
        self.bases[nombre] = base_id
        return base_id

    def consultar_base(self, database_id):
        return [p for p in self.paginas.values() if p["_base"] == database_id]

    def crear_pagina(self, database_id, propiedades):
        pagina_id = self._id("pagina")
        self.paginas[pagina_id] = {
            "id": pagina_id,
            "_base": database_id,
            "properties": propiedades,
            "last_edited_time": _iso(datetime.now(timezone.utc)),
        }
        return pagina_id

    def actualizar_pagina(self, pagina_id, propiedades):
        self.paginas[pagina_id]["properties"].update(propiedades)

    def obtener_pagina(self, pagina_id):
        return self.paginas[pagina_id]

    def tocar_a_mano(self, pagina_id, propiedades, hace: timedelta = timedelta(minutes=1)):
        """Simula una edición humana en Notion: cambia una propiedad y el
        `last_edited_time`, más reciente que cualquier archivo recién escrito."""
        self.paginas[pagina_id]["properties"].update(propiedades)
        self.paginas[pagina_id]["last_edited_time"] = _iso(datetime.now(timezone.utc) + hace)


def _iso(momento: datetime) -> str:
    return momento.isoformat().replace("+00:00", "Z")


def _git(carpeta, *args):
    return subprocess.run(["git", "-C", str(carpeta), *args], capture_output=True, text=True, check=True)


def _boveda(tmp_path, monkeypatch):
    boveda = tmp_path / "boveda"
    (boveda / "proyectos").mkdir(parents=True)
    _git(boveda, "init", "-q")
    _git(boveda, "config", "user.email", "remi@local")
    _git(boveda, "config", "user.name", "Remi")
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(boveda / "proyectos"))
    return boveda


def _libro(boveda, nombre, tema, *, compartible=True, proximo="cinco minutos"):
    archivo = boveda / "proyectos" / nombre
    archivo.write_text(
        "---\n"
        f"titulo: {tema.title()}\n"
        f"tema: {tema}\n"
        "resumen: Un proyecto de prueba.\n"
        f"compartible: {'true' if compartible else 'false'}\n"
        "---\n\n"
        "Cuerpo del libro.\n\n"
        "## Estado\n\n"
        "Quedaste: en el primer paso.\n"
        "Decisiones: ninguna nueva.\n"
        f"Próximo paso: {proximo}\n"
    )
    _git(boveda, "add", "-A")
    _git(boveda, "commit", "-q", "-m", f"libro {tema}")
    return archivo


def _configurar(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTION_TOKEN", "secret_de_prueba")
    monkeypatch.setenv("NOTION_PAGINA_ID", "pagina-remi")


def test_sin_token_se_salta_y_no_rompe(monkeypatch, tmp_path):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_PAGINA_ID", raising=False)
    monkeypatch.setattr(notion, "RUTA_ENV", tmp_path / "sin.env")
    resumen = notion_sync.sincronizar()
    assert resumen.saltado is True
    assert resumen.motivo == "sin NOTION_TOKEN"


def test_libro_no_compartible_no_se_toca(monkeypatch, tmp_path):
    _configurar(monkeypatch, tmp_path)
    boveda = _boveda(tmp_path, monkeypatch)
    _libro(boveda, "privado.md", "privado", compartible=False)
    falso = NotionFalso()

    resumen = notion_sync.sincronizar(cliente=falso)

    assert resumen.proyectos_creados == 0
    assert falso.paginas == {}


def test_crea_la_pagina_de_un_proyecto_nuevo(monkeypatch, tmp_path):
    _configurar(monkeypatch, tmp_path)
    boveda = _boveda(tmp_path, monkeypatch)
    _libro(boveda, "upvisuals.md", "upvisuals", proximo="mandar la propuesta")
    falso = NotionFalso()

    resumen = notion_sync.sincronizar(cliente=falso)

    assert resumen.proyectos_creados == 1
    (pagina,) = falso.paginas.values()
    assert notion.leer_titulo(pagina["properties"]["Título"]) == "Upvisuals"
    assert notion.leer_texto(pagina["properties"]["Próxima acción"]) == "mandar la propuesta"
    assert (tmp_path / "boveda" / ".notion-estado.json").exists()


def test_solo_de_ida_no_lee_ni_anota_conflicto_por_defecto(monkeypatch, tmp_path):
    """docs/ROBUSTEZ.md: sin NOTION_VUELTA=1, sincronizar() empuja lo local y
    nunca lee la página de Notion de vuelta — un cambio hecho a mano en
    Notion no pisa el libro, y un conflicto real tampoco se anota."""
    _configurar(monkeypatch, tmp_path)
    monkeypatch.delenv("NOTION_VUELTA", raising=False)
    boveda = _boveda(tmp_path, monkeypatch)
    archivo = _libro(boveda, "upvisuals.md", "upvisuals", proximo="mandar la propuesta")
    falso = NotionFalso()
    notion_sync.sincronizar(cliente=falso)
    (pagina_id,) = falso.paginas.keys()

    # Cambia en Notion Y localmente: con la vuelta prendida esto sería un conflicto.
    falso.tocar_a_mano(pagina_id, {"Próxima acción": notion.prop_texto("desde Notion")}, hace=timedelta(minutes=5))
    archivo.write_text(archivo.read_text().replace("mandar la propuesta", "desde el libro"))
    _git(boveda, "add", "-A")
    _git(boveda, "commit", "-q", "-m", "cambio local")

    resumen = notion_sync.sincronizar(cliente=falso)

    assert resumen.conflictos == 0
    assert resumen.proyectos_actualizados == 1
    assert "Próximo paso: desde el libro" in archivo.read_text()  # lo local manda, Notion no vuelve
    assert not (boveda / "bitacora.md").exists()
    pagina = falso.obtener_pagina(pagina_id)
    assert notion.leer_texto(pagina["properties"]["Próxima acción"]) == "desde el libro"  # se empujó


def test_solo_de_ida_no_lee_el_estado_de_la_entrega_por_defecto(monkeypatch, tmp_path):
    _configurar(monkeypatch, tmp_path)
    monkeypatch.delenv("NOTION_VUELTA", raising=False)
    boveda = _boveda(tmp_path, monkeypatch)
    _libro(boveda, "upvisuals.md", "upvisuals")

    import db
    import entregas
    from modelos import Entrega

    conexion = db.conectar()
    entrega = Entrega(
        id=uuid4(),
        cliente="Alfonso",
        proyecto_id=notion_sync._id_de_proyecto("upvisuals"),
        fecha=datetime.now(timezone.utc),
        monto=5000.0,
        estado="camino",
        compartible=True,
    )
    entregas.crear_entrega(conexion, entrega)
    conexion.close()

    falso = NotionFalso()
    notion_sync.sincronizar(cliente=falso)
    paginas_entrega = [
        p for p in falso.paginas.values() if notion.leer_titulo(p["properties"].get("Cliente")) == "Alfonso"
    ]
    pagina_id = paginas_entrega[0]["id"]

    falso.tocar_a_mano(pagina_id, {"Estado": notion.prop_seleccion("pagada")})
    resumen = notion_sync.sincronizar(cliente=falso)

    assert resumen.conflictos == 0
    conexion = db.conectar()
    igual = entregas.leer_entrega(conexion, entrega.id)
    conexion.close()
    assert igual is not None
    assert igual.estado == "camino"  # no volvió de Notion


def test_proxima_accion_editada_en_notion_vuelve_al_libro(monkeypatch, tmp_path):
    _configurar(monkeypatch, tmp_path)
    monkeypatch.setenv("NOTION_VUELTA", "1")
    boveda = _boveda(tmp_path, monkeypatch)
    archivo = _libro(boveda, "upvisuals.md", "upvisuals", proximo="mandar la propuesta")
    falso = NotionFalso()
    notion_sync.sincronizar(cliente=falso)
    (pagina_id,) = falso.paginas.keys()

    falso.tocar_a_mano(pagina_id, {"Próxima acción": notion.prop_texto("llamar a Alfonso")})
    antes = _git(boveda, "log", "--oneline").stdout

    resumen = notion_sync.sincronizar(cliente=falso)

    assert resumen.conflictos == 0
    assert "Próximo paso: llamar a Alfonso" in archivo.read_text()
    assert "Quedaste: en el primer paso." in archivo.read_text()  # la prosa no se tocó
    despues = _git(boveda, "log", "--oneline").stdout
    assert despues != antes  # quedó un commit real del cambio


def test_conflicto_lo_anota_en_la_bitacora_y_gana_el_mas_reciente(monkeypatch, tmp_path):
    _configurar(monkeypatch, tmp_path)
    monkeypatch.setenv("NOTION_VUELTA", "1")
    boveda = _boveda(tmp_path, monkeypatch)
    archivo = _libro(boveda, "upvisuals.md", "upvisuals", proximo="mandar la propuesta")
    falso = NotionFalso()
    notion_sync.sincronizar(cliente=falso)
    (pagina_id,) = falso.paginas.keys()

    # Cambia en Notion (más reciente, +1 min) y también localmente.
    falso.tocar_a_mano(pagina_id, {"Próxima acción": notion.prop_texto("desde Notion")}, hace=timedelta(minutes=5))
    archivo.write_text(archivo.read_text().replace("mandar la propuesta", "desde el libro"))
    _git(boveda, "add", "-A")
    _git(boveda, "commit", "-q", "-m", "cambio local")

    resumen = notion_sync.sincronizar(cliente=falso)

    assert resumen.conflictos == 1
    bitacora = (boveda / "bitacora.md").read_text()
    assert "conflicto" in bitacora.lower() or "Próxima acción" in bitacora
    assert "ganó Notion" in bitacora
    assert "Próximo paso: desde Notion" in archivo.read_text()


def test_entrega_compartible_se_crea_y_el_estado_vuelve_desde_notion(monkeypatch, tmp_path):
    _configurar(monkeypatch, tmp_path)
    monkeypatch.setenv("NOTION_VUELTA", "1")
    boveda = _boveda(tmp_path, monkeypatch)
    _libro(boveda, "upvisuals.md", "upvisuals")

    import db
    import entregas
    from modelos import Entrega

    conexion = db.conectar()
    entrega = Entrega(
        id=uuid4(),
        cliente="Alfonso",
        proyecto_id=notion_sync._id_de_proyecto("upvisuals"),
        fecha=datetime.now(timezone.utc),
        monto=5000.0,
        estado="camino",
        compartible=True,
    )
    entregas.crear_entrega(conexion, entrega)
    conexion.close()

    falso = NotionFalso()
    resumen = notion_sync.sincronizar(cliente=falso)
    assert resumen.entregas_creadas == 1
    paginas_entrega = [
        p for p in falso.paginas.values() if notion.leer_titulo(p["properties"].get("Cliente")) == "Alfonso"
    ]
    assert len(paginas_entrega) == 1
    pagina_id = paginas_entrega[0]["id"]

    falso.tocar_a_mano(pagina_id, {"Estado": notion.prop_seleccion("pagada")})
    notion_sync.sincronizar(cliente=falso)

    conexion = db.conectar()
    actualizada = entregas.leer_entrega(conexion, entrega.id)
    conexion.close()
    assert actualizada is not None
    assert actualizada.estado == "pagada"

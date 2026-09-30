"""Cliente y lectura/escritura de propiedades de Notion — sin pegarle a la
API real (Fase 4)."""
from datetime import date

import notion


def test_sin_env_ni_variable_no_hay_token(monkeypatch, tmp_path):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.setattr(notion, "RUTA_ENV", tmp_path / "no-existe.env")
    assert notion.token() is None


def test_variable_de_entorno_gana_sobre_el_env(monkeypatch, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text('NOTION_TOKEN="del-archivo"\n')
    monkeypatch.setattr(notion, "RUTA_ENV", archivo)
    monkeypatch.setenv("NOTION_TOKEN", "de-la-variable")
    assert notion.token() == "de-la-variable"


def test_token_sale_del_env_si_no_hay_variable(monkeypatch, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text("NOTION_TOKEN=secret_abc\nNOTION_PAGINA_ID=pagina-1\n# comentario\n")
    monkeypatch.setattr(notion, "RUTA_ENV", archivo)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_PAGINA_ID", raising=False)
    assert notion.token() == "secret_abc"
    assert notion.pagina_id() == "pagina-1"


def test_ida_y_vuelta_de_las_propiedades():
    assert notion.leer_titulo(notion.prop_titulo("BeaM")) == "BeaM"
    assert notion.leer_texto(notion.prop_texto("cinco minutos")) == "cinco minutos"
    assert notion.leer_fecha(notion.prop_fecha(date(2026, 10, 18))) == "2026-10-18"
    assert notion.leer_fecha(notion.prop_fecha(None)) is None
    assert notion.leer_numero(notion.prop_numero(2400.0)) == 2400.0
    assert notion.leer_seleccion(notion.prop_seleccion("camino")) == "camino"
    assert notion.leer_seleccion(notion.prop_seleccion(None)) is None


def test_leer_con_propiedad_vacia_no_explota():
    assert notion.leer_titulo(None) == ""
    assert notion.leer_texto({"rich_text": []}) == ""
    assert notion.leer_fecha({"date": None}) is None

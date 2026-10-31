import json

import pytest

import etiquetar as e
import telegram
import vida


def _nota(boveda, carpeta, id_, fuente="instagram", titulo="Una nota", dominio="negocio", modelo="negocio"):
    ruta = boveda / carpeta / f"{id_}.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        f'---\nid: "{id_}"\nfuente: "{fuente}"\nurl: "https://x.co/{id_}"\ntitulo: "{titulo}"\n'
        f'dominio: "{dominio}"\ndominio_modelo: "{modelo}"\n---\n\ncuerpo\n',
        encoding="utf-8",
    )


@pytest.fixture
def boveda(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path))
    monkeypatch.setattr(vida, "MENTE", tmp_path)  # las notas viven en la mente (F1.4c)
    return tmp_path


class Transporte:
    def __init__(self):
        self.mensajes, self.botones, self.respondidos = [], [], []

    def enviar_mensaje(self, chat_id, texto):
        self.mensajes.append(texto)

    def enviar_botones(self, chat_id, texto, botones):
        self.botones.append((texto, botones))

    def responder_boton(self, boton_id):
        self.respondidos.append(boton_id)


def test_solo_salen_notas_de_fuente_publica(boveda):
    _nota(boveda, "mundo/fuentes/instagram", "a")
    _nota(boveda, "mundo/fuentes/instagram", "privada", fuente="milo")
    _nota(boveda, "03_oro/decisiones", "rumbo", fuente="rumbo")
    _nota(boveda, "03_oro/inteligencia", "informe", fuente="youtube")
    _nota(boveda, "mundo/fuentes/instagram", "ejemplo-pasos", fuente="youtube")
    assert [n["id"] for n in e.notas(boveda)] == ["a"]


def test_nota_sin_verificar_no_sale_al_telefono(boveda):
    _nota(boveda, "mundo/fuentes/instagram", "a")
    _nota(boveda, "mundo/fuentes/instagram", "b")
    ruta = boveda / "mundo/fuentes/instagram/b.md"
    ruta.write_text(ruta.read_text(encoding="utf-8").replace('id: "b"', 'id: "b"\nsin_verificar: true'), encoding="utf-8")
    assert [n["id"] for n in e.notas(boveda)] == ["a"]
    assert e.manejar_boton("et:negocio:b") is None


def test_el_mensaje_es_ciego_y_lo_privado_va_solo_como_link(boveda):
    _nota(boveda, "mundo/fuentes/instagram", "a", titulo="Cómo cobrar mejor", dominio="crecimiento", modelo="decisiones")
    texto, botones = e.manejar_comando("/etiquetar")
    assert "cobrar" not in texto and "https://x.co/a" in texto
    assert "crecimiento" not in texto and "decisiones" not in texto
    assert all(len(b["callback_data"].encode()) <= 64 for fila in botones for b in fila)


def test_etiquetar_guarda_y_al_final_compara_con_reglas_y_modelo(boveda):
    _nota(boveda, "mundo/fuentes/instagram", "a", dominio="negocio", modelo="contenido")
    _nota(boveda, "mundo/fuentes/instagram", "b", dominio="negocio", modelo="ai-tools")
    primera = e.notas(boveda)[0]["id"]
    texto, botones = e.manejar_boton(f"et:{'negocio' if primera == 'a' else 'ai-tools'}:{primera}")
    assert botones is not None
    segunda = "b" if primera == "a" else "a"
    texto, botones = e.manejar_boton(f"et:{'negocio' if segunda == 'a' else 'ai-tools'}:{segunda}")
    assert botones is None
    assert json.loads((boveda / "_sistema/etiquetas.json").read_text())["a"] == "negocio"
    assert "reglas coinciden contigo en 1" in texto and "modelo en 1" in texto


def test_pausar_no_deja_rastro_y_no_se_no_cuenta(boveda):
    _nota(boveda, "mundo/fuentes/instagram", "a")
    e.manejar_boton("et:pausa:a")
    assert not (boveda / "_sistema/etiquetas.json").exists()
    assert "Aún no hay notas" in e.manejar_boton("et:no_se:a")[0]


def test_boton_de_nota_inexistente_o_comando_ajeno_se_ignora(boveda):
    assert e.manejar_boton("et:negocio:no-existe") is None
    assert e.manejar_boton("otra-cosa") is None
    assert e.manejar_comando("hola") is None


def test_telegram_solo_acepta_botones_del_chat_configurado(boveda, monkeypatch):
    _nota(boveda, "mundo/fuentes/instagram", "a")
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "1")
    t = Transporte()
    consulta = {"id": "q", "data": "et:negocio:a", "message": {"chat": {"id": 2}}}
    telegram._manejar_actualizacion(t, {"update_id": 1, "callback_query": consulta})
    assert not t.respondidos and not (boveda / "_sistema/etiquetas.json").exists()
    consulta["message"]["chat"]["id"] = 1
    telegram._manejar_actualizacion(t, {"update_id": 2, "callback_query": consulta})
    assert t.respondidos == ["q"] and (boveda / "_sistema/etiquetas.json").exists()
    assert t.mensajes


def test_telegram_atiende_el_comando(boveda, monkeypatch):
    _nota(boveda, "mundo/fuentes/instagram", "a")
    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "1")
    t = Transporte()
    telegram._manejar_actualizacion(t, {"update_id": 1, "message": {"chat": {"id": 1}, "text": "/etiquetar"}})
    assert len(t.botones) == 1 and t.botones[0][0].startswith("1 de 1")

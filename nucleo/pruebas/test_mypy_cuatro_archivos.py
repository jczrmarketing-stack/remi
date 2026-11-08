"""Pedido mypy del núcleo: telegram, noche, vida y catalogo_puente quedan sin errores de tipo,
y el comportamiento de las líneas tocadas no cambia."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import catalogo_puente as cp
import telegram
import vida

NUCLEO = Path(__file__).resolve().parent.parent
ARCHIVOS = ["telegram.py", "noche.py", "vida.py", "catalogo_puente.py"]


def test_mypy_no_marca_errores_en_los_cuatro_archivos():
    r = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml", *ARCHIVOS],
        cwd=NUCLEO, capture_output=True, text=True, timeout=500,
    )
    errores = [l for l in r.stdout.splitlines() if any(l.startswith(a + ":") for a in ARCHIVOS) and ": error:" in l]
    assert errores == [], "\n".join(errores)


# — telegram —

class _T:
    def __init__(self) -> None:
        self.enviados: list[tuple[object, str]] = []

    def enviar_mensaje(self, chat_id, texto):
        self.enviados.append((chat_id, texto))


def test_callback_query_va_a_manejar_boton_y_no_procesa_mensaje(monkeypatch):
    llamadas = []
    monkeypatch.setattr(telegram, "_manejar_boton", lambda t, c: llamadas.append(c))
    t = _T()
    cb = dict(id="9", data="x", message=dict(chat=dict(id=5)))
    telegram._manejar_actualizacion(t, dict(callback_query=cb, message=dict(chat=dict(id=5), text="hola")))
    assert llamadas == [cb] and t.enviados == []


def test_p_responde_con_consulta_manejar_comando(monkeypatch):
    import consulta
    import etiquetar

    monkeypatch.setattr(telegram, "chat_id_configurado", lambda: "5")
    monkeypatch.setattr(etiquetar, "manejar_comando", lambda texto: None)
    monkeypatch.setattr(consulta, "manejar_comando", lambda texto: "resp:" + texto)
    t = _T()
    telegram._manejar_actualizacion(t, dict(message=dict(chat=dict(id=5), text="/p qué decidí")))
    assert t.enviados == [(5, "resp:/p qué decidí")]


# — noche —

def test_cerrar_f13_mueve_solo_las_confirmadas(tmp_path, monkeypatch):
    import noche

    (tmp_path / "bandeja").mkdir()
    (tmp_path / "bandeja" / "por-confirmar.md").write_text("- [x] uno\n- [ ] dos\n- [x] tres\n", encoding="utf-8")
    monkeypatch.setattr(vida, "MENTE", tmp_path)
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)
    monkeypatch.setattr("metricas.texto_uso", lambda d: "uso")
    salida = noche.cerrar_f13()
    assert salida["confirmadas"] == 2
    assert (tmp_path / "yo" / "confirmado.md").read_text(encoding="utf-8").endswith("- uno\n- tres\n")
    assert (tmp_path / "bandeja" / "por-confirmar.md").read_text(encoding="utf-8") == "- [ ] dos\n"


# — vida —

@pytest.mark.parametrize("tipo", ["leccion", "decision", "investigacion", "resultado"])
def test_anotar_escribe_en_la_carpeta_de_su_tipo(tmp_path, monkeypatch, tipo):
    monkeypatch.setattr(vida, "MENTE", tmp_path)
    monkeypatch.setenv("REMI_HOY", "2026-10-30")
    destino = vida.TIPOS_CON_DESTINO[tipo]
    assert destino is not None
    texto = "Probé algo https://ejemplo.com/a" if tipo == "investigacion" else "Probé algo"
    vida.anotar(texto, tipo)
    assert list((tmp_path / destino).glob("*.md"))


@pytest.mark.parametrize("tipo,archivo", [("hipotesis", "bandeja.md"), ("hecho_sobre_mi", "por-confirmar.md")])
def test_anotar_hipotesis_y_hecho_sobre_mi_van_a_la_bandeja(tmp_path, monkeypatch, tipo, archivo):
    monkeypatch.setattr(vida, "MENTE", tmp_path)
    monkeypatch.setenv("REMI_HOY", "2026-10-30")
    vida.anotar("algo dicho", tipo)
    assert "algo dicho" in (tmp_path / "bandeja" / archivo).read_text(encoding="utf-8")


# — catalogo_puente —

MENSAJE = "No encuentro la bóveda ahora: no puedo leer el video."


def _no_correr(*a, **k):
    pytest.fail("no debía correr")


def test_leer_video_sin_raiz_dice_que_no_encuentra_la_boveda(monkeypatch):
    monkeypatch.setattr(cp.afirmaciones_puente, "_raiz_boveda", lambda: None)
    assert cp.leer_video("aaaaaaaaaaa", correr=_no_correr) == MENSAJE


def test_leer_video_con_raiz_sin_python_dice_lo_mismo(tmp_path):
    assert cp.leer_video("aaaaaaaaaaa", correr=_no_correr, raiz=tmp_path) == MENSAJE

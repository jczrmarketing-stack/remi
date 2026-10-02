"""GET/PUT /config/conexiones y POST .../probar: nunca por el túnel."""
from fastapi.testclient import TestClient

import conexiones
import servidor


def _cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(conexiones, "RUTA_ENV", tmp_path / ".env")
    conexiones._ULTIMA_PRUEBA.clear()
    return TestClient(servidor.app)


def test_get_conexiones_sin_nada_puesto(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.get("/config/conexiones")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == conexiones.LISTA_BLANCA
    assert all(c["puesta"] is False for c in cuerpo.values())


def test_put_guarda_y_el_valor_nunca_vuelve_completo(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.put("/config/conexiones/GROQ_API_KEY", json={"valor": "gsk-secreta-123456"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["puesta"] is True
    assert cuerpo["termina_en"] == "3456"
    assert "gsk-secreta-123456" not in respuesta.text


def test_put_nombre_fuera_de_lista_es_400(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.put("/config/conexiones/AWS_SECRET_ACCESS_KEY", json={"valor": "x"})
    assert respuesta.status_code == 400


def test_probar_nombre_fuera_de_lista_es_400(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.post("/config/conexiones/AWS_SECRET_ACCESS_KEY/probar")
    assert respuesta.status_code == 400


def test_put_con_cabecera_cf_es_403(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.put(
        "/config/conexiones/GROQ_API_KEY",
        json={"valor": "gsk-x"},
        headers={"Cf-Connecting-Ip": "1.2.3.4"},
    )
    assert respuesta.status_code == 403
    assert "Mac" in respuesta.json()["detail"]
    # Y no guardó nada.
    assert cliente.get("/config/conexiones").json()["GROQ_API_KEY"]["puesta"] is False


def test_probar_con_cabecera_cf_es_403(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    cliente.put("/config/conexiones/GROQ_API_KEY", json={"valor": "gsk-x"})
    respuesta = cliente.post(
        "/config/conexiones/GROQ_API_KEY/probar",
        headers={"CF-Ray": "abc123"},  # mayúsculas distintas: igual debe cortar
    )
    assert respuesta.status_code == 403


def test_get_sin_cabeceras_cf_funciona_como_desde_el_mac(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    respuesta = cliente.get("/config/conexiones")
    assert respuesta.status_code == 200


def test_get_con_cabecera_cf_es_403(tmp_path, monkeypatch):
    """T5.3: termina_en es un pedazo real de la llave — un GET por el
    túnel ya es una fuga, no solo un PUT/POST."""
    cliente = _cliente(tmp_path, monkeypatch)
    cliente.put("/config/conexiones/GROQ_API_KEY", json={"valor": "gsk-secreta-123456"})

    respuesta = cliente.get("/config/conexiones", headers={"Cf-Connecting-Ip": "1.2.3.4"})

    assert respuesta.status_code == 403
    assert "3456" not in respuesta.text


def test_probar_llama_al_proveedor_real_con_monkeypatch(tmp_path, monkeypatch):
    import httpx

    cliente = _cliente(tmp_path, monkeypatch)
    cliente.put("/config/conexiones/GROQ_API_KEY", json={"valor": "gsk-buena"})

    class _Respuesta200:
        status_code = 200

    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _Respuesta200())
    respuesta = cliente.post("/config/conexiones/GROQ_API_KEY/probar")
    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is True


def _plata(tmp_path, monkeypatch):
    import json

    ruta = tmp_path / "plata.json"
    ruta.write_text(json.dumps({"meta_mensual": 2400, "moneda": "USD"}))
    monkeypatch.setattr(conexiones, "RUTA_PLATA", ruta)
    return ruta


def test_put_plata_cambia_la_meta_mensual(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    _plata(tmp_path, monkeypatch)
    respuesta = cliente.put("/config/plata", json={"meta_mensual": 3200})
    assert respuesta.status_code == 200
    assert respuesta.json()["meta_mensual"] == 3200


def test_put_plata_con_cabecera_cf_es_403(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    ruta = _plata(tmp_path, monkeypatch)
    respuesta = cliente.put("/config/plata", json={"meta_mensual": 3200}, headers={"Cf-Ray": "x"})
    assert respuesta.status_code == 403
    import json

    assert json.loads(ruta.read_text())["meta_mensual"] == 2400  # sin tocar


def test_put_plata_cero_es_422(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path, monkeypatch)
    _plata(tmp_path, monkeypatch)
    respuesta = cliente.put("/config/plata", json={"meta_mensual": 0})
    assert respuesta.status_code == 422

"""Desde afuera: un documento que llega al bot se puede bajar con el cliente real."""
from __future__ import annotations

import httpx
import pytest

import telegram


def _cliente(handler) -> telegram.ClienteBotAPI:
    c = telegram.ClienteBotAPI("T")
    c._http_envios = httpx.Client(transport=httpx.MockTransport(handler))
    return c


def test_cliente_real_baja_un_documento_completo(tmp_path):
    contenido = b"hola" * 5000

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/botT/getFile":
            assert req.url.params["file_id"] == "id-9"
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "documents/a.docx"}})
        if req.url.path == "/file/botT/documents/a.docx":
            return httpx.Response(200, content=contenido)
        return httpx.Response(404)

    destino = tmp_path / "nueva" / "a.docx"
    assert _cliente(handler).descargar_archivo("id-9", destino) == destino
    assert destino.read_bytes() == contenido


def test_archivo_remoto_caido_no_deja_archivo(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/getFile"):
            return httpx.Response(200, json={"result": {"file_path": "documents/a.docx"}})
        return httpx.Response(502)

    destino = tmp_path / "a.docx"
    with pytest.raises(httpx.HTTPStatusError):
        _cliente(handler).descargar_archivo("x", destino)
    assert not destino.exists()

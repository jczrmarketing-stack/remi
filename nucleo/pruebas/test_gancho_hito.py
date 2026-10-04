"""B3.2: el gancho SessionEnd lee `hito: <tema>#<n>` del primer turno del
transcript y lo manda al núcleo. El gancho en sí (scripts/hooks/) no
corre contra el núcleo real: un servidor HTTP falso en un hilo."""
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GANCHO = RAIZ / "scripts" / "hooks" / "claude-sesion.py"

sys.path.insert(0, str(GANCHO.parent))
import importlib

claude_sesion = importlib.import_module("claude-sesion")


def _transcript(tmp_path: Path, primer_texto: str) -> Path:
    archivo = tmp_path / "t.jsonl"
    lineas = [
        json.dumps({"type": "user", "message": {"role": "user", "content": primer_texto}}),
        json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "ok"}}),
    ]
    archivo.write_text("\n".join(lineas) + "\n")
    return archivo


def test_hito_del_primer_turno_lo_encuentra_en_la_primera_linea(tmp_path):
    archivo = _transcript(tmp_path, "hito: upvisuals#5\n\nQUÉ\nArreglar X.")
    assert claude_sesion.hito_del_primer_turno(str(archivo)) == "upvisuals#5"


def test_sin_encabezado_de_hito_es_none(tmp_path):
    archivo = _transcript(tmp_path, "QUÉ\nArreglar X, sin hito.")
    assert claude_sesion.hito_del_primer_turno(str(archivo)) is None


def test_contenido_en_bloques_de_texto_tambien_funciona(tmp_path):
    archivo = tmp_path / "t.jsonl"
    linea = json.dumps(
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hito: beam#2\n\nQUÉ"}]}}
    )
    archivo.write_text(linea + "\n")
    assert claude_sesion.hito_del_primer_turno(str(archivo)) == "beam#2"


def test_archivo_que_no_existe_no_rompe():
    assert claude_sesion.hito_del_primer_turno("/no/existe/nada.jsonl") == None


def test_sin_transcript_path_es_none():
    assert claude_sesion.hito_del_primer_turno("") is None


def test_un_tool_result_como_primer_type_user_no_rompe_y_sigue_buscando(tmp_path):
    """Revisión de B3: en el JSONL real, un resultado de herramienta
    también llega con type=="user" pero sin bloques de texto. El gancho
    no debe leer eso como si fuera el primer turno humano con el header."""
    archivo = tmp_path / "t.jsonl"
    lineas = [
        json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}),
        json.dumps({"type": "user", "message": {"role": "user", "content": "hito: upvisuals#5\n\nQUÉ\nArreglar X."}}),
    ]
    archivo.write_text("\n".join(lineas) + "\n")
    assert claude_sesion.hito_del_primer_turno(str(archivo)) == "upvisuals#5"


class _Responde(BaseHTTPRequestHandler):
    ultimo: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length", "0"))
        cuerpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).ultimo = cuerpo
        salida = json.dumps({"proyecto": None, "anotado": False}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(salida)))
        self.end_headers()
        self.wfile.write(salida)

    def log_message(self, formato: str, *args: object) -> None:
        return


def _servidor() -> tuple[ThreadingHTTPServer, str]:
    import threading

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Responde)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_address[1]}"


def test_el_gancho_manda_el_hito_que_encontro_en_el_transcript(tmp_path):
    archivo = _transcript(tmp_path, "hito: upvisuals#5\n\nQUÉ\nArreglar X.")
    servidor, url = _servidor()
    try:
        hecho = subprocess.run(
            ["python3", str(GANCHO)],
            input=json.dumps(
                {
                    "hook_event_name": "SessionEnd",
                    "cwd": str(tmp_path),
                    "session_id": "s1",
                    "transcript_path": str(archivo),
                }
            ),
            capture_output=True,
            text=True,
            env={**os.environ, "REMI_NUCLEO_URL": url},
            check=False,
        )
    finally:
        servidor.shutdown()
    assert hecho.returncode == 0
    assert _Responde.ultimo["datos"]["hito"] == "upvisuals#5"


def test_el_gancho_sin_hito_no_manda_la_clave(tmp_path):
    archivo = _transcript(tmp_path, "QUÉ\nsin hito.")
    servidor, url = _servidor()
    try:
        hecho = subprocess.run(
            ["python3", str(GANCHO)],
            input=json.dumps(
                {
                    "hook_event_name": "SessionEnd",
                    "cwd": str(tmp_path),
                    "session_id": "s1",
                    "transcript_path": str(archivo),
                }
            ),
            capture_output=True,
            text=True,
            env={**os.environ, "REMI_NUCLEO_URL": url},
            check=False,
        )
    finally:
        servidor.shutdown()
    assert hecho.returncode == 0
    assert "hito" not in _Responde.ultimo["datos"]

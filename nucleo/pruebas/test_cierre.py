"""Abrir Claude devuelve el Estado. Cerrar escribe el episodio y el libro."""
import importlib
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[2]
GANCHO = RAIZ / "scripts" / "hooks" / "claude-sesion.py"
INSTALAR = RAIZ / "scripts" / "hooks" / "instalar-claude.py"

LIBRO = """---
titulo: Malik
tema: malik
resumen: Las cuentas.
ruta: {repo}
---

## Estado

Quedaste: en el mosaico.
Decisiones: Reddit espera.
Próximo paso: abrir la ficha, cinco minutos.

## Notas

Esto se queda.
"""


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "libros"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path / "boveda"))
    monkeypatch.setenv("REMI_ESTADO", "1")
    monkeypatch.setenv("REMI_TRABAJO_EN_LINEA", "1")
    for nombre in ("servidor", "db", "trabajo", "libros", "episodios"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _libro(tmp_path, repo: Path) -> None:
    carpeta = tmp_path / "libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "malik.md").write_text(LIBRO.format(repo=repo))


def test_al_abrir_inyecta_donde_quedo(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, repo)
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    respuesta = cliente.post(
        "/evento",
        json={"tipo": "sesion_inicio", "ruta": str(repo), "datos": {"session_id": "abc"}},
    )

    assert respuesta.status_code == 200
    contexto = respuesta.json()["contexto"]
    assert contexto.startswith("Proyecto: Malik")
    assert "Quedaste: en el mosaico." in contexto
    assert "Próximo paso: abrir la ficha, cinco minutos." in contexto
    assert len(contexto.splitlines()) <= 15
    assert "Esto se queda." not in contexto


def test_al_cerrar_escribe_episodio_y_actualiza_el_libro(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, repo)
    transcript = tmp_path / "sesion.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "Dejé la ficha a medias."}})
        + "\n"
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    import cierre

    def redactar(_pedido: str) -> dict[str, str]:
        return {
            "Qué se hizo": "Quedó la ficha a medias.",
            "Decisiones": "Reddit espera.",
            "Pendientes": "la ficha",
            "Primer paso de mañana": "abrir la ficha, cinco minutos",
        }

    monkeypatch.setattr(cierre, "redactar", redactar)
    cliente = TestClient(servidor.app)
    respuesta = cliente.post(
        "/evento",
        json={
            "tipo": "sesion_fin",
            "ruta": str(repo),
            "datos": {"session_id": "abc", "transcript_path": str(transcript)},
        },
    )

    assert respuesta.status_code == 200
    episodios = list((tmp_path / "boveda" / "episodios").glob("*.md"))
    assert len(episodios) == 1
    nota = episodios[0].read_text()
    assert "## Qué se hizo" in nota
    assert "## Decisiones" in nota
    assert "## Pendientes" in nota
    assert "## Primer paso de mañana" in nota
    assert "cinco minutos" in nota
    libro = (tmp_path / "libros" / "malik.md").read_text()
    assert "Quedaste: Quedó la ficha a medias." in libro
    assert "## Notas" in libro
    assert "Esto se queda." in libro


def test_el_titulo_y_el_resumen_se_cortan_en_la_primera_frase(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, repo)
    transcript = tmp_path / "sesion.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "Seguí con la ficha."}}) + "\n"
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    import cierre

    monkeypatch.setattr(
        cierre,
        "redactar",
        lambda _pedido: {
            "Qué se hizo": (
                "Se investigó el fallo de autenticación de la API de Claude. Se confirmó "
                "que el token había vencido."
            ),
            "Decisiones": "ninguna nueva",
            "Pendientes": "ninguno",
            "Primer paso de mañana": (
                "Enviar una solicitud de soporte técnico a Claude para investigar la causa "
                "del error 401. estudio: o freno:"
            ),
        },
    )
    cliente = TestClient(servidor.app)
    respuesta = cliente.post(
        "/evento",
        json={
            "tipo": "sesion_fin",
            "ruta": str(repo),
            "datos": {"session_id": "abc", "transcript_path": str(transcript)},
        },
    )

    assert respuesta.status_code == 200
    episodio = next((tmp_path / "boveda" / "episodios").glob("*.md"))
    nota = episodio.read_text()
    frontmatter = "\n".join(nota.splitlines()[:4])
    assert 'titulo: "Se investigó el fallo de autenticación de la API de Claude."' in frontmatter
    assert "…" not in frontmatter
    assert "Se confirmó" not in frontmatter
    assert "estudio: o freno:" not in frontmatter
    assert (
        'resumen: "Enviar una solicitud de soporte técnico a Claude para investigar la causa del error 401."'
        in frontmatter
    )
    libro = (tmp_path / "libros" / "malik.md").read_text()
    estado = libro[libro.index("## Estado") :]
    assert "estudio: o freno:" not in estado
    assert "Próximo paso: Enviar una solicitud de soporte técnico a Claude para investigar la causa del error 401." in estado


def test_un_problema_resuelto_deja_ademas_un_episodio_de_error(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, repo)
    transcript = tmp_path / "sesion.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": "Ya anduvo: la causa era que el webhook no reintentaba tras un 500.",
                },
            }
        )
        + "\n"
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    import cierre

    monkeypatch.setattr(
        cierre,
        "redactar",
        lambda _pedido: {
            "Qué se hizo": "Se arregló el webhook.",
            "Decisiones": "ninguna nueva",
            "Pendientes": "ninguno",
            "Primer paso de mañana": "seguir mañana",
        },
    )
    monkeypatch.setattr(
        cierre,
        "redactar_error",
        lambda _charla, _titulo: {
            "Síntoma": "El webhook no reintentaba tras un 500.",
            "Causa": "Faltaba el reintento tras un 500.",
            "Cura": "Se agregó el reintento con backoff.",
            "Archivo": "webhook.py",
        },
    )
    cliente = TestClient(servidor.app)
    respuesta = cliente.post(
        "/evento",
        json={
            "tipo": "sesion_fin",
            "ruta": str(repo),
            "datos": {"session_id": "abc", "transcript_path": str(transcript)},
        },
    )

    assert respuesta.status_code == 200
    episodios = sorted((tmp_path / "boveda" / "episodios").glob("*.md"))
    assert len(episodios) == 2
    de_error = [e for e in episodios if "error" in e.name][0]
    nota = de_error.read_text()
    assert "fuente: error" in nota
    assert "claves: [error, malik]" in nota
    assert "## Síntoma" in nota
    assert "El webhook no reintentaba tras un 500." in nota
    assert "## Cura" in nota
    assert "Se agregó el reintento con backoff." in nota


def test_sin_patron_de_error_no_deja_episodio_de_error(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, repo)
    transcript = tmp_path / "sesion.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "Segui con la ficha."}}) + "\n"
    )
    servidor = _arrancar(tmp_path, monkeypatch)
    import cierre

    monkeypatch.setattr(
        cierre,
        "redactar",
        lambda _pedido: {
            "Qué se hizo": "Se avanzó con la ficha.",
            "Decisiones": "ninguna nueva",
            "Pendientes": "ninguno",
            "Primer paso de mañana": "seguir mañana",
        },
    )
    llamado: list[int] = []

    def redactar_error_falso(*_args: object) -> dict[str, str] | None:
        llamado.append(1)
        return None

    monkeypatch.setattr(cierre, "redactar_error", redactar_error_falso)
    cliente = TestClient(servidor.app)
    cliente.post(
        "/evento",
        json={
            "tipo": "sesion_fin",
            "ruta": str(repo),
            "datos": {"session_id": "abc", "transcript_path": str(transcript)},
        },
    )
    assert not llamado
    episodios = list((tmp_path / "boveda" / "episodios").glob("*.md"))
    assert len(episodios) == 1


def test_una_sesion_sin_charla_no_deja_episodio_ni_toca_el_libro(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "malik"
    repo.mkdir()
    _libro(tmp_path, repo)
    libro = tmp_path / "libros" / "malik.md"
    antes = libro.read_text()
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)
    vacio = tmp_path / "vacio.jsonl"
    vacio.write_text("")
    for datos in ({"session_id": "abc"}, {"session_id": "def", "transcript_path": str(vacio)}):
        cliente.post("/evento", json={"tipo": "sesion_fin", "ruta": str(repo), "datos": datos})
    assert list((tmp_path / "boveda" / "episodios").glob("*.md")) == []
    assert libro.read_text() == antes


class _Responde(BaseHTTPRequestHandler):
    ultimo: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length", "0"))
        cuerpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).ultimo = cuerpo
        salida: dict[str, object]
        if cuerpo.get("tipo") == "sesion_inicio":
            salida = {"proyecto": "malik", "contexto": "Proyecto: Malik\nQuedaste: en el mosaico."}
        else:
            salida = {"proyecto": "malik", "anotado": False}
        crudo = json.dumps(salida).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(crudo)))
        self.end_headers()
        self.wfile.write(crudo)

    def log_message(self, formato: str, *args: object) -> None:
        return


def _servidor() -> tuple[ThreadingHTTPServer, str]:
    import threading

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Responde)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_address[1]}"


def test_el_gancho_imprime_el_contexto_al_abrir(tmp_path: Path) -> None:
    servidor, url = _servidor()
    try:
        hecho = subprocess.run(
            ["python3", str(GANCHO)],
            input=json.dumps(
                {
                    "hook_event_name": "SessionStart",
                    "cwd": str(tmp_path),
                    "session_id": "abc",
                    "transcript_path": str(tmp_path / "t.jsonl"),
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
    salida = json.loads(hecho.stdout)
    assert salida["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "Quedaste: en el mosaico." in salida["hookSpecificOutput"]["additionalContext"]


def test_el_gancho_calla_si_el_nucleo_no_esta(tmp_path: Path) -> None:
    hecho = subprocess.run(
        ["python3", str(GANCHO)],
        input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(tmp_path)}),
        capture_output=True,
        text=True,
        env={**os.environ, "REMI_NUCLEO_URL": "http://127.0.0.1:9"},
        check=False,
    )
    assert hecho.returncode == 0
    assert hecho.stdout == ""


def test_instalar_suma_los_ganchos_sin_pisar_el_que_hay(tmp_path: Path) -> None:
    destino = tmp_path / "settings.json"
    destino.write_text(
        json.dumps(
            {
                "model": "sonnet",
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write|MultiEdit",
                            "hooks": [{"type": "command", "command": "python3 \"$HOME/projects/malik-gestion/scripts/hook-no-external-links.py\""}],
                        }
                    ]
                },
            }
        )
    )
    subprocess.run(
        ["python3", str(INSTALAR)],
        check=True,
        env={**os.environ, "REMI_CLAUDE_SETTINGS": str(destino)},
    )
    datos = json.loads(destino.read_text())
    assert datos["model"] == "sonnet"
    assert "hook-no-external-links.py" in json.dumps(datos["hooks"]["PreToolUse"])
    assert "claude-sesion.py" in json.dumps(datos["hooks"]["SessionStart"])
    assert "claude-sesion.py" in json.dumps(datos["hooks"]["SessionEnd"])
    subprocess.run(
        ["python3", str(INSTALAR)],
        check=True,
        env={**os.environ, "REMI_CLAUDE_SETTINGS": str(destino)},
    )
    otra = json.loads(destino.read_text())
    assert len(otra["hooks"]["SessionStart"]) == 1

"""T5.2: scripts/rotar-logs.sh — por tamaño, nunca pierde lo de hoy."""
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "rotar-logs.sh"


def _correr(carpeta: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={"REMI_LOGS": str(carpeta), "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=True,
    )


def test_no_toca_un_log_chico(tmp_path):
    log = tmp_path / "chico.log"
    log.write_text("una línea\n")

    _correr(tmp_path)

    assert log.read_text() == "una línea\n"
    assert not (tmp_path / "chico.log.1").exists()


def test_rota_un_log_grande_sin_perder_nada(tmp_path):
    log = tmp_path / "grande.log"
    contenido = "x" * (11 * 1024 * 1024)
    log.write_text(contenido)

    resultado = _correr(tmp_path)

    assert log.stat().st_size == 0
    copia = tmp_path / "grande.log.1"
    assert copia.exists()
    assert copia.read_text() == contenido
    assert "rotado" in resultado.stdout


def test_un_escritor_que_sigue_abierto_sigue_escribiendo_bien(tmp_path):
    """El caso real: un proceso tiene el archivo abierto en O_APPEND
    (como StandardOutPath de launchd) cuando se rota."""
    log = tmp_path / "vivo.log"
    log.write_text("x" * (11 * 1024 * 1024))

    with open(log, "a") as escritor:
        _correr(tmp_path)
        escritor.write("después de rotar\n")

    assert log.read_text() == "después de rotar\n"

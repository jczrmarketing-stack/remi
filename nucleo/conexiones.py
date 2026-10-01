"""Conexiones (Panel → Ajustes): llaves y tokens, nunca su valor completo.

Lista blanca fija: cualquier otro nombre es `NombreInvalido` (400 en la
ruta). `guardar()` reescribe `nucleo/.env` atómico — temporal + chmod 600
+ `Path.replace()` —, conserva comentarios y líneas ajenas (REMI_PENSADOR,
REMI_VENICE_MODELO, lo que sea), y deja un `.env.bak` con el contenido
anterior. Un valor vacío quita la línea entera, nunca deja `NOMBRE=`.

`probar()` nunca lanza: una llave mala es un resultado para mostrar, no
un error de programa. Timeout corto (8 s) para no colgar el panel.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import httpx
from pydantic import BaseModel

RUTA_ENV = Path(__file__).resolve().parent / ".env"
TIMEOUT_PRUEBA_SEGUNDOS = 8.0
VERSION_NOTION = "2022-06-28"

# Las que de verdad son un secreto: a estas se les muestra `termina_en`.
SECRETOS = {"TELEGRAM_TOKEN", "NOTION_TOKEN", "OPENROUTER_API_KEY", "GROQ_API_KEY", "VENICE_API_KEY"}
# El resto de la lista blanca: un id o un flag, no un secreto.
NO_SECRETOS = {"TELEGRAM_CHAT_ID", "NOTION_PAGINA_ID", "NOTION_VUELTA"}
LISTA_BLANCA = SECRETOS | NO_SECRETOS

_PATRON_CLAVE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")


class NombreInvalido(Exception):
    """Un nombre fuera de la lista blanca."""


class Prueba(BaseModel):
    ok: bool
    mensaje_humano: str


class Conexion(BaseModel):
    puesta: bool
    termina_en: str | None = None
    ultima_prueba: Prueba | None = None


# En memoria, no en disco: «lo último que probé esta sesión». Se pierde
# al reiniciar el núcleo, y eso está bien — no es un dato que haga falta
# conservar entre arranques.
_ULTIMA_PRUEBA: dict[str, Prueba] = {}


def _leer_lineas(ruta: Path) -> list[str]:
    if not ruta.exists():
        return []
    return ruta.read_text().splitlines()


def _valores(lineas: list[str]) -> dict[str, str]:
    """KEY=VALOR por línea, igual que pensar._leer_env: # comenta, comillas
    alrededor del valor se quitan."""
    valores: dict[str, str] = {}
    for linea in lineas:
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        coincidencia = _PATRON_CLAVE.match(limpia)
        if not coincidencia:
            continue
        valores[coincidencia.group(1)] = limpia[coincidencia.end():].strip().strip("\"'")
    return valores


def estado() -> dict[str, Conexion]:
    valores = _valores(_leer_lineas(RUTA_ENV))
    salida: dict[str, Conexion] = {}
    for nombre in LISTA_BLANCA:
        valor = valores.get(nombre, "")
        puesta = bool(valor)
        termina_en = valor[-4:] if (puesta and nombre in SECRETOS) else None
        salida[nombre] = Conexion(puesta=puesta, termina_en=termina_en, ultima_prueba=_ULTIMA_PRUEBA.get(nombre))
    return salida


def guardar(nombre: str, valor: str) -> None:
    """Reescribe nucleo/.env de forma atómica. `valor` vacío quita la
    línea; cualquier otra línea (comentario, en blanco, ajena a la lista
    blanca) queda exactamente donde estaba."""
    if nombre not in LISTA_BLANCA:
        raise NombreInvalido(nombre)

    lineas = _leer_lineas(RUTA_ENV)
    nueva: list[str] = []
    escrita = False
    for linea in lineas:
        limpia = linea.strip()
        coincidencia = None if (not limpia or limpia.startswith("#")) else _PATRON_CLAVE.match(limpia)
        if coincidencia and coincidencia.group(1) == nombre:
            escrita = True
            if valor:
                nueva.append(f"{nombre}={valor}")
            continue  # valor vacío: se quita, no se vuelve a escribir
        nueva.append(linea)
    if valor and not escrita:
        nueva.append(f"{nombre}={valor}")

    contenido = "\n".join(nueva)
    if contenido:
        contenido += "\n"

    if RUTA_ENV.exists():
        shutil.copy2(RUTA_ENV, _ruta_respaldo())

    temporal = RUTA_ENV.parent / (RUTA_ENV.name + ".tmp")
    temporal.write_text(contenido)
    temporal.chmod(0o600)
    temporal.replace(RUTA_ENV)  # atómico: nunca queda un .env a medio escribir

    if nombre in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"):
        # Import diferido: conexiones.py no es algo que telegram.py necesite
        # importar, y así se evita cualquier ciclo si algún día lo hiciera.
        import telegram

        telegram.reiniciar_hilo()


def _ruta_respaldo() -> Path:
    return RUTA_ENV.parent / (RUTA_ENV.name + ".bak")


def probar(nombre: str) -> Prueba:
    if nombre not in LISTA_BLANCA:
        raise NombreInvalido(nombre)

    valor = _valores(_leer_lineas(RUTA_ENV)).get(nombre, "")
    if not valor:
        resultado = Prueba(ok=False, mensaje_humano="No hay nada guardado para probar.")
    else:
        resultado = _probar_de_verdad(nombre, valor)
    _ULTIMA_PRUEBA[nombre] = resultado
    return resultado


def _probar_de_verdad(nombre: str, valor: str) -> Prueba:
    try:
        if nombre == "TELEGRAM_TOKEN":
            return _probar_telegram(valor)
        if nombre == "NOTION_TOKEN":
            return _probar_get(
                "https://api.notion.com/v1/users/me",
                {"Authorization": f"Bearer {valor}", "Notion-Version": VERSION_NOTION},
                "Notion",
            )
        if nombre == "OPENROUTER_API_KEY":
            return _probar_get(
                "https://openrouter.ai/api/v1/auth/key", {"Authorization": f"Bearer {valor}"}, "OpenRouter"
            )
        if nombre == "GROQ_API_KEY":
            return _probar_get(
                "https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {valor}"}, "Groq"
            )
        if nombre == "VENICE_API_KEY":
            return _probar_get(
                "https://api.venice.ai/api/v1/models", {"Authorization": f"Bearer {valor}"}, "Venice"
            )
        return Prueba(ok=True, mensaje_humano="Guardado. No hay una prueba automática para esto.")
    except httpx.TimeoutException:
        return Prueba(ok=False, mensaje_humano="No contestó en 8 segundos. Probá de nuevo.")
    except httpx.HTTPError as error:
        return Prueba(ok=False, mensaje_humano=f"No pude conectarme ({type(error).__name__}).")
    except Exception as error:  # nunca lanza: una prueba rota es un resultado, no un 500
        return Prueba(ok=False, mensaje_humano=f"Falló de un modo raro ({type(error).__name__}).")


def _probar_get(url: str, headers: dict[str, str], proveedor: str) -> Prueba:
    respuesta = httpx.get(url, headers=headers, timeout=TIMEOUT_PRUEBA_SEGUNDOS)
    if respuesta.status_code == 200:
        return Prueba(ok=True, mensaje_humano=f"{proveedor} la acepta.")
    if respuesta.status_code in (401, 403):
        return Prueba(ok=False, mensaje_humano=f"{proveedor} no reconoce esa llave.")
    return Prueba(ok=False, mensaje_humano=f"{proveedor} devolvió {respuesta.status_code}.")


def _probar_telegram(token: str) -> Prueba:
    respuesta = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=TIMEOUT_PRUEBA_SEGUNDOS)
    if respuesta.status_code == 409:
        # El encargo pide estas palabras literales: pasa cuando dos
        # procesos hacen long polling con el mismo token a la vez.
        return Prueba(ok=False, mensaje_humano="Telegram devolvió 409: ya hay otro proceso escuchando con este token.")
    cuerpo = respuesta.json() if respuesta.headers.get("content-type", "").startswith("application/json") else {}
    if respuesta.status_code == 200 and cuerpo.get("ok"):
        usuario = cuerpo.get("result", {}).get("username", "")
        return Prueba(ok=True, mensaje_humano=f"Conectado como @{usuario}." if usuario else "Telegram lo acepta.")
    return Prueba(ok=False, mensaje_humano="Telegram no reconoce ese token.")

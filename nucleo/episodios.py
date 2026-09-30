"""Una charla pegada se guarda como episodio (3c · 7).

Si Juan Camilo pega una conversación larga y dice que sí, se resume con el
modelo local (Haiku si Ollama no está) y queda en dos lados:

- la bóveda: remi-mente/episodios/AAAA-MM-DD-titulo.md, con frontmatter
  titulo/tema/resumen y la charla entera debajo (legible y editable por él);
- la memoria (SQLite), como una fila más que la mente puede listar y leer.

Todavía sin embeddings: eso es 3c-vectores.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import db
import pensar
from modelos import Memoria

CARPETA_BOVEDA = Path(__file__).resolve().parent.parent / "conocimiento"
LARGO_MINIMO = 1500

INSTRUCCIONES = (
    "Te pasan una conversación entera. Devolvé SOLO un JSON, sin nada antes ni después, con "
    'tres campos: "titulo" (máximo 60 caracteres, de qué trató), "tema" (una palabra en '
    'minúsculas: el proyecto o el área, por ejemplo upvisuals, malik, remi, salud, finanzas) y '
    '"resumen" (máximo 220 caracteres: con qué hay que quedarse — decisiones, números, '
    "pendientes). En español."
)


@dataclass
class Episodio:
    titulo: str
    tema: str
    resumen: str
    ruta: Path
    memoria_id: str
    resumido_por: str


def carpeta_episodios() -> Path:
    return Path(os.environ.get("REMI_BOVEDA") or CARPETA_BOVEDA) / "episodios"


def slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    limpio = re.sub(r"[^a-z0-9]+", "-", sin_tildes).strip("-")
    return limpio[:60].rstrip("-") or "charla"


def _leer_json(texto: str) -> dict[str, str] | None:
    encontrado = re.search(r"\{.*\}", texto, re.DOTALL)
    if not encontrado:
        return None
    try:
        datos = json.loads(encontrado.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(datos, dict):
        return None
    return {k: str(v).strip() for k, v in datos.items() if isinstance(v, (str, int, float))}


def _temas_conocidos() -> dict[str, str]:
    """Cada tema con el título de su libro: «upvisuals: UpVisuals — cliente
    Alfonso». Sin el título, gemma no sabe que Alfonso es UpVisuals."""
    conexion = db.conectar()
    try:
        temas: dict[str, str] = {}
        for entrada in db.indice_memoria(conexion):
            temas.setdefault(entrada.tema, entrada.titulo)
        return temas
    finally:
        conexion.close()


def _instrucciones() -> str:
    """Con los temas que ya existen: gemma inventaba «remimarketing»."""
    temas = _temas_conocidos()
    if not temas:
        return INSTRUCCIONES
    lista = "; ".join(f"{tema} ({titulo})" for tema, titulo in sorted(temas.items()))
    return f"{INSTRUCCIONES} Para \"tema\" elegí uno de estos si corresponde: {lista}. Si ninguno, «charla»."


def _recortar(texto: str, largo: int) -> str:
    """Corta en el último espacio antes del largo, nunca a mitad de palabra."""
    if len(texto) <= largo:
        return texto
    return texto[: largo - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _resumir(texto: str) -> tuple[dict[str, str] | None, str]:
    """Ollama primero (local, gratis); si no está o no da un JSON, Haiku."""
    instrucciones = _instrucciones()
    modelo = pensar._ajuste("REMI_OLLAMA_MODELO", pensar.OLLAMA_MODELO_POR_DEFECTO)
    try:
        datos = pensar._llamar_ollama(modelo, instrucciones, texto)
        pensado = pensar._leer_respuesta_venice(datos, modelo, 0, proveedor="ollama")
        resumen = _leer_json(pensado.paso_minimo) if pensado else None
        if resumen:
            return resumen, f"ollama/{modelo}"
        print("[episodio] Ollama no devolvió un JSON: pruebo con Haiku", file=sys.stderr)
    except Exception as error:  # noqa: BLE001 — cualquier falla de Ollama cae a Haiku
        print(f"[episodio] Ollama no está ({type(error).__name__}): pruebo con Haiku", file=sys.stderr)
    pensado = pensar._una_llamada_claude(pensar.MODOS["rapido"], texto, instrucciones, [])
    resumen = _leer_json(pensado.paso_minimo) if pensado else None
    return resumen, "haiku"


def _ruta_libre(carpeta: Path, base: str) -> Path:
    ruta = carpeta / f"{base}.md"
    n = 2
    while ruta.exists():
        ruta = carpeta / f"{base}-{n}.md"
        n += 1
    return ruta


def _una_linea(texto: str) -> str:
    return " ".join(texto.split()).replace('"', "'")


def guardar(texto: str, ahora: datetime, resumidor=None) -> Episodio:  # type: ignore[no-untyped-def]
    """Resume, escribe la nota en la bóveda y la fila en memoria."""
    resumen, por = (resumidor or _resumir)(texto)
    primera = _una_linea(texto)[:60]
    titulo = _recortar(_una_linea((resumen or {}).get("titulo") or primera), 80) or "Charla"
    tema = slug((resumen or {}).get("tema") or "charla").split("-")[0]
    cuerpo_resumen = _recortar(_una_linea((resumen or {}).get("resumen") or primera), 240) or titulo

    carpeta = carpeta_episodios()
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = _ruta_libre(carpeta, f"{ahora:%Y-%m-%d}-{slug(titulo)}")
    ruta.write_text(
        f'---\ntitulo: "{titulo}"\ntema: {tema}\nresumen: "{cuerpo_resumen}"\n---\n\n{texto.strip()}\n'
    )

    memoria = Memoria(
        id=uuid4(),
        titulo=titulo,
        resumen=cuerpo_resumen,
        tema=tema,
        fecha=ahora,
        cuerpo=texto.strip(),
        fuente="ollama" if por.startswith("ollama") else "conversacion",
        claves=None,
        nivel=2,
    )
    conexion = db.conectar()
    try:
        db.guardar_memoria(conexion, memoria)
    finally:
        conexion.close()
    print(f"[episodio] {ruta.name} · tema={tema} · resumió {por}", file=sys.stderr)
    return Episodio(titulo, tema, cuerpo_resumen, ruta, str(memoria.id), por)

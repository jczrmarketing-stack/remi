#!/usr/bin/env python3
"""Genera nucleo/modelos.py desde contratos/contratos.json.

Corre: uv run python generar_modelos.py
Los modelos de nucleo/modelos.py nunca se editan a mano — se regeneran aquí.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CONTRATOS = Path(__file__).resolve().parent.parent / "contratos" / "contratos.json"
SALIDA = Path(__file__).resolve().parent / "modelos.py"

TIPOS_BASE = {
    "uuid": "UUID",
    "string": "str",
    "int": "int",
    "number": "float",
    "bool": "bool",
}

RANGO = re.compile(r"^(\d+)-(\d+)$")
# string(80): un texto con largo máximo. El límite es del contrato, no una
# validación suelta en el servidor — así lo respetan todas las capas.
LARGO_MAXIMO = re.compile(r"^string\((\d+)\)$")


def tipo_python(spec: bool | str) -> tuple[str, str | None, str | None]:
    """Devuelve (anotación, valor_por_defecto_literal, argumentos de Field)."""
    if isinstance(spec, bool):
        return "bool", repr(spec), None

    alternativas = spec.split("|")
    opcional = "null" in alternativas
    alternativas = [a for a in alternativas if a != "null"]

    restriccion = None
    if len(alternativas) == 1:
        alt = alternativas[0]
        rango = RANGO.match(alt)
        largo = LARGO_MAXIMO.match(alt)
        if alt in TIPOS_BASE:
            base = TIPOS_BASE[alt]
        elif alt.startswith("iso"):
            base = "datetime"
        elif rango:
            base = "int"
            restriccion = f"ge={rango.group(1)}, le={rango.group(2)}"
        elif largo:
            base = "str"
            restriccion = f"min_length=1, max_length={largo.group(1)}"
        else:
            base = f'Literal["{alt}"]'
    else:
        opciones = ", ".join(f'"{a}"' for a in alternativas)
        base = f"Literal[{opciones}]"

    tipo = f"{base} | None" if opcional else base
    return tipo, None, restriccion


def linea_campo(campo: str, spec: bool | str) -> str:
    tipo, default_literal, restriccion = tipo_python(spec)

    if default_literal is not None:
        return f"    {campo}: {tipo} = {default_literal}"

    if restriccion is not None:
        opcional = tipo.endswith("| None")
        default = ", default=None" if opcional else ""
        return f"    {campo}: {tipo} = Field({restriccion}{default})"

    return f"    {campo}: {tipo}"


def generar() -> None:
    contrato = json.loads(CONTRATOS.read_text())

    lineas = [
        '"""Generado desde contratos/contratos.json por generar_modelos.py.',
        "",
        "No editar a mano: corre `uv run python generar_modelos.py` de nuevo.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from datetime import datetime",
        "from typing import Literal",
        "from uuid import UUID",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
    ]

    for entidad, campos in contrato.items():
        if entidad.startswith("$") or not isinstance(campos, dict):
            continue
        lineas.append("")
        lineas.append("")
        lineas.append(f"class {entidad}(BaseModel):")
        lineas.append('    model_config = ConfigDict(extra="forbid")')
        lineas.append("")
        for campo, spec in campos.items():
            lineas.append(linea_campo(campo, spec))

    lineas.append("")
    SALIDA.write_text("\n".join(lineas))
    print(f"Escrito {SALIDA}")


if __name__ == "__main__":
    generar()

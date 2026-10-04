#!/usr/bin/env python
"""Pone en el estante lo que Remi tiene que saber desde el primer día.

Idempotente: se puede correr todas las veces que haga falta. Una entrada ya
sembrada se reconoce por su título; si está, no se duplica ni se pisa —
puede haberla editado Juan Camilo y no somos quién para deshacerlo.

    cd nucleo && uv run python sembrar_memoria.py
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import db
from modelos import Memoria

SEMILLAS: tuple[dict[str, str], ...] = (
    {
        "titulo": "Construimos para la gente que usa Shopify, no para Shopify",
        "resumen": (
            "El e-commerce funciona distinto por región: Latinoamérica vive en WhatsApp y "
            "pago contra entrega porque desconfía; EE.UU. compra directo en el sitio."
        ),
        "tema": "shopify-cliente",
        "cuerpo": (
            "La diferencia entre una región y otra no es de tecnología, es de confianza.\n\n"
            "En Latinoamérica el comprador quiere hablar con alguien antes de pagar. Por eso "
            "WhatsApp no es un canal de soporte: es donde ocurre la venta. La tienda es el "
            "catálogo y la conversación es la caja. El pago contra entrega existe por lo "
            "mismo: nadie quiere adelantarle plata a un desconocido, y la tarjeta no arregla "
            "eso.\n\n"
            "En Estados Unidos esa desconfianza ya se resolvió hace veinte años, con tarjetas "
            "y devoluciones fáciles. El checkout del sitio alcanza, y meterle una "
            "conversación al medio solo agrega fricción.\n\n"
            "De ahí sale la regla: construir lo mismo para las dos regiones es construir para "
            "ninguna. Lo que se vende no es una tienda, es la forma de comprar que cada quien "
            "ya tiene."
        ),
    },
)


def sembrar() -> int:
    """Devuelve cuántas entradas se agregaron."""
    conexion = db.conectar()
    try:
        titulos_puestos = {entrada.titulo for entrada in db.indice_memoria(conexion)}
        agregadas = 0
        for semilla in SEMILLAS:
            if semilla["titulo"] in titulos_puestos:
                print(f"ya estaba · {semilla['titulo']}")
                continue
            db.guardar_memoria(
                conexion,
                Memoria(
                    id=uuid4(),
                    titulo=semilla["titulo"],
                    resumen=semilla["resumen"],
                    tema=semilla["tema"],
                    fecha=datetime.now(timezone.utc),
                    cuerpo=semilla["cuerpo"],
                    fuente="manual",
                    claves=None,
                    nivel=None,
                    tipo=None,
                ),
            )
            print(f"sembrada · {semilla['titulo']}")
            agregadas += 1
        return agregadas
    finally:
        conexion.close()


if __name__ == "__main__":
    cuantas = sembrar()
    print(f"\n{cuantas} entrada(s) nueva(s) en el estante.")

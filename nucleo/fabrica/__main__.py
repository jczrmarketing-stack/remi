"""python3 -m fabrica pedir "<idea>" [--base rama] | aprobar <id> | ver [<id>]

Se corre desde `nucleo/` con el venv del núcleo.
"""
from __future__ import annotations

import argparse
import sys

from fabrica import expediente, linea


def main(argv: list[str] | None = None, mundo: linea.Mundo | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m fabrica", description="La fábrica: de una idea a un PR en borrador.")
    sub = parser.add_subparsers(dest="orden", required=True)
    p_pedir = sub.add_parser("pedir", help="crea el pedido y corre el Planificador")
    p_pedir.add_argument("idea")
    p_pedir.add_argument("--base", default="main", help="rama de partida (main por defecto)")
    p_aprobar = sub.add_parser("aprobar", help="aprueba la spec y corre hasta el PR")
    p_aprobar.add_argument("id")
    p_ver = sub.add_parser("ver", help="lista los pedidos o muestra uno")
    p_ver.add_argument("id", nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.orden == "pedir":
            id_ = linea.pedir(args.idea, args.base, mundo)
            datos = expediente.leer(id_)
            print(f"Pedido {id_} · {datos['meta']['estado']}\n\n{datos['secciones']['Spec']}")
        elif args.orden == "aprobar":
            print(f"Pedido {args.id} · {linea.aprobar(args.id, mundo)}")
        elif args.id:
            print((expediente.carpeta(args.id) / "expediente.md").read_text(encoding="utf-8")
                  if expediente.leer(args.id) else "")
        else:
            pedidos = expediente.listar()
            if not pedidos:
                print("No hay pedidos todavía.")
            for meta in pedidos:
                idea = expediente.leer(meta["pedido"])["secciones"]["Contexto"].splitlines()[0]
                print(f"{meta['pedido']} · {meta['estado']} · {idea}")
    except KeyError as error:
        print(f"No encuentro el pedido {error.args[0]}.", file=sys.stderr)
        return 1
    except (linea.Ocupada, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

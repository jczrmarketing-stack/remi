"""python3 -m fabrica pedir "<idea>" [--base rama] | responder <id> "<respuesta>" | aprobar <id> [--de-noche] | ver [<id>]
                  | encolar "<idea>" [--base rama] | noche | cola

Se corre desde `nucleo/` con el venv del núcleo.
"""
from __future__ import annotations

import argparse
import os
import sys

from fabrica import expediente, linea


def main(argv: list[str] | None = None, mundo: linea.Mundo | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m fabrica", description="La fábrica: de una idea a un PR en borrador.")
    sub = parser.add_subparsers(dest="orden", required=True)
    p_pedir = sub.add_parser("pedir", help="crea el pedido y corre el Planificador")
    p_pedir.add_argument("idea")
    p_pedir.add_argument("--base", default="main", help="rama de partida (main por defecto; siempre se toma la de origin)")
    p_responder = sub.add_parser("responder", help="contesta las preguntas del Planificador y rehace la spec")
    p_responder.add_argument("id")
    p_responder.add_argument("respuesta", nargs="?", default="")
    p_aprobar = sub.add_parser("aprobar", help="aprueba la spec y corre hasta el PR")
    p_aprobar.add_argument("id")
    p_aprobar.add_argument("--de-noche", action="store_true", help="aprueba sin construir: lo hace la próxima noche")
    p_encolar = sub.add_parser("encolar", help="deja el pedido para la noche sin gastar ahora")
    p_encolar.add_argument("idea")
    p_encolar.add_argument("--base", default="main")
    sub.add_parser("noche", help="corre un pedido de la cola (lo usa launchd)")
    sub.add_parser("cola", help="la cola en SQLite: pedido, estado y si es de la noche")
    p_ver = sub.add_parser("ver", help="lista los pedidos o muestra uno")
    p_ver.add_argument("id", nargs="?")
    args = parser.parse_args(argv)
    # La fábrica corre desde su casa (un worktree): sin esto, el consumo y la cola
    # irían a un remi.db suelto dentro del worktree y el panel vería 0 tokens.
    os.environ.setdefault("REMI_DB_PATH", str(expediente.repo_principal() / "nucleo" / "remi.db"))
    try:
        if args.orden == "pedir":
            id_ = linea.pedir(args.idea, args.base, mundo)
            datos = expediente.leer(id_)
            print(f"Pedido {id_} · {datos['meta']['estado']}\n\n{datos['secciones']['Spec']}")
        elif args.orden == "responder":
            print(f"Pedido {args.id} · {linea.responder(args.id, args.respuesta, mundo)}")
        elif args.orden == "aprobar" and args.de_noche:
            print(f"Pedido {args.id} · {linea.aprobar_de_noche(args.id)} · lo construye la próxima noche")
        elif args.orden == "aprobar":
            print(f"Pedido {args.id} · {linea.aprobar(args.id, mundo)}")
        elif args.orden == "encolar":
            print(f"Pedido {linea.encolar(args.idea, args.base)} · en la cola de la noche")
        elif args.orden == "noche":
            accion, id_ = linea.noche(mundo)
            print("Nada para la noche." if accion == "nada" else f"Noche: {accion} {id_} · {expediente.leer(id_)['meta']['estado']}")
        elif args.orden == "cola":
            from fabrica import cola

            filas = cola.listar()
            print("La cola está vacía." if not filas else "\n".join(
                f"{f['pedido']} · {f['estado']}{' · noche' if f['noche'] else ''} · {f['idea'][:70]}" for f in filas))
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

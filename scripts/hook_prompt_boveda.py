#!/usr/bin/env python3
"""Hook UserPromptSubmit de Claude Code: antes de que Claude piense, la bóveda
responde. Busca lo que ya tenemos (mente/ y la bóveda) sobre lo que
Juan Camilo acaba de escribir y se lo pone a Claude en el contexto, con la
instrucción de usarlo antes de investigar en la web o abrir un repo.

Cero tokens, cero red: es FTS local sobre markdown. Si no hay nada relevante
no imprime nada. Si algo falla, sale 0 en silencio: una sesión nunca se rompe
por esto.
"""
import json
import re
import sys
from pathlib import Path

VACIAS = frozenset(
    "para como esta este esta estos estas pero donde cuando sobre entre hasta desde porque"
    " that this with from what which would could should there their about into then than"
    " puedo quiero hazme dame dime mira revisa crea haz pues entonces tambien ahora algo"
    " sirve sirven mejor cual cuales tengo tiene tienen vamos hacer hace".split()
)
MAX_CARACTERES = 1400
GITHUB = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
URL = re.compile(r"https?://\S+")


def _plano(texto: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))


def consulta_de(prompt: str) -> str:
    sin_urls = URL.sub(" ", prompt.lower())
    palabras = [p for p in re.findall(r"[a-záéíóúñü0-9][a-záéíóúñü0-9_-]{3,}", sin_urls) if p not in VACIAS]
    vistas: dict[str, None] = {}
    for p in palabras:
        vistas.setdefault(p, None)
    return " ".join(list(vistas)[:8])


def fichas_de_repos(prompt: str, mente: Path | None) -> list[str]:
    if mente is None:
        return []
    salida = []
    for owner, repo in GITHUB.findall(prompt):
        ficha = mente / "mundo" / "repos" / f"{owner.lower()}-{repo.lower().removesuffix('.git')}.md"
        if ficha.exists():
            texto = ficha.read_text(encoding="utf-8", errors="replace")
            veredicto = re.search(r"^veredicto:\s*(.+)$", texto, re.M)
            salida.append(f"{owner}/{repo}: ya tiene ficha en la bóveda ({ficha.relative_to(mente)})"
                          + (f", veredicto: {veredicto.group(1).strip()}" if veredicto else ""))
    return salida


def contexto(prompt: str, buscar, mente: Path | None) -> str | None:
    q = consulta_de(prompt)
    repos = fichas_de_repos(prompt, mente)
    terminos = q.split()
    hallazgos = []
    if len(terminos) >= 2:
        minimo = 2 if len(terminos) >= 3 else 1
        for ruta, frag in buscar(q, n=10):
            plano = _plano(f"{ruta} {frag}")
            if sum(1 for t in terminos if _plano(t) in plano) >= minimo:
                hallazgos.append((ruta, frag))
            if len(hallazgos) == 4:
                break
    if not hallazgos and not repos:
        return None
    partes = ["LA BÓVEDA YA TIENE ALGO SOBRE ESTO (Remi). Léelo antes de buscar en la web, abrir un repo o preguntarle a Juan Camilo; si lo usas, di de qué nota salió."]
    partes += [f"- {r}" for r in repos]
    partes += [f"- {ruta}: {frag}" for ruta, frag in hallazgos]
    texto = "\n".join(partes)
    return texto[:MAX_CARACTERES]


def main() -> int:
    try:
        datos = json.load(sys.stdin)
        prompt = str(datos.get("prompt") or "")
        sesion = str(datos.get("session_id") or "-")
        if len(prompt) < 12 or prompt.startswith("/"):
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nucleo"))
        import vida

        # Router (F1.3): primero el índice único con umbral; si no existe todavía,
        # la búsqueda vieja sobre markdown. Fichas, nunca cuerpos; ≤ ~600 tokens.
        fichas = vida.buscar_indice(prompt, n=4)
        repos = fichas_de_repos(prompt, vida.MENTE)
        if fichas or repos:
            ctx = vida.fichas_para_contexto(fichas)
            if repos:
                ctx += "\n" + "\n".join(f"- {r}" for r in repos)
            ctx = ctx[:vida.PRESUPUESTO_HOOK]
            ids = [f["id"] for f in fichas]
        elif not (vida.MENTE / "indice.db").exists():
            ctx = contexto(prompt, vida.buscar, vida.MENTE)
            ids = ["(fts-markdown)"] if ctx else []
        else:
            ctx, ids = None, []
        try:
            import metricas
            metricas.registrar_consulta("hook", sesion, consulta_de(prompt), ids, len(ctx or ""))
        except Exception:
            pass
        if ctx:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}, ensure_ascii=False))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

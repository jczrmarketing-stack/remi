"""La línea: de la idea al PR en borrador, con todo lo de afuera inyectado."""

import json

import pytest

from fabrica import agentes, expediente, linea
from fabrica.agentes import Salida

SPEC = Salida("hecho", "spec lista", {"spec": "Cambiar X", "escenarios": ["cuando A entonces B"], "preguntas": [],
                                      "toca": ["nucleo/x.py"], "riesgo": "bajo"})
TESTS = Salida("hecho", "tests listos", {"tests": ["nucleo/pruebas/test_x.py"], "resumen": "prueba A→B"})
CONSTRUIDO = Salida("hecho", "listo", {"resumen": "cambié x", "archivos": ["nucleo/x.py"]})
LIMPIO = Salida("hecho", "revisado", {"hallazgos": []})


class MundoFalso:
    def __init__(self, raiz, salidas=None, verificar=(0, "todo pasa"), pytest_rc=1, tokens=0):
        self.raiz = raiz
        self.salidas = {"planificador": [SPEC], "tester": [TESTS], "constructor": [CONSTRUIDO], "revisor": [LIMPIO],
                        **(salidas or {})}
        self.llamadas: list[tuple[str, str | None]] = []
        self.comandos: list[list[str]] = []
        self.avisos: list[str] = []
        self.resultado_verificar = verificar
        self.pytest_rc = pytest_rc
        self.gastado = tokens

    def llamar(self, rol, mensaje, cwd, pedido, modelo=None):
        self.llamadas.append((rol, modelo))
        cola = self.salidas[rol]
        return cola.pop(0) if len(cola) > 1 else cola[0]

    def verificar(self, cwd, base):
        return self.resultado_verificar

    def sh(self, args, cwd):
        self.comandos.append(list(args))
        if "pytest" in args:
            return self.pytest_rc, "1 failed"
        if args[:3] == ["gh", "pr", "create"]:
            return 0, "https://github.com/jczrmarketing-stack/remi/pull/9"
        return 0, ""

    def mundo(self):
        return linea.Mundo(llamar=self.llamar, verificar=self.verificar, sh=self.sh, avisar=self.avisos.append,
                           raiz_repo=self.raiz, lecciones=lambda tarea: "", tokens=lambda pedido: self.gastado)

    def roles(self):
        return [rol for rol, _ in self.llamadas]


@pytest.fixture(autouse=True)
def pedidos(tmp_path, monkeypatch):
    monkeypatch.setattr(expediente, "RAIZ", tmp_path / "pedidos")


def _eventos(id_):
    ruta = expediente.carpeta(id_) / "eventos.jsonl"
    return [json.loads(l) for l in ruta.read_text().splitlines()] if ruta.exists() else []


def test_pedir_deja_la_spec_y_espera(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    datos = expediente.leer(id_)
    assert datos["meta"]["estado"] == "spec"
    assert datos["meta"]["toca"] == ["nucleo/x.py"]
    assert "cuando A entonces B" in datos["secciones"]["Spec"]
    assert falso.roles() == ["planificador"]
    assert f"aprobar {id_}" in falso.avisos[-1]
    assert ["git", "worktree", "add", str(tmp_path / ".worktrees" / f"pedido-{id_}"), "-b", f"fabrica/pedido-{id_}", "main"] in falso.comandos


def test_tope_de_tokens_corta_el_pedido(tmp_path):
    falso = MundoFalso(tmp_path, tokens=3_000_001)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert falso.llamadas == []
    assert "tope" in falso.avisos[-1]
    assert _eventos(id_)[-1]["tipo"] == "parada"


def test_no_puedo_detiene_la_linea(tmp_path):
    falso = MundoFalso(tmp_path, {"tester": [Salida("no_puedo", "no encuentro el módulo", {})]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    estado = linea.aprobar(id_, falso.mundo())
    assert estado == "aprobado"
    assert "constructor" not in falso.roles()
    assert "no encuentro el módulo" in falso.avisos[-1]


def test_necesito_dato_del_planificador_manda_las_preguntas(tmp_path):
    pregunta = Salida("necesito_dato", "falta saber algo", {"spec": "", "escenarios": [], "preguntas": ["¿Base main o verificador?"],
                                                            "toca": [], "riesgo": "bajo"})
    falso = MundoFalso(tmp_path, {"planificador": [pregunta]})
    linea.pedir("Arreglar X", "main", falso.mundo())
    assert "¿Base main o verificador?" in falso.avisos[-1]


def test_si_los_tests_ya_pasan_sale_necesito_dato(tmp_path):
    falso = MundoFalso(tmp_path, pytest_rc=0)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert "constructor" not in falso.roles()
    assert "ya pasan" in falso.avisos[-1]
    assert _eventos(id_)[-1]["tipo"] == "parada"


def test_verificador_que_falla_vuelve_al_constructor_maximo_dos_vueltas(tmp_path):
    falso = MundoFalso(tmp_path, verificar=(1, "tests_nucleo no pasa"))
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert falso.roles().count("constructor") == 3
    assert expediente.leer(id_)["meta"]["vueltas"] == 2
    assert not any(c[:3] == ["gh", "pr", "create"] for c in falso.comandos)
    assert "vueltas" in falso.avisos[-1]


def test_verificador_sin_herramienta_se_detiene(tmp_path):
    falso = MundoFalso(tmp_path, verificar=(2, "falta gitleaks"))
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert falso.roles().count("constructor") == 1
    assert "herramienta" in falso.avisos[-1]


def test_hallazgo_alto_devuelve_al_constructor(tmp_path):
    alto = Salida("hecho", "revisado", {"hallazgos": [{"nivel": "alto", "archivo": "nucleo/x.py", "linea": 3, "texto": "rompe A"}]})
    falso = MundoFalso(tmp_path, {"revisor": [alto, LIMPIO]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.roles().count("constructor") == 2
    assert expediente.leer(id_)["meta"]["vueltas"] == 1


def test_hallazgo_medio_no_devuelve(tmp_path):
    medio = Salida("hecho", "revisado", {"hallazgos": [{"nivel": "medio", "archivo": "nucleo/x.py", "linea": 3, "texto": "nombre raro"}]})
    falso = MundoFalso(tmp_path, {"revisor": [medio]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.roles().count("constructor") == 1
    assert "nombre raro" in expediente.leer(id_)["secciones"]["Revisión"]


def test_camino_feliz_abre_pr_en_borrador(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.roles() == ["planificador", "tester", "constructor", "revisor"]
    commit = next(c for c in falso.comandos if "commit" in c)
    assert "user.name=Fábrica INV3RZA" in commit and "user.email=fabrica@inv3rza.local" in commit
    assert ["git", "push", "-u", "origin", f"fabrica/pedido-{id_}"] in falso.comandos
    pr = next(c for c in falso.comandos if c[:3] == ["gh", "pr", "create"])
    assert "--draft" in pr and pr[pr.index("--base") + 1] == "main"
    assert "cuando A entonces B" in pr[pr.index("--body") + 1]
    assert expediente.leer(id_)["meta"]["estado"] == "pr"
    assert "pull/9" in falso.avisos[-1]


def test_riesgo_alto_construye_con_opus(tmp_path):
    alto = Salida("hecho", "spec", {**SPEC.datos, "riesgo": "alto"})
    falso = MundoFalso(tmp_path, {"planificador": [alto]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert ("constructor", agentes.config()["modelos"]["constructor_alto"]) in falso.llamadas


def test_segundo_pedido_mientras_corre_es_ocupada(tmp_path):
    falso = MundoFalso(tmp_path)
    with linea.candado():
        with pytest.raises(linea.Ocupada):
            linea.pedir("Otro", "main", falso.mundo())
    assert linea.pedir("Otro", "main", falso.mundo())


def test_aprobar_un_pedido_que_no_existe_da_keyerror(tmp_path):
    with pytest.raises(KeyError):
        linea.aprobar("no-existe", MundoFalso(tmp_path).mundo())


def test_aprobar_un_pedido_ya_en_pr_no_corre_nada(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    antes = len(falso.llamadas)
    with pytest.raises(ValueError):
        linea.aprobar(id_, falso.mundo())
    assert len(falso.llamadas) == antes

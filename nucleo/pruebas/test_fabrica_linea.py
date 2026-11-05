"""La línea: de la idea al PR en borrador, con todo lo de afuera inyectado."""

import json

import pytest

import coding

from fabrica import agentes, expediente, linea
from fabrica.agentes import Salida

SPEC = Salida("hecho", "spec lista", {"spec": "Cambiar X", "escenarios": ["cuando A entonces B"], "preguntas": [],
                                      "toca": ["nucleo/x.py"], "riesgo": "bajo"})
TESTS = Salida("hecho", "tests listos", {"tests": ["nucleo/pruebas/test_x.py"], "resumen": "prueba A→B"})
CONSTRUIDO = Salida("hecho", "listo", {"resumen": "cambié x", "archivos": ["nucleo/x.py"]})
LIMPIO = Salida("hecho", "revisado", {"hallazgos": []})


class MundoFalso:
    def __init__(self, raiz, salidas=None, verificar=(0, "todo pasa"), pytest_rc=1, tokens=0, pytest_despues=0, push_rc=None):
        self.raiz = raiz
        self.salidas = {"planificador": [SPEC], "tester": [TESTS], "constructor": [CONSTRUIDO], "revisor": [LIMPIO],
                        **(salidas or {})}
        self.llamadas: list[tuple[str, str | None]] = []
        self.comandos: list[list[str]] = []
        self.avisos: list[str] = []
        self.resultado_verificar = verificar
        self.pytest_rc = pytest_rc
        self.gastado = tokens
        self.pytest_despues = pytest_despues
        self.push_rc = list(push_rc or [0])
        self.commits = 0

    def llamar(self, rol, mensaje, cwd, pedido, modelo=None):
        self.llamadas.append((rol, modelo))
        cola = self.salidas[rol]
        salida = cola.pop(0) if len(cola) > 1 else cola[0]
        if isinstance(salida, Exception):
            raise salida
        return salida

    def verificar(self, cwd, base):
        return self.resultado_verificar

    def probar(self, args, cwd):
        self.comandos.append(["pytest", *args])
        rc = self.pytest_rc if "constructor" not in self.roles() else self.pytest_despues
        return rc, f"pytest salió {rc}"

    def sh(self, args, cwd):
        self.comandos.append(list(args))
        if "commit" in args:
            self.commits += 1
        if args[:2] == ["git", "log"]:
            return 0, "abc123 Fábrica: Arreglar X" if self.commits else ""
        if args[:2] == ["git", "push"]:
            rc = self.push_rc.pop(0) if len(self.push_rc) > 1 else self.push_rc[0]
            return rc, "" if rc == 0 else "rechazado"
        if args[:3] == ["gh", "pr", "create"]:
            return 0, "https://github.com/jczrmarketing-stack/remi/pull/9"
        return 0, ""

    def mundo(self):
        return linea.Mundo(llamar=self.llamar, verificar=self.verificar, sh=self.sh, probar=self.probar, avisar=self.avisos.append,
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


def test_verificador_sin_apps_corre_solo_python_y_seguridad():
    args = linea.revisiones_para(["nucleo/x.py", "nucleo/pruebas/test_x.py"])
    assert args[0] == "--solo"
    assert set(args[1:]) == {"secretos", "tests_nucleo", "tipos_nucleo", "tests_agentes", "codigo_peligroso", "dependencias"}


def test_verificador_con_apps_corre_todo():
    assert linea.revisiones_para(["nucleo/x.py", "apps/panel/src/app/page.tsx"]) == ["--todo"]


# — Arreglos de la revisión final (4-nov) —

def test_reintento_despues_de_las_vueltas_retoma_sin_tester(tmp_path):
    falso = MundoFalso(tmp_path, verificar=(1, "no pasa"))
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert expediente.leer(id_)["meta"]["estado"] == "construyendo"
    falso.resultado_verificar = (0, "pasa")
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.roles().count("tester") == 1


def test_reintento_despues_de_un_push_fallido_no_repite_el_commit(tmp_path):
    falso = MundoFalso(tmp_path, push_rc=[1, 0])
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert linea.aprobar(id_, falso.mundo()) == "revisando"
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.commits == 1
    assert falso.roles().count("constructor") == 1


def test_responder_al_planificador_rehace_la_spec(tmp_path):
    pregunta = Salida("necesito_dato", "falta saber algo", {"spec": "", "escenarios": [], "preguntas": ["¿Base main?"],
                                                            "toca": [], "riesgo": "bajo"})
    falso = MundoFalso(tmp_path, {"planificador": [pregunta, SPEC]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert expediente.leer(id_)["meta"]["estado"] == "idea"
    (tmp_path / ".worktrees" / f"pedido-{id_}").mkdir(parents=True)
    assert linea.responder(id_, "Sí, main.", falso.mundo()) == "spec"
    assert "Sí, main." in expediente.leer(id_)["secciones"]["Contexto"]
    assert sum(1 for c in falso.comandos if c[:3] == ["git", "worktree", "add"]) == 1
    assert f"aprobar {id_}" in falso.avisos[-1]


def test_limite_de_max_detiene_con_aviso_sin_traceback(tmp_path):
    falso = MundoFalso(tmp_path, {"tester": [coding.LimiteDeMax("tester")]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    assert linea.aprobar(id_, falso.mundo()) == "aprobado"
    assert "límite" in falso.avisos[-1]
    assert _eventos(id_)[-1]["tipo"] == "parada"


def test_tests_que_no_se_pueden_correr_paran(tmp_path):
    falso = MundoFalso(tmp_path, pytest_rc=4)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert "constructor" not in falso.roles()
    assert "no se pudieron correr" in falso.avisos[-1]


@pytest.mark.parametrize("ruta", ["../fuera/test_x.py", "/etc/test_x.py", "--basetemp=/Users", "-p"])
def test_tests_fuera_del_worktree_paran(tmp_path, ruta):
    falso = MundoFalso(tmp_path, {"tester": [Salida("hecho", "t", {"tests": [ruta], "resumen": ""})]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert not any("pytest" in c for c in falso.comandos)
    assert "constructor" not in falso.roles()


def test_tests_que_siguen_fallando_despues_de_construir_cuentan_vuelta(tmp_path):
    falso = MundoFalso(tmp_path, pytest_despues=1)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    assert falso.roles().count("constructor") == 3
    assert not any(c[:3] == ["gh", "pr", "create"] for c in falso.comandos)


def test_el_aviso_usa_el_chat_del_checkout_principal(tmp_path, monkeypatch):
    import alertas
    (tmp_path / "nucleo").mkdir()
    (tmp_path / "nucleo" / ".env").write_text("TELEGRAM_CHAT_ID=12345\n")
    monkeypatch.setattr(linea, "_repo_principal", lambda: tmp_path)
    monkeypatch.delenv("ALERTAS_CHAT_ID", raising=False)
    visto = {}
    monkeypatch.setattr(alertas, "enviar", lambda texto, post=None: visto.update(chat=__import__("os").environ.get("ALERTAS_CHAT_ID"), texto=texto))
    linea._avisar_real("hola")
    assert visto == {"chat": "12345", "texto": "Fábrica · hola"}

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


def _archivo(raiz, id_, rel, lineas):
    """El Revisor solo cuenta lo que existe: el archivo que cita tiene que estar en el worktree."""
    ruta = linea.worktree(raiz, id_) / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("".join(f"x = {i}\n" for i in range(lineas)))


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
    _archivo(tmp_path, id_, "nucleo/x.py", 5)
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.roles().count("constructor") == 2
    assert expediente.leer(id_)["meta"]["vueltas"] == 1


def test_hallazgo_medio_no_devuelve(tmp_path):
    medio = Salida("hecho", "revisado", {"hallazgos": [{"nivel": "medio", "archivo": "nucleo/x.py", "linea": 3, "texto": "nombre raro"}]})
    falso = MundoFalso(tmp_path, {"revisor": [medio]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    _archivo(tmp_path, id_, "nucleo/x.py", 5)
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


# — Mejora 3 (6-nov): misión, reglas y «partir» —

def test_partir_manda_un_pedido_por_parte_y_no_construye(tmp_path):
    partir = Salida("partir", "son dos cambios", {"spec": "", "escenarios": [], "preguntas": [], "toca": [], "riesgo": "bajo",
                                                 "como_se_demuestra": "", "partes": ["Arreglar A en x.py", "Arreglar B en y.py"]})
    falso = MundoFalso(tmp_path, {"planificador": [partir]})
    id_ = linea.pedir("Arreglar A y B", "main", falso.mundo())
    aviso = falso.avisos[-1]
    assert "son dos cambios" in aviso
    assert 'pedir "Arreglar A en x.py"' in aviso and 'pedir "Arreglar B en y.py"' in aviso
    assert expediente.leer(id_)["meta"]["estado"] == "idea"


def test_fuera_de_alcance_lo_dice_y_para(tmp_path):
    fuera = Salida("fuera_de_alcance", "es una pantalla nueva: va por mockup", {"spec": "", "escenarios": [], "preguntas": [],
                   "toca": [], "riesgo": "bajo", "como_se_demuestra": "", "partes": []})
    falso = MundoFalso(tmp_path, {"planificador": [fuera]})
    id_ = linea.pedir("Hacer la pantalla de la línea", "main", falso.mundo())
    assert "mockup" in falso.avisos[-1] and "fuera_de_alcance" in falso.avisos[-1]
    assert expediente.leer(id_)["meta"]["estado"] == "idea"


def test_la_spec_lleva_como_se_demuestra(tmp_path):
    con_prueba = Salida("hecho", "spec lista", {**SPEC.datos, "como_se_demuestra": "corre test_x y muestra B en la salida",
                                                 "partes": []})
    falso = MundoFalso(tmp_path, {"planificador": [con_prueba]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    spec = expediente.leer(id_)["secciones"]["Spec"]
    assert "Cómo se demuestra:\ncorre test_x y muestra B en la salida" in spec


# — Mejora 2 (6-nov): escenarios ocultos que el Constructor no ve —

OCULTO = "nucleo/pruebas/test_x_oculto.py"


class MundoConOcultos(MundoFalso):
    """El Tester deja un test visible y uno oculto en el worktree; el oculto pasa o falla según `ocultos`."""

    def __init__(self, raiz, ocultos=(1, 0), oculto_antes=1, **kw):
        super().__init__(raiz, **kw)
        self.ocultos = list(ocultos)
        self.oculto_antes = oculto_antes
        self.visto_por_constructor: list[bool] = []
        self.mensajes: list[str] = []
        self.al_constructor: list[str] = []

    def wt(self, pedido):
        return linea.worktree(self.raiz, pedido)

    def llamar(self, rol, mensaje, cwd, pedido, modelo=None):
        self.mensajes.append(mensaje)
        if rol == "tester":
            (cwd / "nucleo" / "pruebas").mkdir(parents=True, exist_ok=True)
            (cwd / "nucleo" / "pruebas" / "test_x.py").write_text("def test_a(): assert False\n")
            (cwd / OCULTO).write_text("def test_oculto_b(): assert False  # secreto\n")
            return Salida("hecho", "tests listos", {"tests": ["nucleo/pruebas/test_x.py"], "ocultos": [OCULTO], "resumen": "A y B"})
        if rol == "constructor":
            self.visto_por_constructor.append((cwd / OCULTO).exists())
            self.al_constructor.append(mensaje)
        return super().llamar(rol, mensaje, cwd, pedido, modelo)

    def probar(self, args, cwd):
        if args == [OCULTO]:
            assert (cwd / OCULTO).exists(), "el oculto tiene que estar en el worktree mientras corre"
            if "constructor" not in self.roles():
                return self.oculto_antes, "1 failed"
            rc = self.ocultos.pop(0) if len(self.ocultos) > 1 else self.ocultos[0]
            return rc, ("FAILED nucleo/pruebas/test_x_oculto.py::test_oculto_b - AssertionError: secreto" if rc else "1 passed")
        return super().probar(args, cwd)


def test_el_constructor_nunca_ve_el_oculto_y_el_pr_lo_trae(tmp_path):
    falso = MundoConOcultos(tmp_path, ocultos=[0])
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    (falso.wt(id_)).mkdir(parents=True, exist_ok=True)
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.visto_por_constructor == [False]
    assert (falso.wt(id_) / OCULTO).exists()                       # vuelve al worktree antes del commit
    assert "Ocultos: nucleo/pruebas/test_x_oculto.py" in expediente.leer(id_)["secciones"]["Tests"]
    assert not any("secreto" in m for m in falso.mensajes)


def test_si_el_oculto_falla_vuelve_al_constructor_solo_con_el_nombre(tmp_path):
    falso = MundoConOcultos(tmp_path, ocultos=[1, 0], salidas={"constructor": [CONSTRUIDO, CONSTRUIDO]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    falso.wt(id_).mkdir(parents=True, exist_ok=True)
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.visto_por_constructor == [False, False]
    segundo = falso.al_constructor[-1]
    assert "test_oculto_b" in segundo and "secreto" not in segundo and "assert False" not in segundo
    assert expediente.leer(id_)["meta"]["vueltas"] == 1


def test_un_oculto_que_ya_pasa_antes_de_construir_no_prueba_nada(tmp_path):
    falso = MundoConOcultos(tmp_path, oculto_antes=0)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    falso.wt(id_).mkdir(parents=True, exist_ok=True)
    linea.aprobar(id_, falso.mundo())
    assert "constructor" not in falso.roles()
    assert "ocultos ya pasan" in falso.avisos[-1]


def test_sin_ocultos_el_pr_dice_que_ese_control_no_corrio(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    cuerpo = next(c for c in falso.comandos if c[:3] == ["gh", "pr", "create"])[-1]
    assert "Escenarios ocultos: ninguno (este control no corrió)" in cuerpo



# — Mejoras 1 y 5 (6-nov): controles visibles y hallazgos contrastados —

def _hallazgo(nivel, archivo, linea_, texto):
    return {"nivel": nivel, "archivo": archivo, "linea": linea_, "texto": texto}


def test_hallazgo_alto_sobre_codigo_que_no_existe_se_descarta_y_no_devuelve(tmp_path):
    inventado = Salida("hecho", "revisado", {"hallazgos": [_hallazgo("alto", "nucleo/no_existe.py", 3, "rompe todo"),
                                                           _hallazgo("alto", "nucleo/x.py", 99, "línea fuera del archivo")]})
    falso = MundoFalso(tmp_path, {"revisor": [inventado]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    _archivo(tmp_path, id_, "nucleo/x.py", 5)
    assert linea.aprobar(id_, falso.mundo()) == "pr"
    assert falso.roles().count("constructor") == 1
    revision = expediente.leer(id_)["secciones"]["Revisión"]
    assert "Descartados (citan código que no existe)" in revision and "nucleo/no_existe.py:3" in revision


def test_hallazgos_ordenados_por_gravedad(tmp_path):
    revuelto = Salida("hecho", "revisado", {"hallazgos": [_hallazgo("bajo", "nucleo/x.py", 1, "estilo"),
                                                          _hallazgo("medio", "nucleo/x.py", 2, "nombre raro")]})
    falso = MundoFalso(tmp_path, {"revisor": [revuelto]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    _archivo(tmp_path, id_, "nucleo/x.py", 5)
    linea.aprobar(id_, falso.mundo())
    revision = expediente.leer(id_)["secciones"]["Revisión"]
    assert revision.index("[medio]") < revision.index("[bajo]")


def test_riesgo_alto_revisa_un_modelo_distinto_al_que_construye(tmp_path):
    alto = Salida("hecho", "spec", {**SPEC.datos, "riesgo": "alto"})
    falso = MundoFalso(tmp_path, {"planificador": [alto]})
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    modelos = dict(falso.llamadas)
    assert modelos["revisor"] and modelos["revisor"] != modelos["constructor"]


def test_el_pr_lista_cada_control_y_su_resultado(tmp_path):
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    cuerpo = next(c for c in falso.comandos if c[:3] == ["gh", "pr", "create"])[-1]
    controles = cuerpo[cuerpo.index("## Controles"):]
    for linea_ in ("Verificador (--solo secretos, tests_nucleo", "salida 0", "Tests del Tester: nucleo/pruebas/test_x.py, pasan",
                   "Escenarios ocultos: ninguno (este control no corrió)", "Revisor (sonnet): 0 hallazgos"):
        assert linea_ in controles, linea_


def test_las_comas_de_la_spec_sobreviven_en_el_pr(tmp_path):
    """Antes, el formato de los tokens cambiaba todas las comas del cuerpo por puntos."""
    con_comas = Salida("hecho", "spec", {**SPEC.datos, "spec": "Cambiar X, Y y Z"})
    falso = MundoFalso(tmp_path, {"planificador": [con_comas]}, tokens=1234567)
    id_ = linea.pedir("Arreglar X", "main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    cuerpo = next(c for c in falso.comandos if c[:3] == ["gh", "pr", "create"])[-1]
    assert "Cambiar X, Y y Z" in cuerpo and "Tokens: 1.234.567" in cuerpo


def test_con_base_origin_main_el_pr_va_contra_main(tmp_path):
    """6-nov: el main local puede quedar atrás; la fábrica parte de origin/main y abre el PR contra main."""
    falso = MundoFalso(tmp_path)
    id_ = linea.pedir("Arreglar X", "origin/main", falso.mundo())
    linea.aprobar(id_, falso.mundo())
    pr = next(c for c in falso.comandos if c[:3] == ["gh", "pr", "create"])
    assert pr[pr.index("--base") + 1] == "main"
    assert ["git", "worktree", "add", str(linea.worktree(tmp_path, id_)), "-b", f"fabrica/pedido-{id_}", "origin/main"] in falso.comandos

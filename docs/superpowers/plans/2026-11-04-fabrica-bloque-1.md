# Fábrica v1 (Bloque 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (en línea, decidido por Milo). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un pedido entra por `python3 -m fabrica pedir "<idea>"` y sale como PR en borrador, con traza, tope de tokens y eventos en vivo para el piso Ingeniería.

**Architecture:** Paquete `nucleo/fabrica/` (expediente, agentes, línea, CLI, rutas) que llama a `claude -p` con `stream-json` + `--json-schema` + `--settings` (Portero). Todo lo de afuera (CLI, verificador, git, aviso) se inyecta en `linea.py` para probar sin red. El Portero es un hook PreToolUse en Python, 0 tokens.

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest; `claude` CLI (Max); Next.js para el panel (solo después del OK del mockup).

**Spec:** `~/.claude/plans/proud-spinning-nygaard.md` (manda) · `docs/fabrica/PLAN.md` · `.workflow/scratch/bloque1-recon.md`

## Global Constraints

- Python de pruebas: `PY=/Users/juancamilo/proyectos/remi/nucleo/.venv/bin/python`; se corre desde `nucleo/`: `$PY -m pytest pruebas/<archivo> -q`.
- `mypy` estricto del núcleo debe seguir pasando (`$PY -m mypy .` desde `nucleo/`, frente a la línea base).
- Estados del expediente: `idea · spec · aprobado · construyendo · revisando · pr · cerrado`.
- Riesgo: `bajo · medio · alto`. Hallazgos: `alto · medio · bajo`. Salida de agente: `estado: hecho | no_puedo | necesito_dato` + `motivo`.
- Topes: 30 turnos por agente, 2 vueltas, 1 pedido a la vez, 3 000 000 tokens por pedido (`config/fabrica.json`).
- Modelos: Planificador `opus`; Tester `sonnet`; Constructor `sonnet` (`opus` si `riesgo: alto`); Revisor `sonnet`.
- Commit de la fábrica: `-c user.name="Fábrica INV3RZA" -c user.email=fabrica@inv3rza.local`. Los agentes nunca hacen commit ni push.
- `fabrica/pedidos/` y `.worktrees/` ignorados en git. Nada se fusiona a `main`.
- Textos en español; voz de Remi en avisos: sin urgencia, sin contar fallos.
- Un commit por tarea, mensaje en español, imperativo, con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Salida de la CLI sin `structured_output`** (rota, vacía, límite de Max): `agentes.llamar` devuelve `Salida(estado="no_puedo")`, nunca levanta salvo `LimiteDeMax`. Test en Task 4.
2. **Pedido que no existe** en `aprobar`/`ver`/rutas: error claro (`KeyError` → 404), no traceback. Tests en Tasks 2 y 7.
3. **Segundo pedido mientras otro corre**: el candado lo rechaza con mensaje, no lo encola. Test en Task 5.
4. **`eventos?desde=N` con N mayor que el total o negativo**: lista vacía / desde 0, no 500. Test en Task 7.
5. **Portero con rutas relativas o `..`** que escapan del worktree (`../../x`, `~/x`): se niegan. Test en Task 3.

---

### Task 1: Traza y tope por pedido en `consumo.py`

**Files:**
- Modify: `nucleo/consumo.py` (ESQUEMA, `registrar`, nueva `tokens_del_pedido`, `resumen_por_pedido`, `texto_semana`, `main`)
- Test: `nucleo/pruebas/test_consumo_pedido.py`

**Interfaces:**
- Produces: `registrar(agente, modelo, segundos, salida=None, returncode=0, error=None, ruta=None, ahora=None, pedido: str | None = None) -> None`; `tokens_del_pedido(pedido: str, ruta: Path | None = None) -> int`; `resumen_por_pedido(ruta=None, dias=7, ahora=None) -> list[dict]` (claves `pedido, llamadas, tokens`).

- [ ] **Step 1: Tests que fallan**
  - `test_registrar_guarda_el_pedido`: registrar con `pedido="p1"` y salida `{"result":"ok","usage":{"input_tokens":10,"output_tokens":5}}` → `tokens_del_pedido("p1", ruta) == 15`; otro pedido → 0.
  - `test_migra_una_tabla_vieja_sin_columna_pedido`: crear la tabla con el ESQUEMA viejo (sin `pedido`) e insertar una fila; `registrar(..., pedido="p2")` agrega la columna sin perder la fila; `tokens_del_pedido("p2")` > 0.
  - `test_sin_base_tokens_del_pedido_es_cero`: ruta inexistente → 0.
  - `test_semana_muestra_por_pedido`: dos filas de `p1` y una sin pedido → `resumen_por_pedido` trae solo `p1` con `llamadas == 2`; `texto_semana(resumen_semana(r), resumen_por_pedido(r))` contiene `"por pedido"` y `"p1"`.
- [ ] **Step 2:** `$PY -m pytest pruebas/test_consumo_pedido.py -q` → FAIL (argumento `pedido` inexistente).
- [ ] **Step 3:** Implementar. Migración: tras `executescript(ESQUEMA)`, `PRAGMA table_info(consumo_claude)`; si falta `pedido`, `ALTER TABLE consumo_claude ADD COLUMN pedido TEXT` + `CREATE INDEX IF NOT EXISTS idx_consumo_claude_pedido`. Helper `_abrir(ruta) -> sqlite3.Connection` que hace ambas cosas. `texto_semana(resumen, por_pedido=None)`: si hay `por_pedido`, agrega bloque `"\n\npor pedido\n"` con `pedido  llamadas  tokens`.
- [ ] **Step 4:** Mismo comando + `pruebas/test_consumo.py pruebas/test_consumo_semana.py` → PASS.
- [ ] **Step 5:** Commit `Consumo: cada fila sabe de qué pedido es y el tope se mide por pedido`.

### Task 2: Expediente

**Files:**
- Create: `nucleo/fabrica/__init__.py` (vacío con docstring), `nucleo/fabrica/expediente.py`
- Modify: `.gitignore` (agrega `fabrica/pedidos/` y `.worktrees/`)
- Test: `nucleo/pruebas/test_fabrica_expediente.py`

**Interfaces:**
- Produces: `RAIZ: Path` (= `<repo>/fabrica/pedidos`, sobreescribible con `FABRICA_PEDIDOS`); `ESTADOS: tuple[str, ...]`; `SECCIONES = ("Contexto","Spec","Tests","Construcción","Escáneres","Revisión","Fuera de tarea","Decisión")`; `crear(idea: str, repo: str, base: str, raiz: Path | None = None) -> str` (id `AAAAMMDD-HHMM-<slug≤24>`); `leer(id, raiz=None) -> dict` con `{"meta": {...}, "secciones": {nombre: texto}}` (levanta `KeyError` si no existe); `escribir_seccion(id, seccion, texto, raiz=None)`; `cambiar_estado(id, estado, raiz=None)`; `cambiar(id, raiz=None, **campos)` (toca, riesgo, vueltas, rama); `carpeta(id, raiz=None) -> Path`; `listar(raiz=None) -> list[dict]` (meta de cada uno, el más nuevo primero).
- Frontmatter: `pedido, repo, rama, base, estado, toca, riesgo, vueltas` (`base` se agrega al SOP: la línea la necesita para verificar y abrir el PR). `toca` es lista en una línea `[a, b]`.

- [ ] **Step 1: Tests que fallan**
  - `test_crear_deja_estado_idea_y_las_ocho_secciones` (Contexto contiene la idea; `meta["estado"] == "idea"`, `vueltas == 0`, `rama == f"fabrica/pedido-{id}"`).
  - `test_escribir_seccion_reemplaza_solo_esa`.
  - `test_cambiar_estado_rechaza_uno_desconocido` (`ValueError` con `"produccion"`).
  - `test_leer_un_pedido_que_no_existe_da_keyerror`.
  - `test_toca_y_riesgo_viajan_ida_y_vuelta` (`cambiar(id, toca=["nucleo/consumo.py"], riesgo="medio")`).
- [ ] **Step 2:** correr → FAIL (módulo no existe).
- [ ] **Step 3:** Implementar sin YAML externo: frontmatter clave: valor, listas `[a, b]`, enteros para `vueltas`. Escritura atómica (`tmp` + `os.replace`).
- [ ] **Step 4:** correr → PASS.
- [ ] **Step 5:** Commit `Fábrica: expediente por pedido con el frontmatter del SOP`.

### Task 3: Portero

**Files:**
- Create: `fabrica/portero/portero.py`, `fabrica/portero/settings.json`
- Test: `nucleo/pruebas/test_fabrica_portero.py` (carga el módulo por ruta con `importlib.util`)

**Interfaces:**
- Produces: `decidir(evento: dict, worktree: Path) -> str | None` (motivo si niega, `None` si deja pasar); `main() -> int` lee el evento del hook por stdin, worktree de `FABRICA_WORKTREE`; si niega imprime `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":motivo}}` y sale 0. Sin `FABRICA_WORKTREE` niega todo lo que escribe.
- `settings.json`: `{"hooks":{"PreToolUse":[{"matcher":"Bash|Edit|Write|MultiEdit|NotebookEdit","hooks":[{"type":"command","command":"python3 \"$FABRICA_PORTERO\""}]}]}}`.

- [ ] **Step 1: Tests que fallan** (parametrizados, `evento = {"tool_name":..., "tool_input":...}`)
  - Niega Bash: `git push`, `git push --force origin x`, `git commit -m x`, `rm -rf build`, `git branch -D x`, `git reset --hard`, `vercel deploy`, `npm publish`, `cd /tmp && echo x > a`.
  - Deja Bash: `/ruta/.venv/bin/python -m pytest nucleo/pruebas/test_x.py -q`, `git status`, `git diff`, `ls`.
  - Niega Write/Edit con `file_path` fuera del worktree: `/etc/x`, `<wt>/../otro/a.py`, `~/x`; deja `<wt>/nucleo/a.py` y relativo `nucleo/a.py`.
  - `test_main_imprime_deny_en_json` (monkeypatch stdin/env, capsys).
- [ ] **Step 2:** correr → FAIL.
- [ ] **Step 3:** Implementar con regex sobre el comando (`\bgit\s+(push|commit|branch\s+-D|reset\s+--hard|checkout\s+main)\b`, `\brm\s+-[a-z]*r`, `--force`, `deploy|publish`, redirección `>` a una ruta absoluta fuera del worktree) y `Path(...).expanduser().resolve()` + `is_relative_to(worktree.resolve())` para rutas.
- [ ] **Step 4:** correr → PASS.
- [ ] **Step 5:** Commit `Fábrica: el Portero niega push, borrados, despliegues y escrituras fuera del worktree`.

### Task 4: Agentes de la línea

**Files:**
- Create: `nucleo/fabrica/agentes.py`, `fabrica/agentes/planificador.md`, `fabrica/agentes/tester.md`, `fabrica/agentes/constructor.md`, `fabrica/agentes/revisor.md`, `config/fabrica.json`
- Test: `nucleo/pruebas/test_fabrica_agentes.py`

**Interfaces:**
- Consumes: `consumo.registrar(..., pedido=)` (Task 1); `expediente.carpeta(id)` (Task 2); `pensar._entorno`, `pensar.MODOS`, `pensar.PATRON_LIMITE_ALCANZADO`, `pensar.BINARIO`; `coding.LimiteDeMax`; `agentes_estado.avisar`.
- Produces: `Rol = Literal["planificador","tester","constructor","revisor"]`; `@dataclass Salida(estado: str, motivo: str, datos: dict, tokens: int)`; `ESQUEMAS: dict[Rol, dict]`; `config() -> dict` (lee `config/fabrica.json`); `comando(rol, modelo, cwd: Path) -> list[str]`; `eventos_de(linea: str, rol: str) -> list[dict]`; `llamar(rol, mensaje, cwd: Path, pedido: str, modelo: str | None = None, ejecutar: Ejecutar | None = None) -> Salida`; `Ejecutar = Callable[[list[str], str, Path, dict[str,str]], Iterator[str]]` (comando, stdin, cwd, env → líneas de stdout).
- `config/fabrica.json`: `{"tope_tokens_pedido": 3000000, "turnos": 30, "vueltas": 2, "segundos_por_agente": 1200, "modelos": {"planificador":"opus","tester":"sonnet","constructor":"sonnet","constructor_alto":"opus","revisor":"sonnet"}}`.
- Esquemas (todos con `estado` enum y `motivo` string requeridos): planificador + `spec` str, `escenarios` [str], `preguntas` [str] maxItems 3, `toca` [str], `riesgo` enum; tester + `tests` [str], `resumen` str; constructor + `resumen` str, `archivos` [str]; revisor + `hallazgos` [{`nivel` enum, `archivo`, `linea` int, `texto`}].
- Comando: `claude -p --model M --output-format stream-json --verbose --json-schema <json> --settings <ruta settings.json> --system-prompt <fabrica/agentes/<rol>.md + CLAUDE.md del worktree> --tools <herr> --allowedTools <herr> --strict-mcp-config --setting-sources "" --no-session-persistence --max-turns 30`. Lectura: `Read,Grep,Glob`; tester/constructor además `Edit,Write,Bash(<FABRICA_PY> -m pytest:*)`. Env: `pensar._entorno(...)` + `FABRICA_WORKTREE=<cwd>`, `FABRICA_PORTERO=<repo>/fabrica/portero/portero.py`. `FABRICA_PY` = env o `/Users/juancamilo/proyectos/remi/nucleo/.venv/bin/python`.
- Eventos en `expediente.carpeta(pedido)/eventos.jsonl`, uno por línea: `{"n", "rol", "tipo": texto|pensamiento|herramienta|resultado|fin, "texto", "herramienta"?, "en"}`; `resultado` recortado a 600 caracteres. Por cada herramienta, `agentes_estado.avisar(<programador|revisor>, "trabajando", ahora="<Rol>: <herramienta> <archivo o comando ≤60>")`.

- [ ] **Step 1: Tests que fallan** (con `ejecutar` falso que devuelve líneas stream-json grabadas)
  - `test_llamar_devuelve_la_salida_estructurada_y_cuenta_tokens` (evento `result` con `structured_output={"estado":"hecho","motivo":"m","spec":"s",...}` y `usage` → `Salida.estado=="hecho"`, `tokens` = suma; `consumo.tokens_del_pedido(pedido)` igual).
  - `test_llamar_guarda_eventos_de_texto_herramienta_y_resultado` (assistant con `text` + `tool_use{name:"Read",input:{file_path}}`, user con `tool_result` → 3 líneas en `eventos.jsonl` con `n` 0..2 y `tipo` correctos).
  - `test_salida_rota_es_no_puedo` (sin evento `result` → `estado=="no_puedo"`, motivo menciona la CLI).
  - `test_limite_de_max_levanta` (texto "usage limit" → `LimiteDeMax`).
  - `test_comando_trae_json_schema_settings_y_stream_json` (flags presentes; tester trae `Edit` y `Bash(`; planificador no trae `Edit`).
- [ ] **Step 2:** correr → FAIL.
- [ ] **Step 3:** Implementar. `ejecutar` real con `subprocess.Popen(..., stdout=PIPE, text=True)`, escribe stdin, itera `stdout` y mata el proceso pasado `segundos_por_agente`.
- [ ] **Step 4:** correr → PASS.
- [ ] **Step 5: Prueba real de la CLI** (riesgo del plan): `llamar("revisor", "Di hecho con motivo 'prueba'.", cwd=<tmp git>, pedido="humo", modelo="haiku")`. Esperado: `estado=="hecho"`. Si `structured_output` no llega, parsear el `result` como JSON (fallback) y anotarlo; si `--settings` no carga el hook, el Portero pasa a `--disallowedTools`.
- [ ] **Step 6:** Commit `Fábrica: los cuatro agentes con salida en JSON fijo, Portero y eventos en vivo`.

### Task 5: La línea

**Files:**
- Create: `nucleo/fabrica/linea.py`
- Test: `nucleo/pruebas/test_fabrica_linea.py`

**Interfaces:**
- Consumes: Tasks 1, 2, 4.
- Produces: `@dataclass Mundo(llamar, verificar, sh, avisar, raiz_repo: Path)` donde `llamar(rol, mensaje, cwd, pedido, modelo=None) -> Salida`, `verificar(cwd, base) -> tuple[int, str]` (código, `.verificar/ultimo.md`), `sh(args: list[str], cwd: Path) -> tuple[int, str]`, `avisar(texto) -> None`; `mundo_real() -> Mundo`; `pedir(idea: str, base: str = "main", mundo: Mundo | None = None) -> str` (id); `aprobar(id: str, mundo: Mundo | None = None) -> str` (estado final: `"pr"` o el estado donde se detuvo); `class Ocupada(Exception)`.
- Reglas, en orden: candado `fabrica/pedidos/.candado` (O_EXCL; existe → `Ocupada`), se suelta siempre en `finally`. Antes de cada agente, `tokens_del_pedido >= tope` → detiene y avisa. `no_puedo`/`necesito_dato` → detiene, avisa el `motivo` (y `preguntas` si las hay). Cada parada deja evento `{"tipo":"parada","texto":motivo}`.
- `pedir`: `git worktree add <raiz>/.worktrees/pedido-<id> -b fabrica/pedido-<id> <base>` → Planificador → secciones Spec (spec + escenarios + preguntas), `toca`, `riesgo`, estado `spec` → aviso con `python3 -m fabrica aprobar <id>`.
- `aprobar`: estado `aprobado` → Tester → `sh([FABRICA_PY,"-m","pytest",*tests,"-q"])` debe salir ≠0; si sale 0 → evento parada `necesito_dato` «los tests ya pasan». → `construyendo`: Constructor (modelo alto si `riesgo=="alto"`) → verificar: 1 → vuelve al Constructor con el `ultimo.md` (cuenta vuelta); 2 → para «falta herramienta». → `revisando`: Revisor una pasada con spec + `git diff <base>`; hallazgo `alto` → Constructor de nuevo (cuenta vuelta). `vueltas` > 2 → para y avisa. → `git add -A`, commit con identidad de la fábrica, `git push -u origin <rama>`, `gh pr create --draft --base <base> --head <rama> --title <idea≤70> --body <spec, escenarios, hallazgos>` → estado `pr`, aviso con la URL.

- [ ] **Step 1: Tests que fallan** (Mundo falso que graba llamadas)
  - `test_pedir_deja_la_spec_y_espera` (estado `spec`, aviso contiene `aprobar`, no llamó al Tester).
  - `test_tope_de_tokens_corta_el_pedido` (`tokens_del_pedido` monkeypatch → 3 000 001; no se llama al agente; aviso).
  - `test_no_puedo_detiene_la_linea`.
  - `test_si_los_tests_ya_pasan_sale_necesito_dato` (sh de pytest → 0; Constructor nunca llamado).
  - `test_verificador_que_falla_vuelve_al_constructor_maximo_dos_vueltas` (verificar siempre 1 → Constructor llamado 3 veces en total como máximo, `vueltas==2`, sin PR, aviso).
  - `test_hallazgo_medio_no_devuelve` (Revisor con un `medio` → PR creado, Constructor una sola vez).
  - `test_camino_feliz_abre_pr_en_borrador` (commit con `user.name=Fábrica INV3RZA`, `gh pr create --draft`, estado `pr`).
  - `test_segundo_pedido_mientras_corre_es_ocupada` (candado ya creado → `Ocupada`).
- [ ] **Step 2:** correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** correr → PASS.
- [ ] **Step 5:** Commit `Fábrica: la línea lleva un pedido de la idea al PR en borrador`.

### Task 6: CLI

**Files:**
- Create: `nucleo/fabrica/__main__.py`
- Test: `nucleo/pruebas/test_fabrica_cli.py`

**Interfaces:**
- Produces: `main(argv: list[str] | None = None, mundo=None) -> int`. `pedir "<idea>" [--base rama]` imprime id y la spec; `aprobar <id>`; `ver` lista `id · estado · idea`; `ver <id>` imprime el expediente. Pedido inexistente → stderr «No encuentro el pedido <id>.» y 1. `Ocupada` → «Ya hay un pedido corriendo.» y 1.

- [ ] **Step 1:** Tests: `test_ver_sin_pedidos`, `test_ver_pedido_inexistente_sale_1`, `test_pedir_imprime_el_id` (mundo falso).
- [ ] **Step 2:** FAIL. **Step 3:** argparse. **Step 4:** PASS.
- [ ] **Step 5:** Commit `Fábrica: python3 -m fabrica pedir | aprobar | ver`.

### Task 7: Rutas del núcleo

**Files:**
- Create: `nucleo/fabrica/rutas.py`
- Modify: `nucleo/servidor.py` (import + `app.include_router(fabrica.rutas.router)` junto a `coding.router`)
- Test: `nucleo/pruebas/test_fabrica_rutas.py` (TestClient sobre un `FastAPI()` con solo el router)

**Interfaces:**
- Produces: `GET /fabrica/pedidos` → `[meta…]`; `GET /fabrica/pedidos/{id}` → `leer(id)` + `tokens` + `tope` (404 si no existe); `GET /fabrica/pedidos/{id}/eventos?desde=N` → `{"eventos": [...], "siguiente": int}` (N<0 → 0; N> total → vacío).
- [ ] **Step 1:** Tests: lista, detalle, 404, eventos con `desde=1`, `desde=99`, `desde=-3`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS + `$PY -m pytest pruebas/test_servidor*.py -q` sigue igual.
- [ ] **Step 5:** Commit `Fábrica: el núcleo sirve pedidos y eventos para el panel`.

### Task 8: Mockup de «La línea» en el piso Ingeniería — PUERTA

- [ ] Leer `design/tokens.json` y el piso actual (`apps/panel/src/app/(suite)`), armar mockup HTML fiel (tema Noche, tokens del DS, estilo de la Suite): fila de estaciones Spec · Tests · Construir «vuelta N/2» · Verificar · PR; abajo, ve/hace/piensa/por qué de la activa y tokens frente al tope.
- [ ] Mostrarlo a Milo y **esperar su OK**. Sin OK no hay Task 9.

### Task 9: Panel (solo con OK)
- Se planea en detalle después del OK, sobre el mockup aprobado.

### Task 10: Los 3 pedidos reales
- [ ] `python3 -m fabrica pedir "<pedido>" --base <rama>` para: (1) tests de oficios que dependen de `conocimiento/`; (2) `test_notion_sync::test_el_estado_de_notion_no_ensucia_la_boveda`; (3) etapa real en el consumo de `coding.py` (`coding-spec`, `coding-builder`, `coding-revisor`).
- [ ] Milo aprueba cada spec (`aprobar <id>`); quedan 3 PRs en borrador.
- [ ] `python3 nucleo/consumo.py --semana` muestra los tokens por pedido.

## Verificación final
- `$PY -m pytest pruebas -q` y `scripts/verificar.sh --todo` frente a la línea base.
- Reversión: borrar rama `fabrica/bloque-1` y su worktree; cerrar los PRs en borrador.

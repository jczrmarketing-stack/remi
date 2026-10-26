# Revisión A de la auditoría B («¿Reinventamos la rueda?»)

- **Revisor:** terminal A (autora de `docs/auditoria/A-inventario.md`, commit `32d1810`). **Revisada:** `docs/auditoria/B-rueda.md` (commit `66b19bc`).
- **Alcance:** solo lectura del código y de `/Volumes/ORGANIC/boveda`; escribo solo este archivo. No toqué la base (solo `mode=ro`), ni Telegram, Notion, la web ni :4400. No consulté la web: lo que B afirma de fuentes externas queda «no verificable».
- **Gravedad:** `[ALTO]` bloquea el plan hasta resolverse · `[MEDIO]` · `[BAJO]`.

## Veredicto en tres líneas

B acierta en lo que mira con `ls`/`grep`/`wc` y se equivoca en lo que **infiere** del instalador o de los documentos. De 28 afirmaciones revisadas, **17 se sostienen, 6 caen, 1 son parciales, 4 no se pueden verificar o no están probadas**. Dos de las que caen son premisas de su Top 5 (#4 y #5), y su hallazgo B es peor de lo que escribió.

---

## 1. Afirmaciones: ¿llevan prueba y se sostienen?

Regla: si B no dio archivo:línea, comando o enlace, lo marco «sin prueba» en la columna 3 y lo comprobé yo.

| # | Afirmación de B | ¿Prueba en B? | Mi comprobación | Resultado | Gravedad |
|---|---|---|---|---|---|
| 1 | §0-A · Solo `com.remi.nucleo` y `com.remi.noche` en LaunchAgents; `instalar.sh` define 10; no hay crontab | sí (ls, launchctl) | `ls ~/Library/LaunchAgents \| grep remi`; `crontab -l` → «no crontab for juancamilo»; etiquetas en `instalar.sh:13,14,154,205,249,294,337,380,422,467` | **SOSTIENE** | `[ALTO]` |
| 2 | §0-A · «Hipótesis: no se corrió `instalar.sh` completo tras la última limpieza» | no (B la marca hipótesis) | No se prueba ni se descarta. Dato que B no tenía: el repositorio restic de iCloud tiene `data/` modificado el 2-oct 22:46 y no existe `~/Library/Logs/Remi/copia.log`: la copia lleva ≥ 23 días parada, no «desde la última limpieza» | **NO PROBADA** | `[MEDIO]` |
| 3 | §0-B · La trastienda no tiene filtro de privacidad (grep en `pensar.py`) | sí (grep + `pensar.py:1606`) | `grep -n es_privado nucleo/*.py` → solo `telegram.py:68,169,381`; ninguna llamada desde `pensar`, `cierre`, `estado_libro` ni `episodios` | **SOSTIENE (y se queda corto: ver F-3)** | `[ALTO]` |
| 4 | §0-C · `remi.db.memoria` = 0 filas; `conocimiento/` solo `experiencia/`; `conocimiento/proyectos` y `~/proyectos/remi-mente` no existen | sí | `sqlite3 …?mode=ro`; `ls -la conocimiento`; `ls ~/proyectos/remi-mente` → no existe | **SOSTIENE** | `[ALTO]` |
| 5 | §0-C · bóveda `memoria.db` = 2 entradas | sí | `select count(*) from entradas` con `mode=ro` → 2 | **SOSTIENE** | `[BAJO]` |
| 6 | §0-D · «El FTS de experiencia no se reindexa solo (arreglado a medias en `noche.py`)» | cita `ahora.md` | `nucleo/noche.py:195-203` ya llama `experiencia.reindexar` (FTS de cero + vectores); commit `5bb18dc` «Reindexar el FTS de experiencia en la noche». `ahora.md` quedó viejo; no está «a medias» | **CAE** | `[BAJO]` |
| 7 | §1 · Conteos de líneas de Remi (notion 245 + notion_sync 436 + notion_avisos 371 = 1052; pensar 1968; telegram 396; tts 139; memoria_mcp 231; experiencia 628; vectores 209; rumbo 612; calibracion 179) | sí | `wc -l nucleo/*.py` (mi tabla §1.1 coincide en los nueve) | **SOSTIENE** | `[BAJO]` |
| 8 | §1.2 · `memoria_mcp.py:20` usa `MCPServer`; 6 herramientas en `:50–187` | sí | `:20 from mcp.server.mcpserver import MCPServer`; `@servidor.tool` en `indice :50, leer :72, guardar :103, anotar_leccion :144, buscar_lecciones :169, buscar_memoria :187` | **SOSTIENE** | `[BAJO]` |
| 9 | §1.5 · `notion.py:24` versión `2022-06-28`, `:26` `2025-09-03` | sí | `sed -n 24,26p nucleo/notion.py` | **SOSTIENE** | `[BAJO]` |
| 10 | §1.6 · `telegram.py`: `ClienteBotAPI :117`, `es_privado :62`, silencio `:284`, tope 280 | sí | `telegram.py:117`, `:62`, `:284`, `:49 MAX_CARACTERES = 280` | **SOSTIENE** | `[BAJO]` |
| 11 | §1.8 · `pensar.py`: `BINARIO :37`, `_llamar_openai_compatible :1392`, `_llamar_proveedor :1570` | sí | `pensar.py:37`, `:1392`, `:1570` | **SOSTIENE** | `[BAJO]` |
| 12 | §3/§4 · Remi mezcla parser a mano (`libros.py:105`) con `yaml.safe_load` (`:155`) | sí | `libros.py:105 def _frontmatter`, `:155 yaml.safe_load` | **SOSTIENE** | `[MEDIO]` |
| 13 | §1.3 · `boveda.py` 860 líneas; `cargar_yaml :41`, `transcribir :453`, `cascada :494` | sí | `wc -l`; `sed -n 41p/453p/494p` (el `:525` de la caché y el final `:120` del parser no los comprobé) | **SOSTIENE** | `[BAJO]` |
| 14 | §1.3 / §3 / §5 · «requirements.txt:5: kokoro» (la bóveda declara Kokoro) → «quitar kokoro de los requisitos» | sí (archivo:línea) | `wc -l /Volumes/ORGANIC/boveda/requirements.txt` → **4**; `grep -c kokoro` → **0**. El archivo es `yt-dlp`, `youtube-transcript-api`, `faster-whisper`, `langgraph==0.6.11` | **CAE** | `[MEDIO]` |
| 15 | §1.9 · `construir()` (`inteligencia/rumbo.py:563–581`) es lineal: 6 nodos, sin `add_conditional_edges`/checkpoint/interrupt | sí | `sed -n 563,581p` (6 `add_node`, `GRAFO = construir()` en `:581`); `grep -n "add_conditional_edges\|checkpoint\|interrupt"` → vacío | **SOSTIENE** | `[BAJO]` |
| 16 | §1.3 · «whisper.cpp … **ya corre residente en Remi** (`whisper-server`, `instalar.sh:154–200`)» | sí, pero lee el instalador, no el sistema | `lsof -nP -iTCP -sTCP:LISTEN` → solo :4400 y :4402; `launchctl list \| grep remi` → sin `com.remi.whisper`. El servicio está *definido*, no corre | **CAE** | `[ALTO]` |
| 17 | §1.11 · Ventanita ≈ 8.600 líneas TS + Rust | sí | `find apps/ventanita/src -name '*.ts*' \| xargs cat \| wc -l` = 6 805, más Rust 1 830 = 8 635 | **SOSTIENE** | `[BAJO]` |
| 18 | §4 · La memoria de Claude Code tiene 46 archivos | sí | `ls ~/.claude/projects/-Users-juancamilo/memory \| wc -l` → 46 | **SOSTIENE** | `[BAJO]` |
| 19 | §3 · Migración: 10 notas `03_oro/decisiones`, 4 `negocio`, 6 `inteligencia`, «5 JSON de `inteligencia/memoria/`» | sí | `ls` de cada carpeta → 10, 4, 6; `inteligencia/memoria/` tiene 6 entradas (no comprobé cuántas son `.json`) | **SOSTIENE (el «5» sin comprobar)** | `[BAJO]` |
| 20 | §5 #3 · «ya hay un consumidor: `coding.py`» de `consultor.py`/`inyectar_contexto` | no (sin archivo:línea) | `grep -n "consultor\|inyectar_contexto\|capturador" nucleo/coding.py` → vacío. `coding.py:374` usa `bloque_de_experiencia(lecciones)` de `experiencia.py` | **CAE** | `[MEDIO]` |
| 21 | §1.1–1.11 · Fechas de release, versiones, licencias (AGPL/GPL/MIT), «mem0 por defecto usa gpt-5-mini», incidente de LiteLLM de marzo de 2026 | enlaces, sin comprobar aquí | No consulté la web; `pyproject.toml` confirma solo `kokoro>=0.9.4`, `mcp>=2.2.0` | **NO VERIFICABLE** | `[MEDIO]` |
| 22 | §5 · Esfuerzos (1–4 h) y ahorros (líneas) | no (B las declara «estimaciones mías») | Sin medir | **NO VERIFICABLE** | `[BAJO]` |
| 23 | §1.5 · «Las reglas (solo `compartible`, 5 avisos/día, **90 min**) son nuestras y se quedan» | parcial | Biblia v4.2 dice 45 min (`BIBLIA.md:577`), igual que `iniciativa.py:33` y `avisos.json:5`; 90 solo está en `notion_avisos.py:53` | **CAE (consagra el valor equivocado)** | `[MEDIO]` |
| 24 | §1.7 / §5 #4 · `noche`, `notion`, `vigia`, `refresco` pueden ser hilos del núcleo; quedan 4 agentes | no (inferencia) | `scripts/vigia.sh:2-4`: el vigía le «pega a /salud» cada minuto desde fuera; un hilo dentro del núcleo no avisa cuando el núcleo cae (`BIBLIA.md:377`). Además `desinstalar.sh:19` y `doctor.sh:100-133` cuentan estos agentes | **CAE (vigía); PARCIAL (noche, notion, refresco)** | `[ALTO]` |
| 25 | §5 #2 · Unificar frontmatter con PyYAML: «riesgo bajo-medio» | sí, genérico | Prueba corrida: el parser a mano acepta `titulo: La noche: no reindexaba`; `yaml.safe_load` lanza `ScannerError: mapping values are not allowed here`. También devuelve `date`/`float`/`bool` donde el parser a mano devuelve texto (`fecha`, `version`, `usa: no`) | **PARCIAL** | `[MEDIO]` |
| 26 | §3 · «El índice SQLite de la bóveda no debería vivir en ORGANIC («nada vivo en caliente»)» | cita una nota de memoria del usuario | No hay archivo en el repo que lo diga; no lo puedo comprobar | **NO VERIFICABLE** | `[BAJO]` |
| 27 | §1.10 · «Falta que [la copia] *corra*» (restic es la herramienta correcta) | sí | Coincide con mi §3.4; `config/copia.json` destino iCloud; sin `copia.log` | **SOSTIENE** | `[ALTO]` |
| 28 | §1.6 · Pendiente: «un error de `getUpdates` escribe la URL con el token en `nucleo.log`» | cita Bitácora | `grep -c "api.telegram.org/bot[0-9]" ~/Library/Logs/Remi/nucleo.log` → 1 (no imprimí el valor) | **SOSTIENE** | `[ALTO]` |

**Las que caen (números 6, 14, 16, 20, 23, 24):** FTS «a medias» (6), `kokoro` en la bóveda (14), `whisper-server` «ya corre» (16), «`coding.py` consume el consultor» (20), el 90 min (23) y el vigía como hilo (24).

### 1.1 El hallazgo B de B es más grave que como lo escribió `[ALTO]`

B lo deja como «hipótesis: si una conversación de salud/plata se resume en la trastienda, sale del Mac hacia Groq/OpenRouter». **Es cierto por construcción, y sale incluso sin llaves:**
- `pensar_con_trastienda` (`nucleo/pensar.py:1606`) llama `_llamar_proveedor` (`:1570-1573`), que hace `clave = _ajuste(clave_env, "")` y sigue; `_llamar_openai_compatible` (`:1392-1402`) solo omite la cabecera `Authorization` si la clave está vacía y **igual hace `httpx.post(url, json=…)`** con el texto en el cuerpo. A diferencia de la charla, que sí corta con «sin GROQ_API_KEY: sigo sin IA» (`:1530-1534`), la trastienda no mira si hay clave.
- `nucleo/.env` solo tiene `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` (`sed -E 's/=.*//' nucleo/.env`), y la cadena por defecto es `groq → openrouter → ollama` (`nucleo/config/motores.json`). Con Ollama caído o antes de él, cada resumen de fondo (`pensar.py:902 resumir`, tras cada turno que sale de los 10 literales) manda turnos de la conversación a `api.groq.com` y `openrouter.ai`, sin autenticar (recibirán 401, pero el contenido ya salió).
- Es **código leído, no ejecutado**: probarlo exigía llamar a la red.
- Además, la Biblia se contradice: la trastienda en Groq/OpenRouter está *diseñada* (`BIBLIA.md:357`, `ROBUSTEZ.md:23`) y la parte VII dice «a nadie más» (`BIBLIA.md:581`). B lo trata como bug de código; es primero una decisión de Juan Camilo.

---

## 2. Tres hallazgos que B no vio

| # | Gravedad | Hallazgo | Evidencia |
|---|---|---|---|
| F-1 | `[ALTO]` | **El historial de git empieza hoy y no hay remoto.** Los hashes de la bitácora y de los documentos no existen; B propone `git revert` como reversión de varios cambios y apoya su Top 5 en la bitácora. | `git log --format='%h %ci' \| tail -2` → `b08962d 2026-10-26 06:17:11`; `git cat-file -t 742bd8f` (y `123fdc1`, `5f6e1e2`, `f7f1228`, `9bfefc9`, `b464770`) → «Not a valid object name»; `git remote -v` vacío. Hasta que haya una copia fuera del Mac, «revertible» significa «revertible en este disco». |
| F-2 | `[ALTO]` | **Remi no recibe las sesiones de Claude Code.** El `doctor.sh` exige los hooks `SessionStart`/`SessionEnd` (`scripts/doctor.sh:100-133`); `~/.claude/settings.json` solo tiene un `PreToolUse` de otro proyecto y `trabajo_claude` tiene 0 filas. B recomienda construir sobre `coding.py` y «Hoy» sin ver que la mitad de sus entradas no existe. | `python3 -c "import json;print(json.load(open('$HOME/.claude/settings.json'))['hooks'].keys())"` → `PreToolUse`; `sqlite3 …?mode=ro "select count(*) from trabajo_claude"` → 0. El hook de git sí funciona (`trabajo_eventos` tiene eventos `commit`). |
| F-3 | `[MEDIO]` | **596 líneas del Rumbo no las llama nadie fuera de las pruebas** (`claves.py`, `produccion.py`, `juego.py`, `estimacion.py`, `simulacion.py`, `orden_rumbo.py`). Una auditoría de «ruedas» tiene que empezar por lo que sobra: B habla de LangGraph (6 nodos) y no de estos 6 módulos. | `grep -rn "import estimacion\|from estimacion" nucleo --include=*.py \| grep -v pruebas` → vacío (ídem los otros cinco). Detalle en `A-inventario.md` §3.1. |

Extras menores que B tampoco vio (ya en `A-inventario.md`): el panel escucha en `*:4402` sin Access (`lsof -nP -iTCP:4402 -sTCP:LISTEN`, `[MEDIO]`); 6 pruebas fallan porque dependen de la bóveda real vacía (`[MEDIO]`); `avisos.py:22` lee un `config/avisos.json` que no existe en la raíz y cae a los valores por defecto (`[BAJO]`).

---

## 3. Contradicciones entre B y mi informe

| # | Tema | B dice | A dice | Quién tiene razón y por qué | Gravedad |
|---|---|---|---|---|---|
| C-1 | ¿Corre el servidor Whisper? | «ya corre residente en Remi» (§1.3, Top 5 #5) | `com.remi.whisper` no cargado y :4401 sin escucha (`A-inventario.md` §2.3) | **A.** `lsof` y `launchctl list` lo prueban. B leyó `instalar.sh`. | `[ALTO]` |
| C-2 | Vigía dentro del núcleo | `vigia` como hilo; 10 → 4 agentes (§1.7, #4) | El vigía se queda fuera (`A-inventario.md` §3.4: «faltan `copia` y `vigia`») | **A.** `scripts/vigia.sh:2-4` y `BIBLIA.md:377`: tiene que ser un proceso independiente. Además B conserva `ventanita` como agente y esa app no tiene plist (`ls ~/Library/LaunchAgents`). | `[ALTO]` |
| C-3 | Minutos entre avisos | 90 «se quedan» | 45 es el valor de la Biblia, de `iniciativa.py:33` y `avisos.json:5` | **A.** `BIBLIA.md:577`. El 90 de `notion_avisos.py:53` es la excepción a corregir. | `[MEDIO]` |
| C-4 | Memoria vacía: ¿qué hacer? | «Unificar ahora cuesta casi nada»; migrar por copia (#3) | No migrar hasta saber por qué está vacía; la copia del 2-oct podría tenerla (`A-inventario.md` §2.0) | **A**, por prudencia: B migraría 2 entradas hacia un formato nuevo sobre un almacén que quizá deba *restaurarse*, no rediseñarse. Ninguno de los dos tiene prueba de la causa. | `[MEDIO]` |
| C-5 | Causa de la copia parada | «no se corrió `instalar.sh` completo» (hipótesis) | Sin `copia.log`, restic tocado el 2–3 oct | **Empate parcial:** mi dato descarta «tras la última limpieza», pero tampoco prueba la causa. | `[BAJO]` |
| C-6 | FTS de experiencia | «no se reindexa solo, arreglado a medias» | `noche.py:195-203` ya reindexa | **A.** El código y el commit `5bb18dc`. `ahora.md` quedó viejo. | `[BAJO]` |
| C-7 | Líneas de la ventanita | «~8.600 (TS+Rust)» | «10 277 (TS/TSX/CSS 8 447 + Rust 1 830)» | **Ambos**, medidas distintas: sin CSS son 6 805 + 1 830 = 8 635. B tiene razón en lo que midió; mi cifra incluye CSS (lo dice mi tabla). | `[BAJO]` |
| C-8 | Privacidad de la trastienda | Hipótesis condicionada a que haya llaves | Con `.env` de solo Telegram, la trastienda igual manda el texto (§1.1) | **A más fuerte**, sin ejecutarlo. | `[ALTO]` |
| C-9 | Estado de las pruebas | «No verifiqué los 6 fallos» | 6 fallos, una sola raíz: pruebas no herméticas + bóveda vacía | **A** (lo corrí). No contradice a B; lo completa. | `[BAJO]` |

---

## 4. Veredictos «Reemplazar» y «Quitar» de B: qué se rompe

| Veredicto de B | Qué se rompe si se hace hoy | Pruebas / rutas / pantallas afectadas | Gravedad |
|---|---|---|---|
| **Reemplazar LangGraph** por funciones en fila (`/Volumes/ORGANIC/boveda/inteligencia/rumbo.py`) | El archivo es un script (`rumbo.py:11-12`: `python3 inteligencia/rumbo.py "pregunta"` y `--autocomprobar`); `GRAFO = construir()` en `:581`. Nada de Remi lo importa (`grep` en `nucleo/` y `apps/` → vacío). Lo usa Grok Bot desde fuera de este repo, y escribe `03_oro/decisiones/rumbo-*.md` | `--autocomprobar` es la única prueba; no hay `pytest` en la bóveda (`ls /Volumes/ORGANIC/boveda`). Ninguna ruta ni pantalla de Remi | `[BAJO]` — se sostiene |
| **Usar PyYAML** en vez de `libros._frontmatter` (`libros.py:105`) y `cargar_yaml` (`boveda.py:41`) | Un título con dos puntos deja de leerse (prueba arriba, `ScannerError`); `fecha`, `version` y valores como `no` cambian de tipo y rompen las comparaciones de texto que hacen `caminos`, `aldia`, `precarga`… Solo hace falta que *una* nota real tenga un título con «:» | `libros` aparece en 17 archivos de prueba / 111 pruebas; pantallas Proyectos, ficha, Hoy («Al día») y el índice de la mente | `[MEDIO]` |
| **Reemplazar `class Notion`** (`notion.py:66-166`) por `notion-sdk-py` | Cambia el transporte que fingen las pruebas; la versión de API fijada (`notion.py:24 = 2022-06-28`, `:26 = 2025-09-03`) pasaría a la que traiga el SDK, y las data sources dependen de esa fecha. `notion_sync.py:210,232,244,335,388` y `notion_avisos.py:139,157` tipan `notion.Notion` | `test_notion.py` (21), `test_notion_sync.py` (11), `test_notion_avisos.py` (6) usan transporte falso; rutas `/notion/sincronizar`, `/notion/estado`, `/notion/avisos/pendiente`, `/notion/avisos/<built-in function id>/respuesta`; en la ventanita, `AvisoNotion.tsx`/`useAvisoNotion.ts`. Hoy todo está dormido (sin `NOTION_TOKEN`), así que el riesgo real es de pruebas, no de producción | `[MEDIO]` |
| **Un solo cliente OpenAI-compatible** en `pensar.py` | La contabilidad de gasto lee los tokens de la respuesta que hoy arma `_leer_respuesta_venice` (`:1425`); el streaming propio (`_deltas_openai_compatible :1338`) y el tope (`gasto.excede_tope`) están atados al formato actual | `test_pensar.py` y vecinas: `_llamar_proveedor` aparece en 14 pruebas, `_llamar_openai_compatible` en 7, `_llamar_venice` en 4; `test_gasto*` (103); chips Groq/OpenRouter/Venice de la ventanita y `GET /pensar/motores` | `[MEDIO]` |
| **Quitar `faster-whisper`** y usar el `whisper-server` | **La ingesta se queda sin transcripción**: el servidor no corre (C-1) y, según el propio B, arranca con `-l es`, o sea que todo video en otro idioma sale mal | Nada en Remi; rompe la bóveda (`boveda.py:453 transcribir`, `:494 cascada`) y lo que Grok Bot ingiere cada día | `[ALTO]` mientras `com.remi.whisper` no esté cargado |
| **Recortar 10 → 4 agentes** (`noche`, `notion`, `vigia`, `refresco` como hilos) | Sin vigía externo nadie avisa cuando el núcleo cae; `noche` a las 4:00 como hilo no se ejecuta si el núcleo está caído o el Mac dormía (launchd la corre al despertar, `instalar.sh:203-204`) | `scripts/desinstalar.sh:19` (lista de etiquetas), `scripts/doctor.sh:100-133` (chequeo 6) y `:166-178` (chequeo 9, frescura de copia y episodio), `scripts/vigia.sh`, `scripts/noche.sh`, `rotar-logs.sh`; `test_noche` (76 pruebas) sigue válido solo si `noche.correr` se conserva | `[ALTO]` por el vigía; `[MEDIO]` por `noche` |
| **Una sola memoria**: meter `memoria/capturador.py` + `consultor.py` en `experiencia.py` y estrenar el frontmatter de §4 | Cambia el formato de escritura de lecciones (`experiencia.py:203-218`) y por tanto el hash que decide si se recalculan vectores; añade `id`, `evidencia` obligatoria y `compartible`, y las lecciones ya escritas no los tienen. Grok Bot sigue escribiendo con `capturador.py` desde ORGANIC | `memoria_mcp.py` (6 herramientas: `anotar_leccion :144`, `buscar_lecciones :169`, `buscar_memoria :187`); rutas `/experiencia` y `/coding/lecciones`; pantalla Coding; `test_experiencia*` (59 pruebas en 8 archivos), `test_coding` (15), `test_memoria` | `[MEDIO]` (y `[ALTO]` si se hace antes de aclarar por qué la memoria está vacía, C-4) |
| **Quitar `kokoro` de los requisitos de la bóveda** | Nada: ese requisito no existe (afirmación 14) | — | `[BAJO]` |

---

## 5. Qué bloquea el plan

Un `[ALTO]` sin resolver bloquea. Los que quedan abiertos:

1. **B: hallazgo B (trastienda)** — resolver antes de cualquier otro cambio de `pensar.py`: o la trastienda no sale sin llave, o Juan Camilo decide que sí puede. *(§1.1)*
2. **B, Top 5 #4** — no se puede quitar el vigía como agente. *(C-2)*
3. **B, Top 5 #5** — no se puede quitar `faster-whisper` mientras no corra `com.remi.whisper`. *(C-1)*
4. **A+B: F-1 y F-2** — sin copia fuera del Mac y sin hooks de Claude Code, «revertible» y «Hoy se actualiza solo» no se cumplen.
5. **A+B: copia parada** (hallazgo A de B, `[ALTO]`).

## 6. Qué no verifiqué

- Cualquier cosa externa de B: versiones, fechas de release, licencias, el incidente de LiteLLM, las políticas de mem0/Graphiti/ntfy (no usé la web).
- Que la trastienda *realmente* haga el POST sin llave (lo leí; ejecutarlo habría salido a la red).
- `boveda.py:525` y el rango `:41–120`; `capturador.py:49–79`; cuántos de los 6 elementos de `inteligencia/memoria/` son `.json`.
- Qué hace Grok Bot con la bóveda (proceso externo); por eso el impacto en `rumbo.py` de la bóveda y en `capturador.py` es por lectura, no por ejecución.
- Que `notion-sdk-py` 3.x use otra versión de API por defecto (lo supongo de cómo funcionan los SDK; sin prueba).
- Playwright y `doctor.sh` (los dos tocan puertos que no debía tocar).

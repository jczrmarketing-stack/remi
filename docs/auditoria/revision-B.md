# Revisión B de la auditoría A («Inventario honesto de Remi»)

- **Revisor:** terminal B (autora de `docs/auditoria/B-rueda.md`, commit `66b19bc`). **Revisada:** `docs/auditoria/A-inventario.md` (commit `32d1810`, 907 líneas). Leí también `docs/auditoria/revision-A.md` (la revisión de A sobre mi informe).
- **Alcance:** solo lectura. Base abierta con `mode=ro`; pruebas con `REMI_DB_PATH` temporal, `REMI_TELEGRAM=0`, `REMI_NUCLEO_URL=http://127.0.0.1:1`. No corrí `doctor.sh` ni Playwright, ni llamé a la web, Notion, Telegram o :4400. `git status` quedó limpio tras cada prueba.
- **Gravedad:** `[ALTO]` bloquea el plan · `[MEDIO]` · `[BAJO]`.
- **Un aviso de entrada:** mi propio commit `66b19bc` disparó el hook global de git y escribió una fila `commit` en `remi.db` real (la última de `trabajo_eventos`, 16:19 UTC). A lo anotó bien; no lo evité porque entonces no sabía que el hook llegaba a la base real (ver N-2).

## Veredicto en tres líneas

A es mucho más sólido que mi informe en lo que **midió** (base, puertos, launchd, pruebas, conteos) y se equivoca en lo que **infirió** de un solo dato. De 26 afirmaciones revisadas: **19 se sostienen, 6 caen, 1 no está probada**. Las 6 que caen son de detalle, pero dos son de las que llevan a *borrar* cosas (`REVISION.md` y `sembrar_memoria.py`). De las 6 afirmaciones mías que A tumba, acepto las 6, pero con matices en dos: el FTS (queda un hueco real, §3.1) y los agentes (`notion` y `refresco` sí pueden ser hilos, §3.6).

---

## 1. Afirmaciones de A: ¿llevan prueba y se sostienen?

«Sin prueba» = A no dio archivo:línea ni comando para ese punto concreto; lo comprobé yo.

| # | Afirmación de A | ¿Prueba en A? | Mi comprobación | Resultado | Gravedad |
|---|---|---|---|---|---|
| 1 | `remi.db` casi vacía: `tareas`, `sesiones`, `ideas`, `memoria`, `entregas`, `trabajo_claude` = 0; `turnos` 4; `trabajo_eventos` 15 | sí (`sqlite3 mode=ro`) | Repetí `select count(*)` en las 8: idéntico | **SOSTIENE** | `[ALTO]` |
| 2 | Historial de git empieza hoy; 6 hashes de la bitácora no existen; sin remoto | sí | `git cat-file -t` en `742bd8f 123fdc1 5f6e1e2 f7f1228 9bfefc9 b464770` → 6× «Not a valid object name»; `git remote -v` vacío; `docs/ahora.md` ya declara «git init» de hoy | **SOSTIENE** | `[ALTO]` |
| 3 | Solo 2 de los 10 agentes de `instalar.sh` están cargados | sí | `ls ~/Library/LaunchAgents \| grep remi` → `noche`, `nucleo`; `launchctl list` igual (pid 1521) | **SOSTIENE** | `[ALTO]` |
| 4 | Repo restic tocado el 2-oct; sin `copia.log` | sí | `stat`: `copias/data` y `snapshots` = 2-oct 22:46; carpeta 3-oct 19:41; 5 snapshots; `ls ~/Library/Logs/Remi` → solo `nucleo.log`, `ventanita.log` | **SOSTIENE** | `[ALTO]` |
| 5 | «No existe `noche.log`» como prueba de que lo «indestructible» no corre (resumen #3) | sí, pero la inferencia no | `stat` del plist: `com.remi.noche.plist` = **26-oct 07:40**; corre a las 4:00 (`StartCalendarInterval`), o sea que **aún no le ha tocado una sola vez**. Sin log es lo esperado. (A en §2.3 sí lo deja «NO VERIFICADO»; el resumen lo sobrepasa) | **CAE (para `noche`; no para `copia`)** | `[MEDIO]` |
| 6 | Token de Telegram en `nucleo.log` (1 línea) | sí | `grep -c "api.telegram.org/bot[0-9]" nucleo.log` → 1. `grep -rlE` sobre logs, bóveda `Remi`, plists, docs, scripts, `config`, `nucleo/*.py`, pruebas y apps: **solo ese archivo** | **SOSTIENE** | `[ALTO]` |
| 7 | Hooks de sesión de Claude Code ausentes; `trabajo_claude` = 0 | sí | `~/.claude/settings.json` → `hooks` = solo `['PreToolUse']`; `trabajo_claude` = 0 | **SOSTIENE** | `[ALTO]` |
| 8 | `nucleo/.env` solo tiene Telegram → no hay plan B si Max se agota | sí | `sed -E 's/=.*//' nucleo/.env` → `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`; permisos `600`; `git check-ignore` confirma `.env`, `remi.db`, `conocimiento` ignorados | **SOSTIENE** | `[ALTO]` |
| 9 | La trastienda manda el texto aunque no haya llave (revisión A §1.1) | sí (`pensar.py:1392-1402`, `:1570-1573`, `:1530-1534`) | Leí las tres: `_llamar_proveedor` calcula `clave` y, si es `None`/vacía, `_llamar_openai_compatible` solo omite `Authorization` y **igual hace `httpx.post`** con el texto en el cuerpo. `_charla` sí corta sin llave (`:1530-1534`). `_respaldo_de_charla` (`:1639`) tampoco mira la llave. Es lectura de código; no lo ejecuté | **SOSTIENE (y A tiene razón: es más grave que en mi informe)** | `[ALTO]` |
| 10 | 596 líneas de módulos que solo llaman las pruebas | sí | `grep -rn "import <m>"` sobre `nucleo/` y `scripts/`: `claves`, `produccion`, `juego`, `estimacion`, `simulacion`, `orden_rumbo` solo aparecen en su propio `test_<m>.py` (más docstrings/comentarios) | **SOSTIENE** | `[MEDIO]` |
| 11 | `claves.py` «ni siquiera pertenece al Rumbo: lo reemplazó otra ruta» | **sin prueba** | Nadie lo reemplazó: `episodios.py:160` y `cierre.py:357` escriben `claves=None`; `sembrar_conocimiento.py:76` solo *lee* `claves` del frontmatter. `claves.py` es el único generador y nadie lo llama (por eso quedó huérfano, no «reemplazado») | **CAE** | `[MEDIO]` |
| 12 | 6 pruebas fallan; causa: no son herméticas y la bóveda real está vacía | sí | Corrí solo esas 6 con entorno aislado: `6 failed, 1 passed`; mismas aserciones (`test_vectores.py:37` trae `['"La noche no reindexaba…"']` en vez de «Shopify») | **SOSTIENE** | `[MEDIO]` |
| 13 | Panel escucha en `*:4402`; núcleo en `127.0.0.1:4400` | sí | `lsof -nP -iTCP -sTCP:LISTEN` → `python3.1 :4400 127.0.0.1`, `node :4402 *`, `ollama 127.0.0.1:11434` | **SOSTIENE** | `[MEDIO]` |
| 14 | 113 `BaseModel` a mano; 54 rutas en `servidor.py`; `servidor` 2477, `pensar` 1968, `db` 1597, `App.tsx` 1873; 44 `except` en `pensar` | sí | `grep … \| wc -l` → 113; `grep -c '^@app\.'` → 54; `wc -l` coincide; `grep -c '^\s*except' pensar.py` → 44 | **SOSTIENE** | `[BAJO]` |
| 15 | Presupuesto de silencio ×3 con 45 y 90 min | sí | `iniciativa.py:33 MINUTOS_ENTRE_NUDGES = 45`; `notion_avisos.py:53` = 90; `BIBLIA.md:577` = 45 | **SOSTIENE** | `[MEDIO]` |
| 16 | `doctor.sh` tiene 11 chequeos (los docs dicen 10) | sí | Cabecera de `doctor.sh:3`: «11 chequeos» | **SOSTIENE** | `[BAJO]` |
| 17 | Tabla `avisos` no existe en `remi.db` | sí | `select name from sqlite_master where name like 'avisos%'` → vacío | **SOSTIENE** | `[BAJO]` |
| 18 | mypy limpio en 193 archivos; vitest 122 verdes | sí | `uv run --offline mypy .` → «no issues found in 193 source files»; `npm test` → 18 archivos, 122 pruebas | **SOSTIENE** | `[BAJO]` |
| 19 | §1.1: `limpiar_pruebas.py` «Lo llaman: `scripts/archivar_ruido_de_sesiones.py`» | sí (tabla) | El script **no la importa** (`archivar…:28-29` solo importa `db` y `trabajo`); la menciona en un docstring (`:12`). A misma lo llama «sin importador» en la tabla final: se contradice | **CAE** | `[BAJO]` |
| 20 | §1.6: `vendor/kokoro` = «pesos de voz» | sí | `du -sh vendor/kokoro` → 12K; contiene `PARA_CLAUDIO.md` y `tts_kokoro.py`. Los pesos están en `~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M` | **CAE** | `[BAJO]` |
| 21 | §3.5/tabla final: `docs/REVISION.md` es un «histórico y cerrado» que se puede mover a `docs/archivo/` | sí (`PLAN-FINAL.md:7-8`) | `precarga.py:287 RUTA_REVISION = docs/REVISION.md` y `:370-376` la inyectan como **la fuente de «lo que te falta como app»** al responder «¿qué te falta?». No es histórico: se lee en producción | **CAE** | `[MEDIO]` |
| 22 | `sembrar_memoria.py` es «script de una sola vez» → Quitar | sí | Su docstring: «Pone en el estante lo que Remi tiene que saber **desde el primer día**», idempotente. Con `memoria` = 0 (hallazgo #1 de A) es *justo* la herramienta que puebla la memoria. A se contradice | **CAE** | `[MEDIO]` |
| 23 | F-1 (revisión A): «el código no tiene copia fuera de este Mac / revertible solo en este disco» | parcial | Lo que sí: sin remoto (`git remote -v` vacío). Lo que **no** probó: `tmutil destinationinfo` muestra un destino de Time Machine «Copias» (1 TB, Local, montado en `/Volumes/Copias`). No pude leerlo (`Operation not permitted`; `tmutil latestbackup` pide Acceso total al disco) | **NO PROBADA** | `[MEDIO]` |
| 24 | `pensar.py:1` dice «opt-in por mensaje», contra la Biblia v4 | sí | `sed -n 1,3p pensar.py` | **SOSTIENE** | `[BAJO]` |
| 25 | La ventanita corre pero no tiene plist | sí | `ls ~/Library/LaunchAgents \| grep remi` | **SOSTIENE** | `[BAJO]` |
| 26 | `com.remi.whisper` no está cargado, :4401 no escucha | sí | `lsof` y `launchctl list` (ver §3, punto 16) | **SOSTIENE** | `[ALTO]` |

**Resumen del §1:** 26 revisadas → **19 se sostienen · 6 caen (5, 11, 19, 20, 21, 22) · 1 no probada (23)**.

---

## 2. Tres hallazgos que A no vio

| # | Gravedad | Hallazgo | Evidencia |
|---|---|---|---|
| N-1 | `[MEDIO]` | **La memoria de Remi no está disponible fuera del repo Remi.** `ARQUITECTURA-CEREBRO §12` promete «el MCP de memoria se registra global (scope user)… cualquier Claude lee y guarda en la misma memoria». Hoy no hay MCP a nivel de usuario, y el `.mcp.json` del repo usa una ruta relativa (`--directory nucleo`), o sea que solo carga si Claude Code se abre en la raíz de `~/proyectos/remi`. Es otra pata de F-2 de A (sin hooks y sin MCP global, un `claude` abierto en malik-gestion no ve ni guarda nada en Remi). Con `memoria` = 0 hoy no pierde nada, pero rompe la regla de CLAUDE.md «por cada problema resuelto: `anotar_leccion`» en cualquier otro repo | `python3 -c "…json.load(open('~/.claude.json'))['mcpServers']"` → `[]`; `cat .mcp.json` (cuatro líneas, ruta relativa); `scripts/hooks/instalar-mcp.py` existe pero no se ve ejecutado. **Hipótesis:** el `.mcp.json` ni siquiera está aprobado (no hay entrada de proyecto con «remi» en `~/.claude.json`); no lo probé abriendo una sesión |
| N-2 | `[MEDIO]` | **El hook de git es global y copia lo que pasa en repos de clientes a `remi.db`.** `git config --global core.hooksPath` = `~/.config/git/hooks`; su `post-commit` corre `avisar-commit.py` en **cualquier repo de la máquina** y manda mensaje de commit, rama y lista de archivos al núcleo (`avisar-commit.py`: `git log -1 --pretty=%B`, `diff-tree --name-only`). Resultado hoy: 3 de los 15 eventos son de `/Users/juancamilo/projects/malik-gestion` (producción con 29 cuentas, `AGENTS.md`), con `tema` vacío. Es local (127.0.0.1), pero esos textos son la «evidencia literal» que `estado_libro`/`cierre` pasan a `pensar_con_trastienda`, o sea al hallazgo 9. Y es el motivo de que mi commit de B escribiera en la base real | `git config --global core.hooksPath`; `sqlite3 …mode=ro "select tipo,ruta,tema,length(datos) from trabajo_eventos"` (3 filas de malik); `sed -n 1,60p scripts/hooks/avisar-commit.py`. Mitigación que ya existe: `REMI_NUCLEO_URL` o `REMI_SIN_HOOKS=1` |
| N-3 | `[MEDIO]` | **La voz de Remi depende de un archivo en la carpeta de otra app.** `config/ventanita.json → voz.modelo` = `~/Library/Application Support/com.pais.handy/models/ggml-large-v3-turbo.bin` (1,6 GB; el propio `$comment` dice «un modelo que ya tenía descargado Handy»). Handy es una app de terceros que administra esa carpeta (y, según tus notas del 26-oct, ya dicta con Parakeet, no con Whisper). Si Handy limpia o migra modelos, Remi se queda sin Whisper: ni `whisper-cli` ni un futuro `whisper-server` arrancan. Esto además condiciona el «cargar `com.remi.whisper`» que A y yo recomendamos | `python3 -c "…['voz']['modelo']"` y `ls -la` (existe hoy, fecha dic-2025; carpeta con `ggml-small.bin`, `whisper-medium-q4_1.bin`, `parakeet-tdt-0.6b-v3-int8`). **Hipótesis (no probada):** Handy podría borrarlo; hoy está |

Lo que **busqué y no encontré** (descarto, para que nadie lo repita): `claude` sí se encuentra bajo launchd (el plist de `com.remi.nucleo` pone `~/.local/bin` primero; `which -a claude` → 3 copias); `.env` está en 600; el token solo está en `nucleo.log`; el núcleo escucha solo en 127.0.0.1.

---

## 3. Contradicciones con mi informe — las 6 que A dice que se caen

Cada punto: lo que dije, lo que dice A, mi decisión con evidencia, y qué cambia.

### 3.1 «El FTS de experiencia no se reindexa solo (arreglado a medias en `noche.py`)» (A: afirmación 6) — **ACEPTO A MEDIAS** `[BAJO]`
- **A tiene razón en lo escrito.** `nucleo/noche.py:195-203` (`recalcular_vectores`) ya llama a `experiencia.reindexar(conexion)`, que reconstruye el FTS de cero y los vectores cambiados; el commit `5bb18dc` existe (`git cat-file -t` → `commit`). Mi fuente fue `docs/ahora.md` (desactualizado) y **no leí `noche.py`**: error de método, y «a medias» es incorrecto.
- **Pero queda un hueco real que A no menciona:** `experiencia.escribir` (`:222-259`) y `crear_leccion` (`:578-596`) no indexan al escribir; solo `reindexar` indexa. Hoy hay **1 lección en disco y 0 filas en `experiencia_fts_docsize`** (`sqlite3 mode=ro`), y la noche aún no corrió (plist de hoy). Hasta las 4:00 una lección nueva no sale en FTS. No es el bug que cité, es el hueco entre escribir y la noche.
- **Cambia:** quito «arreglado a medias»; mi recomendación #3 (unificar memoria) debe incluir «indexar al escribir», no solo «reindexar de noche».

### 3.2 «`requirements.txt:5` de la bóveda declara `kokoro`» y «quitar `kokoro` de los requisitos» (A: 14) — **ACEPTO** `[MEDIO]`
- `wc -l /Volumes/ORGANIC/boveda/requirements.txt` → **4**; `grep -c -i kokoro` → **0**. El archivo es `yt-dlp`, `youtube-transcript-api`, `faster-whisper`, `langgraph==0.6.11`.
- **De dónde salió mi error (reconstruido):** corrí `cat requirements.txt; ls ~/proyectos/remi/vendor; cat LICENCIAS…` en un solo comando; `ls vendor` imprimió «kokoro» justo debajo de las 4 líneas y lo leí como la quinta. Lo cité con archivo:línea sin releer el archivo.
- **Cambia:** borro de mi §3 la fila «Kokoro» de duplicados y de mi §5 «quitar kokoro de los requisitos». La bóveda no depende de Kokoro; no hay nada que quitar.

### 3.3 «`whisper-server` ya corre residente en Remi (`instalar.sh:154–200`)» (A: 16 / C-1) — **ACEPTO** `[ALTO]`
- `lsof -nP -iTCP -sTCP:LISTEN` → solo `:4400` (127.0.0.1), `:4402` (`*`) y `:11434` (ollama). **Nada en :4401.** `launchctl list | grep remi` → sin `com.remi.whisper`. El servicio está *definido* en `instalar.sh:154`, no cargado. Leí el instalador, no el sistema.
- **Consecuencia sobre mi Top 5 #5 («un solo Whisper: la ingesta llama al `whisper-server` ya residente»):** la premisa es falsa, y el efecto es peor que «no ahorra»: sin servidor, quitar `faster-whisper` deja a la ingesta sin transcripción (ver §4, fila 5). Además el servidor arrancaría con `-l es` (argumentos del plist en el bloque whisper de `instalar.sh`) y depende de un modelo ajeno (N-3).
- **Cambia:** #5 queda **invalidado hasta** cargar `com.remi.whisper` y probar idioma `auto`; lo muevo de «top 5» a «idea condicionada».

### 3.4 «`coding.py` ya es consumidor de `consultor.py`/`inyectar_contexto`» (A: 20) — **ACEPTO** `[MEDIO]`
- `grep -n "consultor\|inyectar_contexto\|capturador" nucleo/coding.py` → vacío; `grep -rn inyectar_contexto nucleo` → ninguno. `coding.py:374` usa `bloque_de_experiencia(lecciones)` de `experiencia.py`. Confundí «coding ya inyecta lecciones» con «inyecta las de la bóveda».
- **Cambia:** la bóveda/`consultor.py` hoy **no tiene ningún consumidor en Remi**; fusionarla (mi #3) implica *portar y cablear*, no «ya hay consumidor». Esfuerzo de #3 sube de ~4 h a una estimación mayor que ya no sé acotar (sin medir).

### 3.5 «Las reglas (solo `compartible`, 5 avisos/día, **90 min**) se quedan» (A: 23 / C-3) — **ACEPTO** `[MEDIO]`
- `BIBLIA.md:577` (v4.2): «45 min entre dos (decidido el 4-oct: la Biblia se alinea con el código)»; `iniciativa.py:33` = 45. Mi 90 sale de `ARQUITECTURA-CEREBRO §3` (`:16`, `:105`) y de `notion_avisos.py:53`. Por la jerarquía de `CLAUDE.md` («La Biblia… fuente única de leyes») manda 45.
- **Cambia:** al «conservar las reglas» de Notion hay que decir «las de la Biblia (45), no las de `notion_avisos.py`». Es justo el defecto que A señala en §5.3; yo lo consagré.

### 3.6 «`vigia` (y `noche`, `notion`, `refresco`) pueden ser hilos del núcleo; 10 → 4 agentes» (A: 24 / C-2) — **ACEPTO PARA `vigia` Y `noche`; REBATO A MEDIAS PARA `notion` Y `refresco`** `[ALTO]`
- **Vigía: A tiene razón.** `scripts/vigia.sh:2-4`: «cada minuto le pega a /salud… si falla 5 min seguidos, avisa»; `BIBLIA.md:377`: «Vigía: si Remi cae 5 min, aviso». Un hilo dentro del núcleo muere con el núcleo y no puede avisar que cayó. Mi propuesta anulaba su razón de existir.
- **Noche: A tiene razón.** `instalar.sh:203-204` (comentario del bloque de la copia, mismo mecanismo): «si el Mac estaba dormido a las 3, launchd la corre al despertar». Un hilo del núcleo no recupera una corrida perdida por sueño o por núcleo caído.
- **Ventanita: A tiene razón.** Yo la daba como uno de los 4 que quedan; no existe plist (`ls ~/Library/LaunchAgents`), la app corre sola (`application.com.remi.ventanita`).
- **Dónde rebato:** `notion` y `refresco`. El agente `notion` solo ejecuta `uv run python notion_sync.py` cada 900 s (`instalar.sh:305-322`) y se «salta solo» sin `NOTION_TOKEN`; `notion_avisos` **ya** es un hilo del núcleo (`notion_avisos.py:320 arrancar_hilo`). Esos dos sí pueden ser tareas internas sin romper ninguna promesa de la Biblia (no son «indestructible»). A mismo los lista como «sobran» (§3.4).
- **Cambia:** de 10 → 4 pasa a **10 → 6 con sentido** (`nucleo`, `noche`, `copia`, `vigia`, `whisper` si se carga, `ventanita` si se quiere que abra al iniciar sesión); `notion` y `refresco` se descargan o pasan a hilos. Mi #4 («recortar a 4») queda reescrito como «cargar `copia` y `vigia` ya» (que es lo que A pide) y **sin** mover el vigía.

### 3.7 Otras contradicciones que A anota (no son de las 6)
| Tema | Mi posición | A | Decisión |
|---|---|---|---|
| C-4: ¿unificar la memoria ya? | «cuesta casi nada, migra por copia» | no migrar hasta saber por qué está vacía; la copia del 2-oct podría tenerla | **Acepto A** (`[MEDIO]`). Mi premisa («memoria casi vacía → barato») es de un día de datos; no abrí la copia restic (no tengo la clave del Llavero y es la de producción). Hasta aclararlo, solo el formato; no la migración |
| C-5: causa de la copia parada | hipótesis «no se corrió `instalar.sh` completo» | `data/` del 2-oct, sin `copia.log` | **Empate:** su dato descarta «tras la última limpieza»; ninguno prueba la causa. `[BAJO]` |
| C-7: líneas de la ventanita | ~8.600 (TS+Rust) | 10.277 (con CSS) | **Ambas** (8.635 sin CSS; mi número era de lo que medí). `[BAJO]` |
| C-8: trastienda | «hipótesis, si hay llaves» | sale incluso sin llaves | **Acepto A** (ver §1, #9): `_llamar_openai_compatible` hace el POST con o sin `Authorization`. Mi «hipótesis» era demasiado tímida. `[ALTO]` |

---

## 4. Veredictos «Quitar» de A (y «Reemplazar/Simplificar» que borran algo): qué se rompe

A no usa la palabra «Reemplazar»; sus «Quitar» son estos. «Pruebas» = archivos de `nucleo/pruebas/` que importan o monkeypatchean el módulo.

| Veredicto de A | Qué se rompe si se hace hoy | Pruebas / rutas / pantallas | Gravedad |
|---|---|---|---|
| **Quitar `calendario.py`** («por ahora») | `servidor.py:55 import calendario` y `:160 app.include_router(calendario.router)`: borrar solo el archivo **tumba el arranque del núcleo**. Se pierden `GET /calendario/estado` y `POST /calendario/importar` (sin cliente, A lo dijo) | `pruebas/test_calendario.py`; ninguna pantalla | `[MEDIO]` (sería `[ALTO]` si se borra sin editar `servidor.py`) |
| **Quitar `claves.py`** | Nada en producción (nadie lo llama). Pero es el **único** generador de `claves` (3–6 palabras por libro, `ARQUITECTURA §2` nivel 1); `episodios.py:160` y `cierre.py:357` ponen `claves=None`. Borrarlo deja la función sin camino de vuelta, y la razón que A da («lo reemplazó otra ruta») no tiene prueba | `pruebas/test_claves.py` | `[MEDIO]` |
| **Quitar o congelar `produccion`, `juego`, `estimacion`, `simulacion`, `orden_rumbo`** | Nada en tiempo de ejecución (sin importadores). Se rompe el **plan**: Biblia VIII (paquete base, revisor) y IX capas 3/4/5 siguen «BLOQUEADO» esperando un `claude -p` real; borrar 427 líneas probadas (40 pruebas) obliga a rehacerlas. `simulacion.py` usa `numpy`, que `calibracion.py` también usa: la dependencia queda | `test_produccion.py`, `test_juego.py`, `test_estimacion.py`, `test_simulacion.py`, `test_orden_rumbo.py`; `analisis_camino.py` conserva su `Protocol Investigador` y el campo `juego` | `[MEDIO]`. **Congelar** (A lo permite) es seguro; **Quitar**, no sin decidir qué pasa con las fases R3-R5/PR |
| **Quitar `limpiar_pruebas.py`** | Se pierde la herramienta para sacar de la base real lo que dejó probar Remi («día cero»); `trabajo.py:48` documenta que `limpiar_pruebas` usa su función | `test_limpiar_pruebas_dia_cero.py` | `[BAJO]` |
| **Quitar `sanear.py`** | `db.py:741` (`sesiones abiertas`) la documenta «las usa `nucleo/sanear.py`»: queda sin usuario. Sin ella no hay forma manual de cerrar sesiones colgadas, que alimentan la **ley 1** («la última vez esto te tomó…») | sin pruebas propias | `[BAJO]` |
| **Quitar `probar_bloqueos.py`** | Es la **única comprobación ejecutable** de que `claude -p` no puede leer claves (`pensar.py:118 PATRONES_QUE_NO_SE_LEEN`); borrarla deja esa defensa sin prueba | ninguna | `[MEDIO]` (seguridad, regla 4 de `AGENTS.md`) |
| **Quitar `sembrar_memoria.py`** | La tabla `memoria` tiene 0 filas (A, hallazgo #1) y este script es *la* siembra «desde el primer día»; quitarlo contradice el hallazgo | `test_memoria.py` | `[MEDIO]` |
| **Quitar `ventanita/src/componentes/Reloj.tsx`** | Nada en ejecución (solo comentarios mencionan el Reloj en `App.tsx:202,480`). `CLAUDE.md:35` lista `Reloj` con la piel `brasa` como componente canónico; el panel conserva el suyo (`apps/panel/src/components/Reloj.tsx`) | sin pruebas | `[BAJO]` |
| **Quitar de la instalación `tunel`, `notion` y `refresco-claude-code`** | `scripts/desinstalar.sh:19` lista esas etiquetas; `doctor.sh` chequeo 6 y 9 las cuentan (A: `:100-133`, `:166-178`). Sin `notion` el espejo nunca corre aunque se ponga token (es lo que quiere el «dormido», pero hay que decirlo). Sin `refresco`, la promesa de `ARQUITECTURA §13` («se refresca cada semana desde el changelog») queda sin ejecutor | `test_notion_sync.py`; las pruebas de `refresco_claude_code` (1 archivo, 8 pruebas según A) | `[MEDIO]` |
| **Mover a `docs/archivo/` los «históricos»** (`PLAN-100`, `PLAN-CIERRE`, `PLAN-REVISION`, `REVISION`, `ENCARGO-VELOCIDAD`, `AUDITORIA-BIBLIA`) | **`REVISION.md` no es histórico:** `precarga.py:287` la lee por ruta fija y alimenta la respuesta a «¿qué te falta?» (`:370-376`); movida, esa respuesta pierde su fuente sin error visible. `BIBLIA` Parte VII cita `docs/AUDITORIA-BIBLIA.md`; `test_t2_voz.py:2` cita `docs/PLAN-100.md` (solo docstring) | `test_estado_propio.py` usa `monkeypatch` (no se rompe); producción sí | `[MEDIO]` por `REVISION.md`; el resto `[BAJO]` |
| **Quitar la rama `EN_EL_CHAT` de `preguntas.py`** (Simplificar) | `BIBLIA.md` v4.1 la documenta como «existe apagado» a propósito | `test_preguntas_telegram.py` y `test_preguntas_en_el_aire.py` (4 referencias) | `[BAJO]` |
| **Unir `config/` y `nucleo/config/`** (Simplificar) | Hay que tocar 3 constantes de ruta: `gasto.py:21-22`, `pensar.py:72`, y `avisos.py:22` (que hoy lee un `config/avisos.json` inexistente y cae a defaults; al moverlo leería el de `nucleo/config/`, mismos valores 5/45) | `REMI_MOTORES` en pruebas; ajustes `/config/gasto` | `[BAJO]` |

Veredictos de **mi** informe que A discute y que aquí **no** tocan nada nuevo: «Reemplazar LangGraph» (A: `[BAJO]`, lo acepto: script suelto, sin importadores en Remi) y «PyYAML único» (A: `[MEDIO]`, lo acepto: su prueba de `ScannerError` con «:» en un título es correcta y es un riesgo real que no medí).

---

## 5. Qué bloquea el plan (`[ALTO]` abiertos tras esta revisión)

1. **Trastienda sin filtro y sin llave** (§1 #9): ningún otro cambio en `pensar.py` antes de decidir. **Aceptado por ambas.**
2. **Token de Telegram en `nucleo.log`** (§1 #6): rotar y limpiar.
3. **Copia restic parada** (§1 #4): cargar `com.remi.copia` (y `vigia`). *Mi propuesta de mover el vigía a un hilo queda retirada (§3.6).*
4. **Sin hooks de Claude Code** (§1 #7) y, añadido por mí, sin MCP global (N-1).
5. **Mi Top 5 #5 (un solo Whisper)** queda invalidado hasta cargar `com.remi.whisper` (§3.3).

Los `[MEDIO]` nuevos (N-1, N-2, N-3) no bloquean, pero N-2 toca la misma frontera de privacidad que el #1.

---

## 6. Qué no verifiqué

- **Que la trastienda realmente haga el POST** (lo leí, no lo ejecuté: habría salido a la red). Tampoco medí cuántas veces ocurrió ya; con 4 turnos en la base, probablemente ninguna.
- **El contenido del disco Time Machine «Copias»** (`Operation not permitted`) ni si respalda `~/proyectos/remi`.
- **El repositorio restic de iCloud** (cifrado, clave en el Llavero; no lo abrí).
- **Las 91 rutas** (solo comprobé las 54 de `servidor.py`) y los números de «solo pruebas»/«sin cliente» de §1.3 de A.
- **Los conteos de `def test_` por módulo** de la tabla §1.1 de A y los «66/551» de `servidor`; ni la lista completa de funciones muertas de §3.1.
- **Playwright, `doctor.sh` y el pytest completo** (corrí solo los 6 fallos). Los 1064 pasan: lo tomo de A.
- **Si el `.mcp.json` está aprobado** en Claude Code (N-1) y **si Handy borra modelos** (N-3): ambos son hipótesis marcadas.
- **Qué hace Grok Bot** con `rumbo.py`/`capturador.py` de la bóveda (proceso externo).

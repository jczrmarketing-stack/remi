# Auditoría A — Inventario honesto de Remi

- **Fecha:** 2026-10-26 · **Rama:** `main` · **HEAD al empezar:** `66b19bc` (la sesión paralela «Auditoría B» hizo ese commit mientras yo leía; no lo toqué).
- **Alcance:** solo lectura. No cambié código, config, base ni bóveda. Escribí solo este archivo y scripts temporales en el scratchpad de la sesión (`/private/tmp/claude-501/-Users-juancamilo/b7a3da1c-a39d-4746-96ea-f43dd784242e/scratchpad/`, que hace de `/tmp`).
- **No llamé** a Telegram, Notion, la web ni al puerto 4400. Por eso **no corrí `scripts/doctor.sh`** (su chequeo 1 llama a `/salud` en :4400, `scripts/doctor.sh:50`).
- **Leyenda de gravedad:** `[ALTO]` rompe una promesa de la Biblia o pone datos/credenciales en riesgo · `[MEDIO]` cuesta mantenimiento o engaña al leer · `[BAJO]` limpieza.
- **Leyenda de estado (sección 2):** **USADO** = código + pruebas + datos reales en `remi.db` (o un cliente vivo que lo llama y no deja datos, como `/tts`) · **HECHO, SIN USO** = código y pruebas, 0 filas · **SOLO PRUEBAS** = nada de producción lo llama · **PARCIAL** · **NO EXISTE**.
- **Regla de lectura:** lo que dice «Sabemos» lleva `archivo:línea` o un comando que lo prueba. Lo que dice «Hipótesis» no está probado y lo marco así.

## Plan de revisión (lo que escribí antes de empezar)

1. Ubicar el repo, leer los seis documentos pedidos y la bóveda `/Volumes/ORGANIC/Remi` (Hoy.md y últimas 10 líneas de Bitacora.md).
2. Con scripts (AST, grep, sqlite en `mode=ro`): grafo de imports de `nucleo/`, rutas HTTP y sus llamadores, código sin referencias, filas por tabla.
3. Cruzar la Biblia v4.2 contra código, pruebas y datos; leer la bitácora para sacar BLOQUEADO y ESPERA.
4. Correr pytest, mypy, vitest (y `tsc --noEmit` de las dos apps) con la base y la bóveda apuntadas a temporales.
5. Redactar las seis secciones y la tabla final; commit solo de este archivo.

---

## Resumen: lo más grave

| # | Gravedad | Hallazgo | Prueba |
|---|---|---|---|
| 1 | `[ALTO]` | **Remi no tiene datos.** `remi.db` tiene 0 filas en `tareas`, `sesiones`, `ideas`, `memoria`, `entregas`, `preguntas`, `nudges` y todas las tablas del Rumbo; y `conocimiento/` solo tiene `experiencia/` (2 archivos): no hay `caracter.md`, ni `oficios/`, ni `proyectos/`. Remi hoy piensa con el «carácter de respaldo» (`nucleo/pensar.py:195-203`). | §2.0 |
| 2 | `[ALTO]` | **El historial de git empieza hoy** (`b08962d`, 2026-10-26 06:17). Los hashes que cita la bitácora (`742bd8f`, `123fdc1`, `5f6e1e2`, `f7f1228`, `9bfefc9`, `b464770`) no existen, y no hay remoto: el código no tiene copia fuera de este Mac. | `git cat-file -t 742bd8f` → «Not a valid object name»; `git remote -v` → vacío |
| 3 | `[ALTO]` | **Lo «indestructible» de la Biblia no está corriendo.** Solo `com.remi.nucleo` y `com.remi.noche` están cargados; copia, vigía, túnel, whisper, notion, refresco y panel (7 de los 10 servicios de `instalar.sh`) no. El repositorio restic de iCloud tiene `data/` modificado el 2-oct 22:46 y la carpeta el 3-oct 19:41 (nada más reciente). No existe `~/Library/Logs/Remi/noche.log` ni `copia.log`. | §3.4 |
| 4 | `[ALTO]` | **Un token de Telegram quedó en `nucleo.log`** (1 línea con `api.telegram.org/bot<token>`). La bitácora ya lo avisó el 26-oct y nadie lo arregló; la regla 4 de AGENTS.md prohíbe credenciales en logs. No imprimí el valor. | `grep -c "api.telegram.org/bot[0-9]" ~/Library/Logs/Remi/nucleo.log` → 1 |
| 5 | `[ALTO]` | **Remi no se entera de las sesiones de Claude Code.** `~/.claude/settings.json` no tiene el hook `claude-sesion.py`; `trabajo_claude` = 0 filas. Sin eso, «la terminal está trabajando», `terminal_termino` y el cierre de hitos por encargo no pueden ocurrir. Los commits sí llegan (≥15 filas `commit` en `trabajo_eventos`). | §2.3 |
| 6 | `[ALTO]` | **No hay plan B real si Max se agota.** `nucleo/.env` solo tiene `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`: sin llaves de Groq, OpenRouter, Venice ni Notion, el respaldo (`pensar.py:1639 _respaldo_de_charla`) devuelve `None` y Remi contesta sin IA. | `sed -E 's/=.*//' nucleo/.env` |
| 7 | `[MEDIO]` | **596 líneas del Rumbo no las llama nadie fuera de las pruebas** (`estimacion`, `simulacion`, `orden_rumbo`, `produccion`, `juego`, `claves`) más 369 de pruebas. Hoy **no** se ordena por el Rumbo; el investigador, los estimadores a ciegas y el revisor reales nunca se construyeron (BLOQUEADO en bitácora). | §3.1 |
| 8 | `[MEDIO]` | **6 pruebas fallan** en un núcleo sano: dependen de `conocimiento/` real (gitignored) y ya no está. `docs/ahora.md:17-19` las atribuye a «oficios, Notion, Ollama»; la causa real es esa. | §6 |
| 9 | `[MEDIO]` | **El panel escucha en todas las interfaces** (`*:4402`) (`next-server`, arrancó 07:14, no está bajo launchd), sin túnel ni Access. | `lsof -nP -iTCP:4402 -sTCP:LISTEN` |
| 10 | `[MEDIO]` | **Cuatro archivos concentran la complejidad:** `servidor.py` 2477 líneas (54 rutas propias + 60 modelos), `pensar.py` 1968 (44 `except`), `db.py` 1597, `App.tsx` 1873 (un solo componente de ~1680 líneas). | §5.1 |
| 11 | `[MEDIO]` | **El presupuesto de silencio está implementado tres veces con dos valores** (45 min en `iniciativa.py:33` y `config/avisos.json:5`; 90 min en `notion_avisos.py:53`). | §5.3 |
| 12 | `[MEDIO]` | **113 clases `BaseModel` escritas a mano fuera de `modelos.py`**, contra `CLAUDE.md:44` («se generan de ahí, jamás se escriben a mano»); y las formas J–S del plan no están en `contratos.json`. | §5.6 |

**Lo que sí está bien (también cuenta):** mypy limpio en 193 archivos; 122 pruebas de vitest verdes; `tsc --noEmit` con exit 0 en las dos apps; las 62 piezas del núcleo se importan solas sin romperse (los ciclos son benignos, §5.2); las seis leyes no tienen violaciones visibles en el código de producción (§2.1); y las pruebas tienen una guardia de red que corta Telegram/Notion/:4400 (`nucleo/pruebas/conftest.py:55-70`).

---

## 1. Mapa

### 1.1 `nucleo/` — 62 módulos, 19 372 líneas (+ 130 archivos de prueba, 18 721 líneas)

Columnas: **Llama a** = imports internos (`*` = import dentro de una función); **Lo llaman** = módulos que lo importan, o su entrada externa si no tiene importador; **Pruebas** = archivos/`def test_` que lo mencionan (un módulo de base como `db` sale en casi todos). Generado por script (apéndice A). La lista completa de aristas está en el apéndice B.

| Módulo | Líneas | Qué hace | Llama a | Lo llaman | Pruebas | Nota |
|---|---|---|---|---|---|---|
| `servidor.py` | 2477 | API HTTP del núcleo (FastAPI): 91 rutas, 60 modelos de respuesta, el despacho de `/mensaje` (`_atender`, :507) y el ciclo de vida (hilos de Telegram, TTS, Notion) | agenda, aldia, analisis_camino, avisos, bandeja, boveda_git, calendario (+35) | telegram | 66/551 |  |
| `pensar.py` | 1968 | Motores de IA (Claude por Max, Groq, OpenRouter, Venice, Ollama), system prompt con índice de la mente, historial de conversación, resumen vivo y respaldos | concreto, db, gasto, libros, precarga, trabajo, vectores (+4) | cierre, claves, coding, episodios, estado_libro, probar_bloqueos (+2) | 26/261 |  |
| `db.py` | 1597 | Esquema SQLite (30 tablas) y todo el acceso a datos: tareas, sesiones, ideas, memoria, turnos, rumbo, pronósticos… | modelos | aldia, analisis_camino, calendario, calibracion, cierre, coding (+24) | 90/718 |  |
| `trabajo.py` | 711 | Recibe eventos de git y de Claude Code (`recibir`, :439), los guarda y cierra hitos por encargo | avisos, boveda_git, caminos, clasificar, db, episodios, estado_libro (+4) | ficha, limpiar_pruebas, pensar, rumbo, servidor | 9/60 |  |
| `experiencia.py` | 628 | T8 (Biblia v3.9, Parte VII «La experiencia es memoria»): lecciones con evidencia, no transcripts | boveda_git, db, episodios, libros, vectores, correcciones, modelos | cierre, coding, memoria_mcp, noche, notion_sync, preguntas (+2) | 8/59 |  |
| `preguntas.py` | 618 | T3 (fase Q, Biblia v3.8): Remi pregunta lo que le falta — nunca un humano, nunca un chat, nunca un modelo | boveda_git, clasificar, db, entregas, iniciativa, libros, modelos (+3) | noche, servidor | 5/44 |  |
| `rumbo.py` | 612 | R1 (forma N, PLAN-FINAL.md): Rumbo — visión, meta, escalera y punto de partida | db, modelos, plata, reloj, trabajo | servidor | 1/18 |  |
| `coding.py` | 504 | Coding con la bóveda delante (Biblia Parte VII + VIII) | db, experiencia, pensar, telegram | pensar, servidor | 2/15 |  |
| `cierre.py` | 475 | Al cerrar Claude Code, un episodio y el Estado del libro. | boveda_git, db, episodios, estado_libro, experiencia, libros, modelos (+2) | noche, pensar, servidor, trabajo | 5/26 |  |
| `notion_sync.py` | 436 | Fase 4 · espejo de Notion: proyectos y entregas. | boveda_git, db, entregas, estado_libro, experiencia, libros, notion | notion | 1/11 |  |
| `telegram.py` | 396 | Telegram (Biblia Parte IV): el teléfono — avisos y charla corta. | entregas, servidor | coding, conexiones, noche, preguntas, servidor | 3/54 |  |
| `precarga.py` | 384 | Precarga del proyecto activo (ARQUITECTURA-CEREBRO §4). | db, libros, estado_libro, sembrar_conocimiento, temas | pensar, servidor | 7/42 |  |
| `notion_avisos.py` | 371 | Puente Notion → Ventanita: los avisos de «Remi · CRM de vida». | avisos, db, notion | servidor | 1/6 |  |
| `caminos.py` | 369 | La sección «## Camino» de un libro de proyecto: hitos «- [ ] …» / «- [x] …». | libros | aldia, ficha, servidor, trabajo | 5/34 |  |
| `noche.py` | 354 | Consolidación nocturna (ARQUITECTURA-CEREBRO §6): LaunchAgent com.remi.noche a las 4:00, después de la copia d | boveda_git, db, estado_libro, experiencia, libros, preguntas, sembrar_conocimiento (+2) | scripts/noche.sh (launchd) | 5/76 |  |
| `aldia.py` | 342 | B2: «Al día» — Remi sabe en qué vas, sin que lo marques (PLAN-FINAL.md, forma J) | caminos, db, entregas, libros | ficha, servidor | 1/11 |  |
| `avisos.py` | 323 | B5 (docs/PLAN-FINAL.md): avisos que jalan la atención — los únicos tres con sonido: `terminal_termino` (cierra | accesibilidad | notion_avisos, servidor, trabajo | 4/40 |  |
| `plata.py` | 320 | La plata del mes (Panel · Metas): sin regaños, solo números. | db, ficha | entregas, limpiar_pruebas, rumbo, semana, servidor | 6/74 |  |
| `libros.py` | 301 | Lee/escribe los libros de proyecto (`conocimiento/proyectos/*.md`): ruta, tema, frontmatter | — | aldia, boveda_git, caminos, cierre, claves, entregas (+12) | 17/111 |  |
| `iniciativa.py` | 289 | El motor de iniciativa (Biblia Parte III «el que sabe cuándo», ley 6). | bandeja, modelos | preguntas, servidor | 2/24 |  |
| `entregas.py` | 280 | Entregas (3f · 2): CRUD del contrato Entrega, aparte de servidor.py — un router que se incluye con una sola lí | db, libros, modelos, plata | aldia, ficha, notion_sync, preguntas, servidor, telegram | 6/52 |  |
| `estado_libro.py` | 258 | La sección «Estado» de un libro de proyecto. | pensar | cierre, noche, notion_sync, precarga, refresco_claude_code, servidor (+1) | 4/45 |  |
| `notion.py` | 245 | Cliente delgado de la API de Notion, y la puerta HTTP del sync (Fase 4). | notion_sync | notion_avisos, notion_sync, servidor | 2/21 |  |
| `memoria_mcp.py` | 231 | El estante de Remi, como servidor MCP (stdio). | db, experiencia, modelos | .mcp.json (MCP) | 6/47 |  |
| `conexiones.py` | 223 | Conexiones (Panel → Ajustes): llaves y tokens, nunca su valor completo. | telegram | servidor | 3/67 |  |
| `limpiar_pruebas.py` | 215 | Lo que quedó de probar Remi en la base real — dos patrones, nada más: | db, plata, trabajo | scripts/archivar_ruido_de_sesiones.py | 1/4 |  |
| `modelos.py` | 212 | Generado desde contratos/contratos.json por generar_modelos.py. | — | analisis_camino, bandeja, calendario, calibracion, cierre, db (+12) | 16/175 |  |
| `clasificar.py` | 210 | Reglas de texto (sin IA): ¿cobro, gasto, idea, cliente, cortesía, «anota esto», petición de búsqueda? | — | mensaje_cliente, preguntas, servidor, temas, trabajo | 4/79 |  |
| `vectores.py` | 209 | Vectores locales de la bóveda (ARQUITECTURA-CEREBRO §3 / Biblia Parte IV·B). | libros | experiencia, pensar | 7/32 |  |
| `sembrar_conocimiento.py` | 203 | Mete las fichas de conocimiento/proyectos/*.md en el estante. | db, modelos | correcciones, noche, pensar, precarga, refresco_claude_code, servidor | 6/60 |  |
| `ficha.py` | 198 | B6: los números derivados de la ficha de cliente — gastado (agrupado), tiempo total y por_hora | aldia, caminos, db, entregas, libros, trabajo | plata, servidor | 4/35 |  |
| `analisis_camino.py` | 183 | R3 (forma Q, PLAN-FINAL.md): el análisis de un camino | db, modelos | servidor | 1/5 |  |
| `calibracion.py` | 179 | R4.5 (forma P, PLAN-FINAL.md): pronósticos y calibración. | db, modelos | servidor | 1/6 |  |
| `refresco_claude_code.py` | 172 | Refresco semanal del oficio Claude Code (Biblia Parte VI, Fase S punto 5). | boveda_git, estado_libro, pensar, sembrar_conocimiento | scripts/refresco-claude-code.sh | 1/8 |  |
| `episodios.py` | 170 | Una charla pegada se guarda como episodio (3c · 7). | boveda_git, db, modelos, pensar | cierre, experiencia, servidor, trabajo | 3/21 |  |
| `claves.py` | 169 | Claves (3–6 palabras) en el frontmatter de libros, oficios y episodios. | boveda_git, libros, pensar | — | 1/7 | SOLO PRUEBAS |
| `bandeja.py` | 168 | La Bandeja (Ley 6): lo suelto enfría 48 h antes de una revisión en frío. | modelos | iniciativa, semana, servidor | 0/0 |  |
| `reloj.py` | 166 | R2 (forma S, PLAN-FINAL.md): el Reloj — estimación basada en evidencia (EBS de Joel Spolsky) | db | rumbo, servidor | 2/17 |  |
| `voseo.py` | 166 | De vos a tú, sin modelo. | — | pensar | 1/6 |  |
| `gasto.py` | 164 | Tope de gasto en los motores pagados (B1, docs/PLAN-FINAL.md) | db | pensar, servidor | 5/103 |  |
| `correcciones.py` | 161 | Aprender de las correcciones (Biblia Parte VI): Remi propone, nunca guarda solo. | boveda_git, db, sembrar_conocimiento | experiencia, preguntas, servidor | 1/11 |  |
| `tts.py` | 139 | Voz de Remi, local y sin clave: Kokoro-82M en CPU. | — | servidor | 1/13 |  |
| `produccion.py` | 136 | PR (PLAN-FINAL.md, Biblia Parte VIII): del encargo a producción | — | — | 1/8 | SOLO PRUEBAS |
| `calendario.py` | 118 | B10.1 (PLAN-FINAL.md): Google Calendar | db, modelos | servidor | 2/10 |  |
| `generar_modelos.py` | 113 | Genera nucleo/modelos.py desde contratos/contratos.json. | — | CLI (genera modelos.py) | 0/0 |  |
| `agenda.py` | 109 | Agenda por voz (T2.5): «mañana…», «a las 3…», «el viernes…», «vence el 15 de octubre…» crean una tarea con fec | — | servidor | 0/0 |  |
| `semana.py` | 104 | GET /semana (Forma D, T4.2): las cinco preguntas del panel «Semana» contestadas con datos reales — de lunes (B | bandeja, db, plata | servidor | 1/6 |  |
| `gastos.py` | 103 | B6.1: un gasto que llega hablado — «gasté 40 en el servidor de UpVisuals», «pagué 20 del dominio», «la membres | temas | servidor | 2/21 |  |
| `juego.py` | 99 | R3 (PLAN-FINAL.md): «Ábreme el juego» — 20 jugadas con muestreo verbalizado y los lentes de la Parte IX | modelos | — | 1/6 | SOLO PRUEBAS |
| `temas.py` | 80 | A qué libro pertenece una idea (Biblia v3.7: `Idea.tema`). | clasificar, libros | cierre, cobros, gastos, hilos, precarga, servidor | 2/8 |  |
| `concreto.py` | 79 | Si piden un prompt, el prompt sale primero. | — | pensar | 1/6 |  |
| `sembrar_memoria.py` | 78 | Pone en el estante lo que Remi tiene que saber desde el primer día. | db, modelos | CLI manual | 1/19 |  |
| `boveda_git.py` | 72 | Cada escritura de Remi en la bóveda queda con revert real. | libros | cierre, claves, correcciones, episodios, experiencia, noche (+5) | 3/25 |  |
| `estimacion.py` | 70 | R4.1-R4.3 (PLAN-FINAL.md): números honestos | — | — | 2/15 | SOLO PRUEBAS |
| `simulacion.py` | 68 | R4.4 (PLAN-FINAL.md): simulación de seis meses, sembrada con `numpy` (misma semilla → mismas bandas, siempre) | — | — | 1/6 | SOLO PRUEBAS |
| `probar_bloqueos.py` | 67 | ¿Remi puede leer una clave? Prueba de verdad, con la CLI (3c · 10). | pensar | CLI manual | 0/0 |  |
| `accesibilidad.py` | 59 | B10.2 (PLAN-FINAL.md): accesibilidad de macOS — la app activa y el título de ventana entran como contexto | — | avisos | 2/24 |  |
| `sanear.py` | 56 | Cierra las sesiones que quedaron abiertas y nadie cerró. | db | CLI manual | 0/0 |  |
| `orden_rumbo.py` | 54 | R5.1 (PLAN-FINAL.md): Hoy ordenado por el Rumbo | — | — | 1/5 | SOLO PRUEBAS |
| `cobros.py` | 42 | Un cobro que llega hablado (T2.4): «Alfonso pagó 1.000», «me pagaron 1.500 de UpVisuals» | temas | servidor | 1/11 |  |
| `mensaje_cliente.py` | 39 | B3.1: «ya le mandé el avance a Alfonso» cierra el hito de ese cliente cuyo `cierra_con` es "mensaje" — sin IA, | clasificar, libros | servidor | 1/5 |  |
| `hilos.py` | 30 | Hilos por tema (B7): anota qué quedó a medias al saltar de proyecto y lo devuelve una vez | db, temas | servidor | 0/0 |  |

### 1.2 Grafo de dependencias de `nucleo/`

Generado con `ast` (apéndice A, `grafo.py`): 62 nodos; aristas de importación a nivel de módulo y dentro de funciones (`*`).

**Sabemos:**
- **Fan-in más alto** (los cimientos): `db` 30 · `libros` 18 · `modelos` 18 · `boveda_git` 11 · `pensar` 8 · `experiencia` 8 · `estado_libro` 7.
- **Fan-out más alto:** `servidor` 42 (importa 42 de los otros 61 módulos) · `pensar` 11 · `trabajo` 11 · `preguntas` 10 · `cierre` 9 · `noche` 9.
- **Hojas puras** (no importan nada interno): `libros`, `modelos`, `clasificar`, `voseo`, `tts`, `concreto`, `agenda`, `estimacion`, `simulacion`, `produccion`, `generar_modelos`, `orden_rumbo`, `accesibilidad`.
- **Ciclos de importación a nivel de módulo (SCC de tamaño > 1):** dos.
  1. `pensar → trabajo → estado_libro → pensar` y `trabajo → episodios → pensar` (4 módulos: `episodios`, `estado_libro`, `pensar`, `trabajo`).
  2. `aldia → entregas → plata → ficha → aldia` (4 módulos).
- **Si se cuentan también los imports dentro de funciones**, 21 módulos quedan en una sola componente fuertemente conexa (`servidor`, `pensar`, `trabajo`, `cierre`, `telegram`, `notion`, `notion_sync`, `notion_avisos`, `coding`, `experiencia`, `preguntas`, `rumbo`, `semana`, `precarga`, `plata`, `entregas`, `ficha`, `aldia`, `conexiones`, `episodios`, `estado_libro`).
- **Pares mutuos:** `cierre↔pensar`, `coding↔pensar`, `notion↔notion_sync`, `servidor↔telegram` (todos resueltos con import dentro de función).
- **Módulos sin importador** (solo los llama una entrada externa o nadie): `noche` (launchd vía `scripts/noche.sh`), `memoria_mcp` (`.mcp.json`), `refresco_claude_code`, `limpiar_pruebas`, `sembrar_memoria`, `sanear`, `probar_bloqueos`, `generar_modelos` (CLI), y **seis que solo llaman las pruebas:** `claves`, `estimacion`, `simulacion`, `orden_rumbo`, `produccion`, `juego`.

**Hipótesis:** que `servidor` importe casi todo es lo esperable de un archivo de rutas; lo que no es esperable es que `pensar` (un motor de IA) importe `cierre` y `coding` (módulos de flujo) y que `trabajo`→`pensar`→`trabajo` sea un ciclo. Ver §5.2.

### 1.3 Rutas HTTP del núcleo — 91

`python3 -I rutas.py` (apéndice A): 54 rutas en `servidor.py` y 37 en 14 routers (13 módulos). Se buscó cada ruta (con sus parámetros) en `apps/panel/src`, `apps/ventanita/src`, `scripts/`, `apps/panel/tests`, `nucleo/pruebas` y `nucleo/`.

- **67 rutas VIVAS** (las llama el panel, la ventanita o un script).
- **19 rutas SOLO PRUEBAS** y **5 SIN CLIENTE** (ni el panel, ni la ventanita, ni un script, ni una prueba):

| Ruta | Definida en | Estado |
|---|---|---|
| `GET /avisos/hoy` | `servidor.py:1956` | solo pruebas |
| `GET /calendario/estado` | `calendario.py:115` | solo pruebas |
| `POST /calendario/importar` | `calendario.py:105` | solo pruebas |
| `GET /calibracion` | `calibracion.py:164` | solo pruebas |
| `POST /cobros` | `entregas.py:238` | solo pruebas |
| `POST /entregas/{entrega_id}/estado` | `entregas.py:270` | sin cliente |
| `POST /experiencia` | `experiencia.py:578` | solo pruebas |
| `GET /experiencia` | `experiencia.py:599` | solo pruebas |
| `POST /idea/{idea_id}/tema` | `servidor.py:1883` | solo pruebas |
| `GET /memoria` | `servidor.py:1477` | solo pruebas |
| `POST /memoria` | `servidor.py:1508` | solo pruebas |
| `GET /memoria/{memoria_id}` | `servidor.py:1496` | solo pruebas |
| `PATCH /memoria/{memoria_id}` | `servidor.py:1533` | solo pruebas |
| `GET /notion/estado` | `notion.py:229` | sin cliente |
| `POST /notion/sincronizar` | `notion.py:234` | sin cliente |
| `POST /pronosticos` | `calibracion.py:110` | solo pruebas |
| `POST /pronosticos/{pronostico_id}/resolver` | `calibracion.py:128` | solo pruebas |
| `GET /reloj/estimar` | `reloj.py:152` | solo pruebas |
| `POST /rumbo/apuestas/{apuesta_id}/cerrar` | `rumbo.py:507` | solo pruebas |
| `GET /rumbo/poda` | `rumbo.py:605` | sin cliente |
| `POST /rumbo/propuestas` | `rumbo.py:324` | sin cliente |
| `POST /sesion/{sesion_id}/cerrar` | `servidor.py:1189` | solo pruebas |
| `POST /tarea/{tarea_id}/agenda` | `servidor.py:1271` | solo pruebas |
| `GET /tarea/{tarea_id}/historial` | `servidor.py:1746` | solo pruebas |

**Hipótesis:** `/memoria*` y `/experiencia*` pueden usarse desde el MCP o desde Claude Code a mano (`curl`); el patrón no lo ve. Las cinco «sin cliente» son: `POST /entregas/{id}/estado`, `GET /notion/estado`, `POST /notion/sincronizar`, `GET /rumbo/poda`, `POST /rumbo/propuestas`.

### 1.4 `apps/ventanita` — Tauri 2 + React (10 277 líneas: TS/TSX/CSS 8 447 + Rust 1 830)

| Pieza | Líneas | Qué hace | La llama | Llama |
|---|---|---|---|---|
| `src/App.tsx` | 1873 | Un solo componente `App` (`:192` a `:1873`): estados reposo/escuchando/pensando/hablando, 1/2/3 clics, dictado, chat, nudges, avisos | `main.tsx` | `componentes/*`, `servidor.ts`, `voz.ts`, `gestos.ts`… |
| `src-tauri/src/voz.rs` | 1541 | Grabación, detección de silencio, Whisper (`whisper-cli` o servidor residente en :4401), 40 funciones | Tauri | binarios de Homebrew |
| `src/voz.ts` | 587 | Voz del sistema/Kokoro, velocidad, cola de frases | `App`, `ChipVoz`, `StatusDot`, `AccionesRespuesta` | `/tts` |
| `src/servidor.ts` | 348 | Cliente del núcleo: 20 rutas (`/mensaje`, `/mensaje/stream`, `/conversaciones`, `/pensar/motores`…) | `App`, `ChipCerebro`, `Historial` | núcleo :4400 |
| `src/gestos.ts` | 316 | Lógica pura de los gestos (sin React ni Tauri) | `App` | — |
| `src/preferencias.ts` | 235 | Preferencias persistidas (localStorage) | `App`, chips, `voz` | — |
| `src/componentes/*` (14 `.tsx` + CSS) | ver `wc -l` | `Chat`, `Nudge`, `Campo`, `Historial`, `ChipCerebro/Lectura/Voz`, `StatusDot`, `Semaforo`, `AvisoNotion`… | `App` | — |
| `src/componentes/Reloj.tsx` | 29 | Reloj piel brasa | **nadie** (`[BAJO]` muerto) | — |
| `src/*.prueba.ts` (18 archivos) | ~1 400 | vitest: gestos 467, voz 153, markdown 89, preferencias 86… | `npm test` | — |

### 1.5 `apps/panel` — Next.js 15 PWA (5 718 líneas en `src/`, 1 749 en `tests/`)

| Pantalla (ruta) | Archivo | Líneas | Llama al núcleo | Prueba e2e |
|---|---|---|---|---|
| Hoy `/` | `src/app/page.tsx` | 582 | `/hoy`, `/hoy/aldia`, `/hoy/agenda`, `/preguntas`, `/nudges/pendiente`, `/avisos/pendiente`… | `tests/hoy.spec.ts` |
| Bandeja `/bandeja` | `bandeja/page.tsx` | 168 | `/bandeja`, `/idea/{id}/revision`, `/idea/{id}/destacar` | `bandeja.spec.ts` |
| Proyectos `/proyectos` | `proyectos/page.tsx` | 224 | `/libros` | `proyectos.spec.ts` |
| Proyecto/ficha `/proyectos/[tema]` | `proyectos/[tema]/page.tsx` | 569 | `/libros/{tema}`, `/libros/{tema}/camino/{n}[/deshacer]`, `/gastos/{id}`, `/entregas*` | `proyecto.spec.ts` |
| Metas `/metas` | `metas/page.tsx` | 247 | `/plata`, `/rumbo` | `metas.spec.ts` |
| Semana `/semana` | `semana/page.tsx` | 246 | `/semana` | `semana.spec.ts` |
| Rumbo `/rumbo` | `rumbo/page.tsx` | 433 | `/rumbo`, `/rumbo/cuenta`, `/rumbo/apuestas`, `/rumbo/vision`, `/rumbo/meta` | `rumbo.spec.ts`, `rumbo-cuenta.spec.ts` |
| Rumbo · camino | `rumbo/caminos/[id]/page.tsx` | 155 | `/rumbo/caminos/{id}` | `rumbo-camino.spec.ts` |
| Rumbo · partida | `rumbo/partida/page.tsx` | 112 | `/rumbo` | `partida.spec.ts` |
| Rumbo · motor | `rumbo/motor/page.tsx` | 80 | `/rumbo/latido`, `/config/gasto` | `rumbo-motor.spec.ts` |
| Ajustes `/ajustes` | `ajustes/page.tsx` + `components/Conexiones.tsx` | 118 + 244 | `/config/conexiones*`, `/config/plata`, `/config/gasto` | `ajustes.spec.ts` |
| Coding `/coding` | `coding/page.tsx` | 273 | `/coding/estado`, `/coding/lecciones`, `/coding/corrida*` | **ninguna** (no hay `coding.spec.ts`) |

Soporte: `components/` (15 piezas canónicas: `StatusDot`, `Reloj`, `Chip`, `ProgressBar`, `ProjectPath`, `NudgeCard`… — todas con importador), `lib/nucleo.ts` (405, cliente tipado), `lib/hoy.ts`, `lib/lider.ts`, `lib/proyecto.ts`, `lib/formato.ts`, `bionica.ts`, `hooks/` (2). El panel no tiene `vitest`; su prueba es Playwright contra un núcleo falso (`tests/nucleo-falso.mjs`), que **no corrí** (§6).

### 1.6 Todo lo demás

| Carpeta | Contenido | Estado |
|---|---|---|
| `scripts/` (18 + `hooks/`) | `instalar/desinstalar/actualizar/recargar.sh`, `doctor.sh` (11 chequeos), `copia.sh`, `copia-comun.sh`, `restaurar.sh`, `noche.sh`, `vigia.sh`, `tunel.sh`, `rotar-logs.sh`, `refresco-claude-code.sh`, `banco.py`, `sembrar_camino.py`, `oficios_a_skills.py`, `skill_a_oficio.py`, `archivar_ruido_de_sesiones.py` | todos referenciados por otro archivo; ver §3.4 |
| `scripts/hooks/` | `git-gancho` (post-commit → núcleo), `avisar-commit.py`, `claude-sesion.py`, `instalar-*.{sh,py}` | git: funciona (15 eventos `commit`); Claude Code: **no instalado** |
| `config/` | `apps_trabajo, copia, nucleo, plata, rumbo, ventanita .json` | sin claves muertas reales (§3.3) |
| `nucleo/config/` | `avisos.json`, `gasto.json`, `motores.json` | **segunda carpeta de config**. `avisos.py:22` lee `config/avisos.json` de la **raíz**, donde no existe: `leer_config` (`avisos.py:96-99`) cae a `CONFIG_POR_DEFECTO` (`:71`, mismos valores 5/45). `nucleo/config/avisos.json` no lo lee nadie (`[BAJO]`); `gasto.py:21` y `pensar.py:72` sí leen `nucleo/config/` |
| `nucleo/prompts/` | `cliente.md`, `encargo.md`, `tecnico.md` | en uso (`pensar.py:303-357`) |
| `contratos/`, `design/` | `contratos.json` (17 contratos), `tokens.json` | ver §5.6 |
| `vendor/kokoro` | pesos de voz | ignorado en git |
| `docs/` | 16 documentos + `mockups/` | ver §3.5 |

---

## 2. Diseñado vs. hecho vs. usado

### 2.0 Qué hay de verdad en la base y la bóveda

`remi.db` abierta con `file:…?mode=ro` (`PRAGMA query_only=1`), 45 objetos, 397 312 bytes. Tablas con su recuento, y cuántas veces las lee/escribe el código:

| Tabla | Filas | Lecturas en código | Escrituras en código | Creada en | Nota |
|---|---|---|---|---|---|
| `aldia_borrador` | 0 | 1 | 1 | db.py |  |
| `aldia_visto` | 1 | 1 | 3 | db.py |  |
| `analisis_camino` | 0 | 3 | 2 | db.py |  |
| `apuesta` | 0 | 3 | 2 | db.py |  |
| `conversaciones` | 1 | 5 | 9 | db.py |  |
| `entregas` | 0 | 12 | 2 | db.py |  |
| `escalon` | 0 | 1 | 0 | db.py | SIN ESCRITOR |
| `experiencia_fts` | 0 | 2 | 2 | otro módulo |  |
| `fuente` | 0 | 1 | 1 | db.py |  |
| `gasto_motor` | 0 | 1 | 1 | db.py |  |
| `gasto_proyecto` | 0 | 4 | 2 | db.py |  |
| `hilos` | 0 | 2 | 2 | db.py |  |
| `hito_cerrado` | 0 | 2 | 2 | db.py |  |
| `idea_destacada` | 0 | 2 | 2 | otro módulo |  |
| `ideas` | 0 | 5 | 8 | db.py |  |
| `iniciativa_nudges` | 0 | 3 | 1 | otro módulo |  |
| `iniciativa_silencios` | 0 | 1 | 1 | otro módulo |  |
| `memoria` | 0 | 5 | 2 | db.py |  |
| `meta` | 0 | 1 | 1 | db.py |  |
| `notas_vector` | 0 | 3 | 2 | otro módulo |  |
| `notas_vector_embed` | (vec0) | 1 | 2 | otro módulo |  |
| `nudges` | 0 | 3 | 2 | db.py |  |
| `partida` | 0 | 0 | 0 | db.py | SIN LECTOR |
| `preguntas` | 0 | 3 | 2 | db.py |  |
| `pronostico` | 0 | 4 | 2 | db.py |  |
| `propuesta` | 0 | 4 | 1 | db.py |  |
| `propuestas_correccion` | 0 | 2 | 2 | db.py |  |
| `sesiones` | 0 | 25 | 3 | db.py |  |
| `tareas` | 0 | 19 | 8 | db.py |  |
| `trabajo_claude` | 0 | 7 | 2 | db.py |  |
| `trabajo_commits` | 0 | 3 | 2 | db.py |  |
| `trabajo_estado_en` | 0 | 2 | 2 | db.py |  |
| `trabajo_eventos` | 15 | 6 | 1 | db.py |  |
| `turnos` | 4 | 6 | 1 | db.py |  |
| `ultimo_tema_visto` | 0 | 1 | 1 | db.py |  |
| `vision` | 0 | 1 | 1 | db.py |  |

**Sabemos:**
- Las únicas tablas con datos son `turnos` (4), `conversaciones` (1), `trabajo_eventos` (15), `aldia_visto` (1). Los 4 turnos son una prueba de código del 26-oct (`noche.py` / FTS de experiencia), no uso personal.
- `trabajo_eventos` son eventos `commit` por repo: `proyectos/remi` 7, `projects/malik-gestion` 3, `/Volumes/ORGANIC/boveda` 2, `/Volumes/ORGANIC/Remi` 2, `remi/conocimiento` 1. El hook de git **sí** funciona.
- `conocimiento/` (la bóveda de Remi dentro del repo, repo git anidado `82bc728`) contiene solo `experiencia/` (1 lección + README). No existen `conocimiento/caracter.md`, `conocimiento/oficios/`, `conocimiento/proyectos/`. Comandos: `ls -la ~/proyectos/remi/conocimiento`, `find ~ /Volumes/ORGANIC -maxdepth 6 -name caracter.md -o -name oficios` (sin resultados).
- `notas_vector_embed` no se pudo contar en solo lectura (módulo `vec0` no cargado); `notas_vector` = 0 y `notas_vector_embed_info` = 4.
- Efecto en producción: cada llamada a `pensar` registra «no encuentro …/caracter.md: uso el carácter de respaldo» (`pensar.py:195-203`).

**Hipótesis (no verificada):** la base y la bóveda fueron reiniciadas o restauradas vacías (el repo también se reinició hoy, ver hallazgo 2). La copia del 2–3 oct en iCloud (`~/Library/Mobile Documents/com~apple~CloudDocs/Remi/copias`, restic cifrado) podría tener los datos originales; **no la abrí** (necesita la clave del Llavero y es la copia de producción).

### 2.1 Las seis leyes

| Ley | Dónde vive en el código | Pruebas | Datos reales | Estado |
|---|---|---|---|---|
| 1 · Ceguera temporal | `reloj.py:66 estimar`; `servidor.py:1572` (`ultima_vez_min` en `/hoy`); ventanita `src/tiempo.ts` («hace N min») | `test_reloj` 17 · `tiempo.prueba.ts` | `sesiones` = 0 → no hay «última vez» que devolver | HECHO, SIN USO |
| 2 · Memoria externa | `bandeja.py:63 listar_abiertas`; panel `bandeja/page.tsx`; rituales: `iniciativa.py:164 _regla_ritual` y `noche.py:298` (consolidación). **El ritual de la mañana no existe** (`BITACORA.md:1427-1429`) | `bandeja.spec.ts`; `bandeja.py` sin prueba propia en pytest (la cubren las de servidor) | `ideas` = 0 | PARCIAL |
| 3 · Sin cadena de culpa | `iniciativa.py:177 _regla_encoger`; `notion_avisos.py:16-19` («Ahora no» solo corre 2 h); `nudges.respuesta` nunca se cuenta | `test_iniciativa` 24 · `nudges.prueba.ts` | `nudges` = 0, `iniciativa_nudges` = 0 | HECHO, SIN USO |
| 4 · Presión invertida | Sin «urgente/crítico» visible: `grep -rnE "urgente\|crítico" nucleo apps/*/src` solo da el flag técnico `urgente` de Telegram (`telegram.py:319,377`, `noche.py:285-293`) y comentarios que lo niegan | — | — | CUMPLE (ver `[BAJO]` abajo) |
| 5 · Cuerpo primero | `iniciativa.py:150 _regla_cuerpo` (bloque > 90 min, `:34`); ventanita `componentes/Nudge.tsx` | `test_iniciativa` | `iniciativa_nudges` = 0 | HECHO, SIN USO |
| 6 · Enfriamiento | `bandeja.py:17 HORAS_DE_ENFRIAMIENTO = 48`, `:32`; `db.py:59 enfria_hasta` | `bandeja.spec.ts` | `ideas` = 0 | HECHO, SIN USO |

Hallazgos de leyes y diseño, todos `[BAJO]`:
- `apps/ventanita/src/App.css:20` usa `box-shadow: inset 0 1px 0 var(--borde-especular)`: una sombra, y el DS solo permite los tres `glow-*` (`CLAUDE.md:31`).
- `apps/panel/src/app/layout.tsx:18` tiene `themeColor: "#151112"`: un hex a mano contra `CLAUDE.md:7`.
- `apps/ventanita/src/gestos.ts:253` tiene voseo en un comentario («lo cortás vos: podés callarte») y `nucleo/probar_bloqueos.py:39` en un prompt de prueba (`Sos un asistente. Hacé…`). Nada de esto llega al usuario.
- `nucleo/pensar.py:1` dice «opt-in por mensaje (think=true) … Por defecto Remi no gasta nada», lo contrario de la Biblia v4 («piensa siempre», `BIBLIA.md:321`).
- Las «rachas» de la ventanita (`App.tsx:280`, `gestos.ts`) son rachas de **clics**, no de fallos: no violan la Ley 3.

### 2.2 Las pantallas

| Pantalla (Biblia) | Hecha en | Pruebas | Datos reales | Estado |
|---|---|---|---|---|
| Ventanita: reposo→escuchando→respuesta, 1/2/3 clics, ⌃⌥R | `App.tsx`, `gestos.ts`, `voz.rs`; `/mensaje` → `_atender` en `servidor.py:507` | vitest 122 (gestos 467 líneas de prueba) | `sesiones` 0, `conversaciones` 1 (de prueba). «5 días seguidos» (`BIBLIA.md:579`) no se puede comprobar | PARCIAL (la app corre: proceso `application.com.remi.ventanita`) |
| Panel · Hoy (+ «Al día», `BIBLIA.md:278-294`) | `page.tsx`; `aldia.py` (`calcular_estamos_en :179`, `calcular_lo_ultimo :193`, `calcular_sigue :228`) | `hoy.spec.ts`; `test_aldia` 11 | `aldia_visto` 1; `trabajo_eventos` 15 | PARCIAL: «lo último» puede salir de commits; «la terminal está trabajando» no (sin hook de Claude Code) |
| Panel · Bandeja | `bandeja/page.tsx`, `bandeja.py` | `bandeja.spec.ts` | `ideas` 0 | HECHO, SIN USO |
| Panel · Proyectos (camino, no árbol) | `proyectos/page.tsx`, `caminos.py`, `libros.py`; `components/ProjectPath.tsx` | `proyectos.spec.ts`; `test_caminos` 34 | `conocimiento/proyectos/` no existe → 0 libros | HECHO, SIN USO |
| Panel · Ficha de cliente | `proyectos/[tema]/page.tsx`, `ficha.py:59,82`, `gastos.py` | `proyecto.spec.ts`; `test_ficha` 35 | `gasto_proyecto` 0, `entregas` 0 | HECHO, SIN USO |
| Panel · Metas | `metas/page.tsx`, `plata.py:287` | `metas.spec.ts`; `test_plata` 74 | `meta` 0, `entregas` 0 | HECHO, SIN USO |
| Panel · Semana | `semana/page.tsx`, `semana.py:86` | `semana.spec.ts`; `test_semana` 6 | todas vacías | HECHO, SIN USO. Falta la «notificación del domingo» (`PLAN-FINAL.md:292`): no encontré código |
| Panel · Rumbo (visión, meta, cuenta, apuestas) | `rumbo/page.tsx`, `rumbo.py:76 parsear_vision`, `:108 calcular_partida_medida` | `rumbo*.spec.ts`; `test_rumbo` 18 | `vision`, `meta`, `escalon`, `partida`, `propuesta`, `apuesta` = 0 | HECHO, SIN USO |
| Rumbo · análisis de un camino | `rumbo/caminos/[id]/page.tsx`, `analisis_camino.py:124` | `rumbo-camino.spec.ts`; `test_analisis_camino` 5 | `analisis_camino` 0 | PARCIAL: `POST /rumbo/caminos` crea una fila «investigando» que nadie termina (no hay investigador; `BITACORA.md:463-480`) |
| Rumbo · punto de partida | `rumbo/partida/page.tsx` | `partida.spec.ts` | `partida` = 0, **sin lector** en SQL | HECHO, SIN USO |
| Panel · Ajustes → Conexiones | `ajustes/page.tsx`, `Conexiones.tsx`, `conexiones.py` | `ajustes.spec.ts`; `test_conexiones` 67 | `.env` con 2 claves | USADO (Telegram se configuró desde ahí) |
| Panel · Coding | `coding/page.tsx`, `coding.py` | `test_coding` 15; **sin e2e** | `turnos` 4 (pruebas) | PARCIAL. **No está en la Biblia ni en `CLAUDE.md:14`**, que lista las vistas |
| Ventanita · avisos de Notion | `useAvisoNotion.ts`, `AvisoNotion.tsx`, `notion_avisos.py` | `avisoNotion.prueba.ts`; `test_notion_avisos` 6 | sin `NOTION_TOKEN` | HECHO, DORMIDO. Contradice la Biblia (§3.5) |

### 2.3 Funciones, partes y promesas de la Biblia

| Parte / función | Dónde está (archivo:línea) | Pruebas | Datos reales | Estado |
|---|---|---|---|---|
| Núcleo local + SQLite fuente de verdad | `db.py:13-20`, `servidor.py` | 1 072 pytest | DB viva | USADO |
| Clasificador sin IA (idea / hoy / hecha, cobro, gasto) | `clasificar.py` (79 pruebas), `cobros.py:31`, `gastos.py:79` | sí | — | HECHO, SIN USO |
| Reglas del líder / nudges | `iniciativa.py:200 evaluar`, `avisos.py:310 evaluar` | 24 + 40 | 0 | HECHO, SIN USO |
| Medidor de tiempo de sesión | `db.py:748 cerrar_sesion`; `sanear.py` | sí | `sesiones` 0 | HECHO, SIN USO |
| Whisper local | `voz.rs` (`whisper-cli`); servidor residente `com.remi.whisper` | — | :4401 **no escucha** (`lsof`) | PARCIAL (cae a `whisper-cli`) |
| Kokoro local, 4 voces | `tts.py:108 sintetizar`, `/tts` viva | `test_tts` 13 | — | USADO (la ventanita llama `/tts`) |
| Memoria: mente + turnos + vectores | `db.py` memoria; `vectores.py:140,176`; `memoria_mcp.py` | `test_memoria`, `test_vectores` | `memoria` 0; `notas_vector` 0 | HECHO, SIN USO |
| Cerebro: niveles 0–3, precarga | `pensar.py:416 instrucciones_con_indice`, `precarga.py` | 42 | — | HECHO, SIN USO (el índice está vacío) |
| Accesibilidad macOS | `accesibilidad.py:44` → `avisos.py` | 24 | permiso no dado (`BITACORA.md:316`) | HECHO, ESPERA PERMISO |
| Telegram (avisos y charla corta) | `telegram.py:212 escuchar`, `:369 avisar`, `:284 en_silencio` | 54 | token puesto (`.env`) y bitácora de la bóveda dice «aviso de prueba enviado ok» | USADO |
| Notion, solo de ida | `notion_sync.py:388`, `notion.py` | 11 + 21 | sin `NOTION_TOKEN`; sin servicio `com.remi.notion` | HECHO, DORMIDO |
| Google Calendar | `calendario.py:105,114` | 10 | sin OAuth (`BITACORA.md:312`) | HECHO, ESPERA PERMISO; **sin cliente** (§1.3) |
| Motores y chips (Claude, Groq, OpenRouter, Venice, Ollama) | `pensar.py:557-700`, `nucleo/config/motores.json` | 261 | solo Claude/Max tiene credencial | PARCIAL (§hallazgo 6) |
| Tope de gasto | `gasto.py:149 excede_tope`, `pensar.py:1195` | 103 | `gasto_motor` 0 (no hay motor pagado con llave) | HECHO, SIN USO |
| Indestructible: GitHub privado | — | — | `git remote -v` vacío | NO EXISTE |
| Indestructible: copia nocturna cifrada | `scripts/copia.sh`, `config/copia.json` | `test_copia*` | iCloud `copias/data` modificada 2-oct; sin `copia.log` | NO CORRE |
| Indestructible: se cura solo (KeepAlive) | `com.remi.nucleo` (pid 1521) | probado en bitácora | `launchctl list` | USADO |
| Indestructible: vigía, túnel, panel afuera | `vigia.sh`, `tunel.sh` | — | no cargados | NO CORRE |
| `doctor.sh` | `scripts/doctor.sh:3` (**11** chequeos) | — | no lo corrí (llama a :4400) | HECHO; docs dicen «10» |
| Reporte de la noche / consolidación | `noche.py:283,298` | 76 | sin `noche.log` | NO VERIFICADO que corra |
| Oficios (9) | carga en `pensar.py:303 _cuerpo_oficio`; faltan los archivos | pruebas fallan | `conocimiento/oficios/` no existe | NO EXISTE (el código sí) |
| Banco de pruebas | `scripts/banco.py` (`arrancar \| frases \| parar`) | — | no lo corrí | HECHO |
| Libro de errores / experiencia (T8) | `experiencia.py:578 crear_leccion`, `:475 reindexar`, `:533 buscar` | 59 | 1 lección en `conocimiento/experiencia/`; FTS 0 filas | PARCIAL |
| Adaptarse: Remi propone la regla | `correcciones.py:84 proponer_regla` | 11 | `propuestas_correccion` 0 | HECHO, SIN USO |
| Remi pregunta en el panel, nunca en el chat | `preguntas.py:48 EN_EL_CHAT = False` | 44 | `preguntas` 0 | HECHO, SIN USO |
| Hilos por tema (B7) | `hilos.py:14 rastrear` | **0 pruebas directas** (se prueba por servidor) | `hilos` 0 | HECHO, SIN USO |
| Hitos que se cierran solos | `caminos.py:312`, `trabajo.py:292 _cerrar_hito_por_encargo`, `mensaje_cliente.py` | 34 + 5 | `hito_cerrado` 0 | HECHO, SIN USO (el cierre por encargo exige el hook de Claude Code, ausente) |
| Avisos con sonido (B5): `terminal_termino`, `foco_25`, `desvio` | `avisos.py`; ventanita `useAvisoNotion` solo trae avisos de Notion | 40 | — | PARCIAL: la UI de la ventanita para los 3 avisos propios y el Telegram de B5 siguen BLOQUEADOS (`BITACORA.md:646`) |
| Presupuesto de silencio | `iniciativa.py:32-34`, `avisos.json:4-5`, `notion_avisos.py:53` | — | — | HECHO ×3 (§5.3) |
| Lista de cierre, camino del SOP, archivar | `cierre.py`, `caminos.py`, `db` `archivada` | 26 | — | HECHO, SIN USO |
| Revisión semanal del lunes | `semana.py`, `/semana` | 6 | — | PARCIAL |
| Parte VIII · PR (paquete base, revisión con otro modelo, explicación) | `produccion.py:50,71,97,105` | 8 (solo dobles) | — | SOLO PRUEBAS. BLOQUEADO (`BITACORA.md:275-281`) |
| Rumbo · capa 1 punto de partida | `rumbo.py:108` | `test_rumbo` | `partida` 0 | HECHO, SIN USO |
| Rumbo · capa 2 investiga | `analisis_camino.py:57 Investigador` (Protocol; ninguna clase lo implementa) | dobles | — | NO EXISTE |
| Rumbo · capa 3 el juego | `juego.py:87 generar_jugadas`, `:91 jugadas_a_ideas` | 6 | — | SOLO PRUEBAS; no hay ruta |
| Rumbo · capa 4 calcula (1 000 corridas, Kelly) | `simulacion.py:41 simular`, `:60 kelly_tope` | 6 | — | SOLO PRUEBAS |
| Rumbo · capa 5 se contradice | `estimacion.py:22,49,65` | 15 | — | SOLO PRUEBAS |
| Rumbo · capa 6 aprende | `calibracion.py:63 entrenar_recalibrador`, `:109` rutas | 6 | `pronostico` 0 | PARCIAL (`entrenar_recalibrador` solo en pruebas) |
| Rumbo · cuenta hacia atrás, reloj, apuestas, latido | `rumbo.py`, `reloj.py:66`, `/rumbo/cuenta`, `/rumbo/latido` vivas | 18 + 17 | 0 | HECHO, SIN USO |
| Hoy ordenado por el Rumbo | `orden_rumbo.py` | 5 | — | SOLO PRUEBAS: ningún módulo lo importa, `/hoy` no lo usa |
| Poda mensual | `rumbo.py:605 GET /rumbo/poda` | 0 | — | HECHO, SIN CLIENTE |
| «Listo cuando de uso real» (5 días / 7 mañanas / 1 semana) | — | — | sin datos para medirlo | NO MEDIBLE |

---

## 3. Lo que sobra

### 3.1 Código muerto

Método: `python3 -I muertos.py` (apéndice A) cuenta referencias a cada función/clase de nivel módulo en el resto de `nucleo/`, `scripts/`, `apps/`, `config/` y `prompts/`. Dio **6 sin ninguna referencia** y **128 que solo mencionan las pruebas** (de ellas, la mayoría se usan además dentro de su propio archivo: no son muertas). `vulture` no está instalado; no instalé nada.

**Funciones sin ninguna referencia (muertas de verdad)** `[BAJO]`:
- `db.py:1483 apuesta_por_id`
- `precarga.py:312 _preguntas_pendientes`
- `telegram.py:147 _fecha_corta` y `:151 _monto_corto`
- `trabajo.py:352 que_falta`
- (`entregas.py:238 crear_cobro` salió como muerta pero es el handler de `POST /cobros`: falso positivo.)

**Referenciadas solo desde pruebas y sin uso interno** (`self=0`, candidatas):
- `calendario.py:68` tarea_a_evento — solo la llaman pruebas
- `db.py:1483` apuesta_por_id — ninguna referencia
- `estimacion.py:22` combinar_a_ciegas — solo la llaman pruebas
- `estimacion.py:49` estimar_a_ciegas — solo la llaman pruebas
- `estimacion.py:65` necesita_segunda_ronda — solo la llaman pruebas
- `experiencia.py:289` hay_vueltas — solo la llaman pruebas
- `juego.py:87` generar_jugadas — solo la llaman pruebas
- `juego.py:91` jugadas_a_ideas — solo la llaman pruebas
- `notion.py:205` leer_fecha — solo la llaman pruebas
- `notion.py:211` leer_numero — solo la llaman pruebas
- `pensar.py:858` _turnos — solo la llaman pruebas
- `precarga.py:312` _preguntas_pendientes — ninguna referencia
- `produccion.py:50` generar_paquete_base — solo la llaman pruebas
- `produccion.py:71` puede_entregar — solo la llaman pruebas
- `produccion.py:97` revisar_sesion — solo la llaman pruebas
- `produccion.py:105` nada_grave_pendiente — solo la llaman pruebas
- `produccion.py:112` ListaDeLaVerdad — solo la llaman pruebas
- `reloj.py:84` excede_90_min — solo la llaman pruebas
- `reloj.py:138` piezas_caladas — solo la llaman pruebas
- `simulacion.py:41` simular — solo la llaman pruebas
- `simulacion.py:60` kelly_tope — solo la llaman pruebas
- `telegram.py:147` _fecha_corta — ninguna referencia
- `telegram.py:151` _monto_corto — ninguna referencia
- `trabajo.py:352` que_falta — ninguna referencia

**Módulos enteros que solo llaman las pruebas** `[MEDIO]` (596 líneas + 369 de pruebas): `claves.py` (169), `produccion.py` (136), `juego.py` (99), `estimacion.py` (70), `simulacion.py` (68), `orden_rumbo.py` (54). Comando: `grep -rn "import estimacion\|from estimacion" nucleo --include=*.py | grep -v pruebas` → vacío (ídem los otros cinco). `claves.py` ni siquiera pertenece al Rumbo: lo reemplazó otra ruta y quedó huérfano.

**Rutas sin cliente:** ver §1.3 (5 rutas) y `[BAJO]` `ventanita/src/componentes/Reloj.tsx` (sin importador).
**Exports TS sin uso** `[BAJO]`: `panel/src/config.ts` (`URL_NUCLEO`, `PUERTO_PANEL`, 0 usos), y ~16 tipos exportados de `lib/nucleo.ts` solo usados dentro del archivo.

### 3.2 Tablas

- `partida`: **sin lector ni escritor** en SQL (no hay `FROM/INTO/UPDATE partida` en `nucleo/*.py`) y 0 filas; la pantalla `rumbo/partida` se alimenta de `calcular_partida_medida` en memoria. `[MEDIO]`
- `escalon`: se lee (`db.py`) pero **nadie escribe** (0 INSERT en el código): la escalera no puede poblarse sin escribir a mano en SQL. `[MEDIO]`
- 26 de las 30 tablas de `db.py` tienen 0 filas (ver §2.0): son «vacías con lector», o sea falta de uso, no sobrantes.
- `experiencia_fts*` y `notas_vector*` (virtuales) las crean `experiencia.py` y `vectores.py`, fuera del esquema de `db.py`: **dos lugares definen el esquema**. `[BAJO]`

### 3.3 Configuración sin uso

- `config/copia.json` → `destinos.icloud` aparece como «clave sin referencia» porque el código lee `destino`+`destinos[destino]` dinámicamente: **falso positivo**; sí se usa.
- No hallé claves de `config/*.json` realmente muertas (script: apéndice A, mismo método que arriba).
- **Dos carpetas de config** (`config/` y `nucleo/config/`) sin criterio visible de cuál va dónde. `[BAJO]`

### 3.4 Servicios y scripts (`scripts/instalar.sh`, 556 líneas)

Etiquetas que define: `nucleo` (`:13`), `ventanita` (`:14`), `whisper` (`:154`), `copia` (`:205`), `noche` (`:249`), `notion` (`:294`), `refresco-claude-code` (`:337`), `vigia` (`:380`), `tunel` (`:422`), `panel` (`:467`) = **10**.

Comando: `launchctl list | grep -i remi` → `com.remi.noche`, `com.remi.nucleo` y la app `application.com.remi.ventanita`. `ls ~/Library/LaunchAgents | grep remi` → solo `noche` y `nucleo`.

| Servicio | Aporta | Cargado hoy |
|---|---|---|
| nucleo | el núcleo, KeepAlive | sí (pid 1521) |
| ventanita | abre la app al iniciar sesión | la app corre, pero no hay plist |
| noche | consolidación 4:00 | cargado; **sin `noche.log`** |
| whisper | Whisper residente (:4401) | no |
| copia | copia cifrada a iCloud/R2/B2 | no — `[ALTO]` |
| notion | espejo cada 15 min | no (sin token) |
| refresco-claude-code | relee el changelog los domingos 5:00 | no |
| vigia | avisa por Telegram si Remi cae | no — `[ALTO]` |
| tunel | Cloudflare Tunnel + Access | no |
| panel | `next start` bajo launchd | no: el panel que corre se lanzó a mano |

**Sobran, hoy y por diseño:** `notion` (Notion «solo de ida» y sin token, mientras `notion_avisos.py` lee de Notion), `refresco-claude-code` (semanal; usa `pensar` para releer un changelog; ningún dato lo pide), y `tunel` si no hay plan de exponer el panel. **Faltan** `copia` y `vigia`, que son los dos que la Biblia más defiende (`BIBLIA.md:365-385`).

Scripts de una sola vez: `scripts/archivar_ruido_de_sesiones.py` y `nucleo/limpiar_pruebas.py` (limpieza «día cero»), `nucleo/sanear.py`, `nucleo/probar_bloqueos.py`, `nucleo/sembrar_memoria.py`: sin importador y 0–1 pruebas. `[BAJO]`

### 3.5 Documentos viejos o que contradicen la Biblia

| Documento | Problema | Prueba | Gravedad |
|---|---|---|---|
| `docs/ARQUITECTURA-CEREBRO.md` | «90 min entre dos» (`:16`, `:105`) frente a 45 en la Biblia v4.2 (`BIBLIA.md:577`) y en el código; «Notion en los dos sentidos» (`:153`, `:211`) frente a «solo de ida» (`CLAUDE.md:9`, `BIBLIA.md:29`); «10 piezas» (`:220`) frente a 11 chequeos en `doctor.sh:3`; usa voseo («escribís», `:105`) | líneas citadas | `[MEDIO]` |
| `docs/BIBLIA.md` consigo misma | `:476` «Notion es la vitrina, de ida y vuelta» vs `:29` y `:359` «solo de ida»; `:244` «Whisper large» vs `:335` «large-v3-turbo»; `:381` «10 piezas» (son 11) | líneas citadas | `[MEDIO]` |
| `scripts/instalar.sh:333` | imprime «notion: ida y vuelta cada 15 min» | línea citada | `[BAJO]` |
| `nucleo/notion_avisos.py:11-19` | decide leer de Notion (15-oct) y usa 90 min entre avisos; contradice `CLAUDE.md:9` y la Biblia (45) | líneas citadas | `[MEDIO]` |
| `CLAUDE.md:14` | lista las vistas del panel sin **Coding** (existe, `apps/panel/src/app/coding/page.tsx`) ni Ajustes; `:63` apunta a `docs/vision.md`, que no existe (`ls docs/vision.md`) | comando | `[BAJO]` |
| `docs/README.md` | «Estado» congelado en la Fase 2b/2d («Fase 2b … en curso», `:5-13`); `:3` pide `vision.md` | líneas citadas | `[BAJO]` |
| `docs/ahora.md:8` | «1048 ok, 6 fallos previos ajenos (oficios, Notion, Ollama)»: hoy son 1 064 ok y 6 fallos, y la causa no es Notion/Ollama (§6) | §6 | `[BAJO]` |
| `docs/PLAN-100.md`, `PLAN-CIERRE.md`, `PLAN-REVISION.md`, `REVISION.md`, `ENCARGO-VELOCIDAD.md`, `AUDITORIA-BIBLIA.md` | históricos y cerrados (`PLAN-FINAL.md:7-8`); siguen en `docs/` sin marca de archivados | — | `[BAJO]` |
| `docs/BITACORA.md` (4 616 líneas) | hashes inexistentes en el repo actual; la entrada más nueva es del 6-oct y el trabajo del 26-oct (coding, Telegram limitado) vive solo en `ahora.md` y en la bitácora de la bóveda | `git cat-file -t` | `[MEDIO]` |
| `docs/PLAN-FINAL.md` | sigue como «estado vivo» (`CLAUDE.md:50`) aunque lo que quedó es BLOQUEADO/ESPERA; pide `doctor.sh` «10/10» (`:64`) | líneas citadas | `[BAJO]` |

---

## 4. Lo que falta

### 4.1 BLOQUEADO y ESPERA de la bitácora (los que siguen abiertos)

Comando: `grep -n "BLOQUEADO\|ESPERA" docs/BITACORA.md`.

| Marca | Qué es | Dónde | Sigue abierto hoy |
|---|---|---|---|
| BLOQUEADO | **Investigador y generador reales** (R3.1/R3.2): STORM con búsqueda web en `claude -p` y «Ábreme el juego» | `BITACORA.md:463` | sí: `analisis_camino.py:57` es un Protocol sin implementación; `juego.py` sin ruta |
| BLOQUEADO | **Tres estimadores a ciegas y la crítica** (R4.1/R4.3) | `:418` | sí: `estimacion.py` solo con dobles |
| BLOQUEADO | **Revisión real con otro modelo** (PR.2/PR.3) y el gancho `SessionEnd` | `:275` | sí: `produccion.py` solo con dobles; el hook no está instalado |
| BLOQUEADO | **Ventanita y Telegram para los avisos de B5** | `:646` | parcial (Telegram ya manda avisos de coding, `telegram.py:369`) |
| BLOQUEADO | **«Jugadas que ganan pase lo que pase»** (Parte IX) | `:98` | sí: sin campo ni ruta |
| BLOQUEADO | **Mapa de apps «en el tema»** para afinar `desvio` | `:320` | sí: lo tiene que decir Juan Camilo (`config/apps_trabajo.json` existe, falta la lista) |
| BLOQUEADO | **Correr `desinstalar.sh` + `instalar.sh` de punta a punta** | `:1422` | sí (no lo corrí tampoco) |
| BLOQUEADO | **Ritual de la mañana** no existe | `:1427` | sí |
| ESPERA PERMISO | OAuth de Google Calendar (B10.1); Accesibilidad de macOS (B10.2) | `:312`, `:316` | sí |
| ESPERA D1 | Paneles de Rumbo (tablero 6), Bandeja con jugadas (7), aporte por proyecto (9) | `:227`, `:538` | **parcial**: el panel de Rumbo y el camino se construyeron después (entradas 10-06); la Bandeja con jugadas y el aporte por proyecto: no verifiqué si existen |

### 4.2 Lo que la Biblia pide y no existe

1. **`conocimiento/` poblado:** `caracter.md`, `oficios/` (los 9 de `BIBLIA.md:537-547`), `proyectos/`. El código los espera; los archivos no están (§2.0).
2. **Copia en GitHub privado** (`BIBLIA.md:369`): `git remote -v` vacío.
3. **Hook de sesión de Claude Code** (`scripts/hooks/claude-sesion.py` existe; no está instalado en `~/.claude/settings.json`).
4. **Cloudflare Access delante del panel** y el panel bajo launchd.
5. **Llaves de los respaldos** (Groq, OpenRouter, Venice) y del espejo (Notion).
6. **Notificación de domingo para la revisión semanal** (`PLAN-FINAL.md:292`): no hay código (`grep -rn domingo nucleo/*.py` solo devuelve el mapa de días de `agenda.py:24`).
7. **Investigador real, estimadores a ciegas, crítica, revisor de sesiones, «jugada que gana pase lo que pase»** (todo el Rumbo capa 2/3/5 y la fase PR).
8. **Tabla `avisos`:** el esquema está en `avisos.py:29-30` pero la tabla no existe en `remi.db`: `avisos.py` nunca corrió contra la base real.
9. **Contrato `Turno`** (`BIBLIA.md:462`) y las formas J–S de `PLAN-FINAL.md` en `contratos/contratos.json` (§5.6).
10. **Mejora medida del Hoy:** «Hoy ordenado por el Rumbo» (`PLAN-FINAL.md:339-350`) no está conectado.
11. **Ritual de la mañana** (`BIBLIA.md:53`, «dos revisiones rituales: noche y mañana»).
12. **Verificación de que `noche` corre:** no hay `noche.log`.

### 4.3 Lo que existe pero necesita una acción de Juan Camilo

Rotar el token de Telegram y limpiar el log; instalar el hook de Claude Code; decidir qué servicios de `instalar.sh` se cargan; dar el permiso de Accesibilidad / OAuth de Calendar si siguen en el plan; contestar el mapa de apps.

---

## 5. Arquitectura

### 5.1 Archivos de más de 500 líneas (sin generados, `node_modules`, `.next`, `target`)

| Archivo | Líneas | Por qué creció (dato) |
|---|---|---|
| `nucleo/servidor.py` | 2477 | 54 rutas propias (716 líneas) + 358 líneas de clases + 845 de funciones auxiliares; 14 routers se incluyeron aparte (`app.include_router`, p. ej. `servidor.py:163`) pero las rutas de hoy, tareas, libros, conversaciones, plata, rumbo-vision y config siguieron aquí. `_atender` (`:507`) tiene **146** líneas y despacha todos los tipos de mensaje. 60 `BaseModel` de respuesta viven aquí. |
| `nucleo/pensar.py` | 1968 | 86 funciones: carácter, índice, precarga, historial/resumen, hilos en segundo plano, y cinco proveedores. `pensar_en_frases` (`:1072`) tiene **121** líneas y mezcla armado de contexto, reglas de forzar Claude, streaming, respaldo y escritura de turnos. `_deltas_claude` (`:1827`) 91. |
| `apps/ventanita/src/App.tsx` | 1873 | Un componente `App` de ~1 680 líneas con 29 `useState`, 27 `useEffect`, 35 `useRef`, 30 `useCallback`. |
| `nucleo/db.py` | 1597 | 30 tablas + ~60 funciones de acceso; toda la persistencia pasa por un solo archivo (30 módulos lo importan). |
| `apps/ventanita/src-tauri/src/voz.rs` | 1541 | 40 funciones: grabación, silencio, Whisper, cola. |
| `nucleo/pruebas/test_pensar.py` | 1019 | prueba de `pensar.py`. |
| `nucleo/trabajo.py` | 711 | eventos de git y de Claude Code, hitos por encargo, turnos. |
| `nucleo/experiencia.py` | 628 | lecciones: crear, FTS, vectores, router. |
| `nucleo/preguntas.py` | 618 | detección de huecos, creación y respuesta; tiene una rama `EN_EL_CHAT` apagada (`:48,85,127,156`). |
| `nucleo/rumbo.py` | 612 | visión, meta, escalera, partida, cuenta, apuestas, latido, poda y propuestas en un archivo. |
| `apps/ventanita/src/voz.ts` | 587 | |
| `apps/panel/src/app/page.tsx` | 582 | Hoy. |
| `apps/panel/src/app/proyectos/[tema]/page.tsx` | 569 | ficha de cliente entera. |
| `nucleo/coding.py` | 504 | el más reciente (26-oct). |

Patrón: el crecimiento viene de que **cada fase del plan agregó su rama al archivo existente** en vez de un módulo (`servidor.py`, `pensar.py`, `db.py`, `rumbo.py`), no de una complejidad esencial.

### 5.2 Ciclos de imports

**Sabemos:** hay 2 ciclos a nivel de módulo (§1.2) y 4 pares mutuos con import dentro de función. Aun así **los 62 módulos se importan solos en un intérprete limpio** (`for m in …; python -c "import $m"` con `REMI_DB_PATH` temporal → 0 fallos), o sea: no hay ciclo que rompa el arranque hoy. El riesgo es de **orden de import**, no de error actual. `[MEDIO]` por `pensar → cierre/coding` (un motor que conoce flujos) y `plata → ficha → aldia → entregas → plata`.

### 5.3 Lógica duplicada

Método: AST por nombre de función en ≥2 módulos y por cuerpo idéntico (≥5 líneas).

- **Presupuesto de silencio ×3** `[MEDIO]`: `avisos.py:152 _presupuesto_ok`, `iniciativa.py:90 _presupuesto_ok`, `notion_avisos.py:215 _presupuesto_ok`, con `_en_noche` (×2), `_hoy` (×2), `_preparar` (×3) y `responder` (×4) también repetidos, y **dos valores**: 45 min (`iniciativa.py:33`, `avisos.json:5`) y 90 min (`notion_avisos.py:53`). La Ley 3/Parte VII dice 45.
- **Lectura de `.env` ×3** `[MEDIO]`: `_leer_env` en `notion.py:29`, `pensar.py:533`, `telegram.py:79`; y `_ajuste` ×3 (`notion.py:46`, `pensar.py:552`, `telegram.py:95`). Tres implementaciones de lo mismo (leer `nucleo/.env`); un cambio de formato se toca en tres sitios.
- **Idéntico:** `_fila_a_idea` en `bandeja.py:41` y `db.py:609` (11 líneas); `_cuerpo`/`_indice`/`_fin` en `caminos.py:246-260` y `estado_libro.py:224-238` (5 líneas cada una, y `claves.py:85`); `ver_plata` (`plata.py:315`) y `ver_semana` (`semana.py:99`).
- **Utilidades repetidas:** `_recortar` ×5 (`coding.py:118`, `episodios.py:97`, `iniciativa.py:80`, `limpiar_pruebas.py:133`, `refresco_claude_code.py:58`); `_lunes` ×3 y `_primero_del_mes` ×2 (`plata.py`, `rumbo.py`, `trabajo.py`); `_config` ×4 (`estimacion`, `juego`, `plata`, `rumbo`).
- **Dos carpetas de config** y dos lugares con esquema SQL (§3.2).
- **Pydantic a mano vs. generado:** ver §5.6.

### 5.4 «Sin IA donde hay reglas»

**Sabemos (dónde se llama a un modelo):** `grep -nE "pensar\.(pensar|pensar_con_trastienda|pensar_en_frases)\(" nucleo/*.py` → `claves.py:75` (muerto), `cierre.py:210` (redacta el episodio), `estado_libro.py:165` (redacta el Estado), y en `servidor.py` solo el mensaje de chat (`:497-498`), el encargo (`:950`), la lectura de un cliente (`:976`), abrir un bloque (`:1055`) y el borrador de un mensaje (`:1675`). Todos son «redactar o conversar»; ninguno decide un número ni un estado:
- Montos, fechas, clasificación, cierre de hito, cuenta, simulación y calibración son funciones puras (`clasificar.py`, `cobros.py`, `gastos.py`, `agenda.py`, `rumbo.py:60 _numero`, `rumbo.py:76 parsear_vision`, `simulacion.py`).
- `estado_libro.redactar` (`:130`) filtra el texto del modelo con una validación de «entidad que no aparece literal» (`:121-122`) — la regla de «Estados solo desde evidencia literal».
- El borrador del cliente (`servidor.py:1675`) le pasa el monto al modelo y le pide no inventar cifras.

**Dónde se rompe o se debilita (hipótesis razonadas):**
- `[BAJO]` `parsear_vision` es pura y la voz «Entendí: … Confírmamela» sale de una plantilla (`rumbo.py:218`); `PLAN-FINAL.md:263` prometía «el modelo redacta, una función pura valida». No es una violación: es una promesa a medias.
- `[BAJO]` `/mensaje` con `think=false` responde «Sin pensar no puedo armar el encargo» (`servidor.py:944-947`): la rama sin IA de los encargos no existe; el camino sin IA solo cubre tareas y cobros.

**No encontré** una ruta donde un modelo ponga la cifra final ni decida qué es verdad. Lo anterior puede cambiar el día que se construyan los estimadores a ciegas (`estimacion.py`): el diseño ya prevé que el número lo ponga código (`BIBLIA.md:677`).

### 5.5 Rutas de fallo de `pensar.py`

Comando: AST sobre `nucleo/pensar.py`.

- **44** manejadores `except` (14 de ellos `Exception`: `:238, :351, :410, :445, :466, :471, :483, :492, :500, :509, :847, :865, :947, :968`), **1** `raise` (`LimiteDeClaude`, `:1952`) y **38** `return None`.
- 86 funciones. La API pública es `pensar()` (`:1051`) → `pensar_en_frases()` (`:1072`), y el contrato es: *devuelve `Pensado | None`; `None` significa «sigue sin IA»* (docstring `:1062-1064`).
- Los caminos de fallo se agrupan en cinco familias:
  1. **Motor no disponible** (CLI `claude` ausente `:1799`/`:1859`, Ollama caído `:632`, respuesta sin contenido utilizable `:1432-1434`) → `None`.
  2. **Red / HTTP** por proveedor: `HTTPStatusError`/`HTTPError` en `:1479-1482` (Venice), `:1548-1551` (charla), `:1646`, `:1670`, `:1688-1691` → `None`.
  3. **Formato**: `json.JSONDecodeError` (`:1375, :1583, :1818, :1883`), `KeyError/IndexError/TypeError` (`:1431`) → `None`.
  4. **Tiempo**: `subprocess.TimeoutExpired` (`:1802`) → `None`.
  5. **Límite de Max** (`LimiteDeClaude`, `:97, :1160, :1952`) → respaldo de charla por OpenRouter/Groq (`:1639`), salvo en tareas de código, que paran (`:1161`, `_respaldo_de_coding_permitido :1047`).
- A lo anterior se suma el **fallo en streaming**: si el motor falla después de haber soltado alguna frase no se cambia de motor (`:1084-1093`), y el que llama recibe `None` con la mitad ya dicha.
- **Lectura:** cada familia devuelve el mismo `None` (`_respaldo_de_charla :1639-1660` solo imprime a stderr y devuelve `None`), así que **quien llama no distingue** «sin llave» de «sin red» de «timeout». Solo `stderr` lo cuenta (`print(…, file=sys.stderr)`), de modo que el panel y la ventanita no pueden decirle al usuario por qué Remi se quedó sin IA. `[MEDIO]`
- 14 `except Exception` anchos (`pensar.py`) son el 34 % de los 41 de todo el núcleo (`servidor` 5, `telegram` 3, `cierre` 3).

### 5.6 Contratos

- `contratos/contratos.json` tiene 17 contratos y `nucleo/modelos.py` 16 clases (`Nudge`, `Memoria`, `Pregunta`… más los de Rumbo). **Faltan** `Turno` (`BIBLIA.md:462`) y las formas J–S del plan: `AlDia`, `Hito`, `Aviso`, `Gasto`, `Cuenta`, `Reloj` no están en el JSON.
- Hay **113** `class …(BaseModel)` a mano fuera de `modelos.py`: `servidor.py` 60, `rumbo.py` 15, `plata.py` 9, `semana.py` 4, `coding.py` 4, `calibracion.py` 4, `experiencia.py` 3, `entregas.py` 3, `analisis_camino.py` 3, `reloj.py` 2, `notion_avisos.py` 2, `conexiones.py` 2, `telegram.py` 1, `calendario.py` 1. Comando: `grep -n "^class .*(BaseModel)" nucleo/*.py | grep -v modelos.py | wc -l` → 113. `[MEDIO]`
- El lado TypeScript sí se genera (`apps/*/scripts/generar-contratos.mjs`, `contratos.ts` con cabecera «Generado desde…»); pero `panel/src/lib/nucleo.ts` redefine a mano los tipos de respuesta del núcleo.

---

## 6. Salud

Entorno: `REMI_DB_PATH` → carpeta temporal, `REMI_TELEGRAM=0`, `REMI_SEMBRAR_CONOCIMIENTO=0`, `REMI_NUCLEO_URL=http://127.0.0.1:1`; `uv run --offline`; la guardia de `nucleo/pruebas/conftest.py:55-70` corta Telegram, Notion y :4400.

| Suite | Comando | Resultado exacto |
|---|---|---|
| pytest | `cd nucleo && uv run --offline pytest -q -p no:cacheprovider` | **6 failed, 1064 passed, 2 skipped in 98.10 s** (1 072 pruebas) |
| mypy | `cd nucleo && uv run --offline mypy .` | **Success: no issues found in 193 source files** (2.27 s) |
| vitest (ventanita) | `cd apps/ventanita && npm test` | **18 archivos, 122 pruebas, todas verdes** (346 ms) |
| tsc ventanita | `npx tsc --noEmit --incremental false` | exit 0 |
| tsc panel | `npx tsc --noEmit --incremental false` | exit 0 |
| Playwright (panel) | — | **no corrido** (arranca servidores; fuera del alcance) |
| `doctor.sh` | — | **no corrido** (llama a :4400) |

Los 2 `skipped`: `test_escala_experiencia.py:22` y `test_vectores.py:24` (`pytestmark = skipif(…)`).

### Los 6 fallos y su causa

| Prueba | Fallo | Causa (verificada) |
|---|---|---|
| `test_cliente.py::test_sistema_cliente_carga_los_oficios_de_verdad` (`:55`) | `assert "Remi NUNCA envía nada" in texto` | El texto del oficio «Clientes» ya no está: la prueba lee el contenido **real** de `conocimiento/` (gitignored), que está vacío |
| `test_puerta_prompts.py::test_sistema_encargo_carga_los_oficios_de_verdad` (`:39`) | `"Un objetivo por prompt" not in texto` | ídem (oficio «prompting» ausente) |
| `test_registros.py::test_el_registro_de_trabajo_lleva_…` (`:47`) | `## Oficio: prompting` ausente | ídem |
| `test_sistema_encargo_reglas.py::test_suma_stack_y_vibe_coding` (`:23`) | `## Oficio: stack` ausente | ídem |
| `test_notion_sync.py::test_el_estado_de_notion_no_ensucia_la_boveda` (`:368`) | `FileNotFoundError: …/conocimiento/.gitignore` | La prueba copia el `.gitignore` real de la bóveda; no existe |
| `test_vectores.py::test_asociacion_trae_shopify_y_mantenimiento` (`:37`) | `asociados_cliente = ['"La noche no reindexaba el FTS de experiencia"']` | Usa la semilla real de la bóveda; solo hay 1 lección y no «Shopify» |

**Sabemos:** los 6 fallos tienen una sola raíz: **las pruebas no son herméticas** (leen la bóveda personal y gitignored) y esa bóveda está vacía (§2.0). `docs/ahora.md:17-19` dice «(oficios, Notion, Ollama)»; Notion y Ollama no intervienen: `test_notion_sync` falla por el `.gitignore` de la bóveda, no por la API.
**Efecto:** hoy un fallo real y uno de datos se ven igual. `[MEDIO]`.

### Verificación de integridad de la base

`remi.db` cambió de hash y de mtime durante mi trabajo (`mtime` 10:04 → 11:19). **No fui yo:** abrí la base solo con `mode=ro`, las pruebas usaron `REMI_DB_PATH` temporal, y la fila nueva es un evento `commit` de las 16:19 UTC producido por el hook de git cuando la sesión «Auditoría B» hizo su commit (`66b19bc`, 11:18:58). Para mi propio commit uso `REMI_NUCLEO_URL=http://127.0.0.1:1` y así el hook no llega al núcleo real.

---

## Tabla final: Mantener / Simplificar / Quitar

Criterio: **Mantener** = hace su trabajo y se usa o se usará sin cambios grandes. **Simplificar** = sirve, pero su forma (tamaño, duplicación, mezcla de responsabilidades) cuesta. **Quitar** = nadie lo llama o fue de una sola vez; recomendación, **no ejecuté ninguna** (si algo se quita, que sea en un commit aparte y con las pruebas que lo cubren).

### `nucleo/`

| Módulo | Decisión | Razón |
|---|---|---|
| `servidor.py` | **Simplificar** | 2477 líneas; mover los 60 modelos y partir las rutas por dominio como ya se hizo con `entregas`, `rumbo`, `plata` |
| `pensar.py` | **Simplificar** | partir motores / conversación / contexto; que el fallo devuelva una causa, no solo `None` (§5.5) |
| `db.py` | **Simplificar** | un solo lugar para el esquema (incluir FTS y vectores) y partir por dominio |
| `modelos.py`, `generar_modelos.py` | **Mantener** | generados; el problema son los 113 modelos a mano, no estos |
| `trabajo.py` | **Mantener** | recibe los eventos que sí llegan (git) |
| `experiencia.py`, `episodios.py`, `cierre.py`, `estado_libro.py`, `boveda_git.py` | **Mantener** | núcleo de la memoria con evidencia |
| `libros.py`, `caminos.py`, `temas.py`, `clasificar.py`, `concreto.py`, `voseo.py`, `agenda.py`, `cobros.py`, `gastos.py`, `mensaje_cliente.py`, `hilos.py` | **Mantener** | reglas puras, bien probadas (hilos sin prueba directa: añadirla) |
| `bandeja.py` | **Mantener** | Ley 6; quitar `_fila_a_idea` duplicado |
| `iniciativa.py`, `avisos.py` | **Simplificar** | unificar el presupuesto de silencio (hoy ×3) |
| `notion_avisos.py` | **Simplificar** | fusionar su presupuesto con `avisos.py`; decidir si Notion se lee (contradice `CLAUDE.md:9`) |
| `notion.py`, `notion_sync.py` | **Mantener (dormido)** | sin token; no costarán nada hasta que se pongan |
| `telegram.py`, `conexiones.py`, `gasto.py` | **Mantener** | en uso; rotar el token y evitar que el cliente HTTP lo imprima |
| `aldia.py`, `ficha.py`, `plata.py`, `semana.py`, `entregas.py` | **Mantener** | pantallas del panel; romper el ciclo `aldia↔entregas↔ficha↔plata` |
| `precarga.py`, `vectores.py`, `sembrar_conocimiento.py`, `memoria_mcp.py` | **Mantener** | el cerebro; dependen de que `conocimiento/` exista |
| `tts.py`, `accesibilidad.py` | **Mantener** | usados / esperan permiso |
| `preguntas.py` | **Simplificar** | quitar la rama `EN_EL_CHAT` apagada (`:48,85,127,156`) |
| `correcciones.py`, `noche.py`, `refresco_claude_code.py` | **Mantener** | `noche` por verificar; `refresco` dormido |
| `rumbo.py` | **Simplificar** | 612 líneas: sacar apuestas / cuenta / poda a archivos propios |
| `reloj.py`, `calibracion.py` | **Mantener** | usados por el panel (rutas vivas) |
| `coding.py` | **Mantener** | nuevo; falta su prueba e2e |
| `analisis_camino.py` | **Simplificar** | no crear filas «investigando» hasta que haya investigador |
| `calendario.py` | **Quitar (por ahora)** | sin cliente y sin OAuth; recuperable cuando haya permiso |
| `claves.py` | **Quitar** | 169 líneas solo con pruebas |
| `produccion.py`, `juego.py`, `estimacion.py`, `simulacion.py`, `orden_rumbo.py` | **Quitar o congelar** | 427 líneas sin llamador; si se quieren, conectarlos a una ruta primero |
| `limpiar_pruebas.py`, `sanear.py`, `probar_bloqueos.py`, `sembrar_memoria.py` | **Quitar** | scripts de una sola vez |

### Apps, scripts y docs

| Pieza | Decisión | Razón |
|---|---|---|
| `ventanita/src/App.tsx` | **Simplificar** | un componente de 1 680 líneas, 29 `useState` y 35 `useRef`: extraer hooks |
| `ventanita/src-tauri/src/voz.rs` | **Simplificar** | 1 541 líneas, 40 funciones |
| `ventanita/src/componentes/Reloj.tsx` | **Quitar** | sin importador |
| resto de `ventanita/src/**` | **Mantener** | pruebas verdes |
| `panel/src/app/page.tsx`, `proyectos/[tema]/page.tsx` | **Simplificar** | 582 y 569 líneas |
| resto de `panel/src/**` | **Mantener** | `config.ts` sin uso: quitar o usarlo |
| `panel/src/app/coding/page.tsx` | **Mantener** | añadir `coding.spec.ts`; reflejarla en `CLAUDE.md` |
| `scripts/instalar.sh` | **Simplificar** | 556 líneas, 10 servicios; cargar solo los que se usan (`nucleo`, `noche`, `copia`, `vigia`) |
| `scripts/copia.sh`, `vigia.sh`, `restaurar.sh`, `doctor.sh` | **Mantener** | lo que la Biblia más defiende; hoy sin correr |
| `scripts/tunel.sh`, servicio `notion`, `refresco-claude-code` | **Quitar (de la instalación)** | sin uso hoy |
| `config/` + `nucleo/config/` | **Simplificar** | una sola carpeta |
| `docs/` históricos (`PLAN-100`, `PLAN-CIERRE`, `PLAN-REVISION`, `REVISION`, `ENCARGO-VELOCIDAD`, `AUDITORIA-BIBLIA`) | **Quitar de `docs/`** (mover a `docs/archivo/`) | cerrados |
| `docs/ARQUITECTURA-CEREBRO.md`, `docs/README.md`, `BIBLIA.md` §contradicciones | **Simplificar** | alinear con 45 min, «solo de ida», 11 chequeos |

---

## Apéndice A — Scripts usados (se corrieron desde el scratchpad, no están en el repo)


<details><summary><code>grafo.py</code></summary>

```python
import ast, sys, json, pathlib, collections
R = pathlib.Path.home()/"proyectos/remi/nucleo"
mods = {p.stem: p for p in R.glob("*.py")}
info = {}
for name, p in sorted(mods.items()):
    src = p.read_text()
    tree = ast.parse(src)
    top, lazy = set(), set()
    defs = []
    for node in ast.walk(tree):
        pass
    def visit(node, depth_fn):
        for ch in ast.iter_child_nodes(node):
            fn = depth_fn or isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef))
            if isinstance(ch, ast.Import):
                for a in ch.names:
                    m = a.name.split(".")[0]
                    if m in mods and m != name: (lazy if depth_fn else top).add(m)
            elif isinstance(ch, ast.ImportFrom) and ch.module and ch.level == 0:
                m = ch.module.split(".")[0]
                if m in mods and m != name: (lazy if depth_fn else top).add(m)
            visit(ch, fn)
    visit(tree, False)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.append(n.name)
    info[name] = dict(lines=len(src.splitlines()), top=sorted(top), lazy=sorted(lazy - top), defs=defs)
rev = collections.defaultdict(set)
for m, d in info.items():
    for t in d["top"] + d["lazy"]: rev[t].add(m)
# SCC (all edges, and top-only)
def scc(edges):
    idx, low, st, on, out, c = {}, {}, [], set(), [], [0]
    sys.setrecursionlimit(10000)
    def sc(v):
        idx[v] = low[v] = c[0]; c[0]+=1; st.append(v); on.add(v)
        for w in edges.get(v, []):
            if w not in idx: sc(w); low[v] = min(low[v], low[w])
            elif w in on: low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop(); on.discard(w); comp.append(w)
                if w == v: break
            if len(comp) > 1: out.append(sorted(comp))
    for v in edges:
        if v not in idx: sc(v)
    return out
all_e = {m: d["top"]+d["lazy"] for m,d in info.items()}
top_e = {m: d["top"] for m,d in info.items()}
print("SCC_TOP", json.dumps(scc(top_e)))
print("SCC_ALL", json.dumps(scc(all_e)))
# direct 2-cycles
two = sorted({tuple(sorted((a,b))) for a,ds in all_e.items() for b in ds if a in all_e.get(b,[])})
print("PARES_MUTUOS", two)
print("%-24s %5s  %-3s %-3s  %s" % ("modulo","lineas","out","in","llama(top|lazy)  <- llamado por"))
for m,d in sorted(info.items(), key=lambda kv:-kv[1]["lines"]):
    print("%-24s %5d  %-3d %-3d  top=%s lazy=%s <- %s" % (m,d["lines"],len(d["top"])+len(d["lazy"]),len(rev[m]),",".join(d["top"]),",".join(d["lazy"]),",".join(sorted(rev[m]))))
json.dump({m:{**d,"rev":sorted(rev[m])} for m,d in info.items()}, open("grafo.json","w"), indent=1)
# dot
with open("grafo.dot","w") as f:
    f.write("digraph nucleo {\n rankdir=LR;\n")
    for m,d in info.items():
        for t in d["top"]: f.write(f' "{m}" -> "{t}";\n')
        for t in d["lazy"]: f.write(f' "{m}" -> "{t}" [style=dashed];\n')
    f.write("}\n")
```
</details>

<details><summary><code>muertos.py</code></summary>

```python
import ast, pathlib, re, collections
R = pathlib.Path.home()/"proyectos/remi"
N = R/"nucleo"
prod = {p: p.read_text() for p in N.glob("*.py")}
tests = {p: p.read_text() for p in (N/"pruebas").glob("*.py")}
other = {}
for d in ["scripts", "apps/panel/src", "apps/ventanita/src", "apps/panel/tests", "config", "nucleo/prompts"]:
    for p in (R/d).rglob("*"):
        if p.is_file() and p.suffix in (".py",".sh",".ts",".tsx",".json",".md",".plist",".mjs"):
            try: other[p] = p.read_text()
            except Exception: pass
def count(name, texts, exclude=None):
    pat = re.compile(r"(?<![A-Za-z0-9_])"+re.escape(name)+r"(?![A-Za-z0-9_])")
    n = 0
    for p,t in texts.items():
        if p == exclude: continue
        n += len(pat.findall(t))
    return n
rows = []
for p, src in sorted(prod.items()):
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nm = node.name
            deco = [ast.unparse(d) for d in getattr(node,"decorator_list",[])]
            if any(d.startswith(("app.","router.")) for d in deco): continue  # rutas aparte
            in_self = len(re.findall(r"(?<![A-Za-z0-9_])"+re.escape(nm)+r"(?![A-Za-z0-9_])", src)) - 1
            in_prod = count(nm, prod, exclude=p)
            in_test = count(nm, tests)
            in_other = count(nm, other)
            rows.append((p.name, node.lineno, nm, in_self, in_prod, in_test, in_other))
print("# funciones/clases sin NINGUNA referencia en produccion (otros modulos), scripts ni apps")
for r in rows:
    f,l,nm,s,pr,t,o = r
    if pr==0 and o==0 and not nm.startswith("__") and nm != "main":
        tag = "SOLO-PRUEBAS" if t>0 else ("SOLO-INTERNO" if s>0 else "NADIE")
        print(f"{tag:13s} {f}:{l} {nm} (self={s}, tests={t})")
```
</details>

<details><summary><code>rutas.py</code></summary>

```python
import ast, pathlib, re, json
R = pathlib.Path.home()/"proyectos/remi"; N = R/"nucleo"
routes = []
prefixes = {}
for p in N.glob("*.py"):
    src = p.read_text(); tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func).endswith("APIRouter"):
            pre = ""
            for kw in node.value.keywords:
                if kw.arg == "prefix": pre = ast.literal_eval(kw.value)
            prefixes[(p.stem, node.targets[0].id)] = pre
for p in N.glob("*.py"):
    tree = ast.parse(p.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ("get","post","put","patch","delete","websocket") and isinstance(d.func.value, ast.Name):
                    obj = d.func.value.id
                    path = ast.literal_eval(d.args[0]) if d.args else ""
                    pre = prefixes.get((p.stem,obj), "") if obj != "app" else ""
                    routes.append((d.func.attr.upper(), pre+path, f"{p.name}:{node.lineno}", node.name))
# include_router prefixes in servidor
inc = [ast.unparse(n) for n in ast.walk(ast.parse((N/"servidor.py").read_text())) if isinstance(n, ast.Call) and ast.unparse(n.func).endswith("include_router")]
print("INCLUDE", inc)
clients = {}
for d in ["apps/panel/src","apps/ventanita/src","apps/panel/tests","scripts","nucleo/pruebas","nucleo","config","docs/INSTALAR.md","docs/GUIA-HOY.md"]:
    base = R/d
    files = [base] if base.is_file() else [x for x in base.rglob("*") if x.is_file() and x.suffix in (".ts",".tsx",".mjs",".sh",".py",".json",".md") and "node_modules" not in x.parts and ".next" not in x.parts and "__pycache__" not in x.parts]
    for f in files:
        try: clients[f] = f.read_text()
        except: pass
def rx(path):
    segs = [s for s in path.split("/") if s]
    parts = []
    for s in segs:
        parts.append(r"[^/\"'`\s?]+" if s.startswith("{") else re.escape(s))
    return re.compile(r"/"+"/".join(parts)+r"(?![A-Za-z0-9_-])")
out = []
for m, path, loc, fn in sorted(routes, key=lambda r: r[1]):
    r = rx(path) if path else None
    hits = {"panel":0,"ventanita":0,"scripts":0,"nucleo_interno":0,"pruebas":0,"e2e":0}
    for f,t in clients.items():
        if r is None: continue
        s = str(f)
        if str(N/"servidor.py") == s and False: continue
        n = len(r.findall(t))
        if not n: continue
        if "apps/panel/src" in s: hits["panel"] += n
        elif "apps/ventanita" in s: hits["ventanita"] += n
        elif "apps/panel/tests" in s: hits["e2e"] += n
        elif "/scripts/" in s: hits["scripts"] += n
        elif "/pruebas/" in s: hits["pruebas"] += n
        elif "/nucleo/" in s: hits["nucleo_interno"] += n
    out.append((m,path,loc,fn,hits))
for o in out:
    m,path,loc,fn,h = o
    vivo = h["panel"]+h["ventanita"]+h["scripts"]
    tag = "VIVA" if vivo else ("SOLO-PRUEBAS/E2E" if (h["pruebas"]+h["e2e"]) else ("INTERNO?" if h["nucleo_interno"] else "NADIE"))
    print(f"{tag:17s} {m:6s} {path:45s} {loc:24s} panel={h['panel']} vent={h['ventanita']} scr={h['scripts']} nuc={h['nucleo_interno']} test={h['pruebas']} e2e={h['e2e']}")
print(len(out), "rutas")
```
</details>


El resto fueron comandos sueltos citados en cada sección (`lsof`, `launchctl list`, `git cat-file`, `sqlite3 …?mode=ro`, `grep`, `uv run pytest/mypy`, `npm test`).

## Apéndice B — Aristas de importación de `nucleo/` (todas)

`→` imports de módulo; `*` import dentro de función.

- `accesibilidad` → (nada)
- `agenda` → (nada)
- `aldia` → caminos, db, entregas, libros
- `analisis_camino` → db, modelos
- `avisos` → accesibilidad
- `bandeja` → modelos
- `boveda_git` → libros
- `calendario` → db, modelos
- `calibracion` → db, modelos
- `caminos` → libros
- `cierre` → boveda_git, db, episodios, estado_libro, experiencia, libros, modelos, pensar, temas*
- `clasificar` → (nada)
- `claves` → boveda_git, libros, pensar
- `cobros` → temas
- `coding` → db, experiencia, pensar, telegram
- `concreto` → (nada)
- `conexiones` → telegram*
- `correcciones` → boveda_git, db, sembrar_conocimiento
- `db` → modelos
- `entregas` → db, libros, modelos, plata
- `episodios` → boveda_git, db, modelos, pensar
- `estado_libro` → pensar
- `estimacion` → (nada)
- `experiencia` → boveda_git, db, episodios, libros, vectores, correcciones*, modelos*
- `ficha` → aldia, caminos, db, entregas, libros, trabajo
- `gasto` → db
- `gastos` → temas
- `generar_modelos` → (nada)
- `hilos` → db, temas
- `iniciativa` → bandeja, modelos
- `juego` → modelos
- `libros` → (nada)
- `limpiar_pruebas` → db, plata, trabajo
- `memoria_mcp` → db, experiencia, modelos
- `mensaje_cliente` → clasificar, libros
- `modelos` → (nada)
- `noche` → boveda_git, db, estado_libro, experiencia, libros, preguntas, sembrar_conocimiento, telegram, cierre*
- `notion` → notion_sync*
- `notion_avisos` → avisos, db, notion
- `notion_sync` → boveda_git, db, entregas, estado_libro, experiencia, libros, notion
- `orden_rumbo` → (nada)
- `pensar` → concreto, db, gasto, libros, precarga, trabajo, vectores, voseo, cierre*, coding*, sembrar_conocimiento*
- `plata` → db, ficha
- `precarga` → db, libros, estado_libro*, sembrar_conocimiento*, temas*
- `preguntas` → boveda_git, clasificar, db, entregas, iniciativa, libros, modelos, correcciones*, experiencia*, telegram*
- `probar_bloqueos` → pensar
- `produccion` → (nada)
- `refresco_claude_code` → boveda_git, estado_libro, pensar, sembrar_conocimiento
- `reloj` → db
- `rumbo` → db, modelos, plata, reloj, trabajo
- `sanear` → db
- `semana` → bandeja, db, plata
- `sembrar_conocimiento` → db, modelos
- `sembrar_memoria` → db, modelos
- `servidor` → agenda, aldia, analisis_camino, avisos, bandeja, boveda_git, calendario, calibracion, caminos, cierre, clasificar, cobros, coding, conexiones, correcciones, db, entregas, episodios, estado_libro, experiencia, ficha, gasto, gastos, hilos, iniciativa, libros, mensaje_cliente, modelos, notion, notion_avisos, pensar, plata, precarga, preguntas, reloj, rumbo, semana, sembrar_conocimiento, telegram, temas, trabajo, tts
- `simulacion` → (nada)
- `telegram` → entregas*, servidor*
- `temas` → clasificar, libros
- `trabajo` → avisos, boveda_git, caminos, clasificar, db, episodios, estado_libro, libros, modelos, cierre*, experiencia*
- `tts` → (nada)
- `vectores` → libros
- `voseo` → (nada)

# Auditoría B — ¿Estamos reinventando la rueda?

26 oct 2026 · solo lectura (no se tocó código, base, Notion ni Telegram) · rama `main`.
Leído: `CLAUDE.md`, `docs/BIBLIA.md` (I–IV, VII–IX), `docs/ARQUITECTURA-CEREBRO.md`, `docs/ahora.md`, y de la bóveda `README.md`, `plan_boveda.md`, `memoria/README.md`, `inteligencia/README.md` + el código de las piezas.

**Respuesta corta:** en el *motor* casi no reinventamos (SQLite/FTS5, sqlite-vec, SDK oficial de MCP, restic, Tauri, whisper.cpp, Kokoro ya son ruedas ajenas). Reinventamos en tres sitios concretos: **(1)** el parseo de frontmatter/YAML, hecho a mano tres veces; **(2)** la memoria, que vive en tres cuadernos casi vacíos con formatos distintos; **(3)** LangGraph usado para una cadena lineal. Y hay dos hallazgos que no son «rueda» sino riesgo (ver §0).

> Convención: «Qué sabemos» = visto en archivo:línea o con cifra. «Hipótesis» = lo marco así.

---

## 0. Hallazgos que pesan más que la rueda

| # | Qué sabemos | Por qué importa |
|---|---|---|
| A | `~/Library/LaunchAgents` solo tiene `com.remi.nucleo` y `com.remi.noche` (`ls` + `launchctl list`). `scripts/instalar.sh` define 10 (nucleo, ventanita, whisper, copia, noche, notion, refresco-claude-code, vigia, tunel, panel: líneas 13, 154, 205, 249, 294, 337, 380, 422, 467). No hay crontab. | **La copia restic de las 3:00 (`com.remi.copia`) no está programada en este Mac.** `noche.sh:4` dice «corre después de la copia». Hipótesis: no se corrió `instalar.sh` completo tras la última limpieza; confirmar con `launchctl list`. |
| B | `pensar.pensar_con_trastienda` (`nucleo/pensar.py:1606`) manda resumen vivo, claves, estados de libro y cierres (`pensar.py:906`, `claves.py:75`, `estado_libro.py:165`, `cierre.py:210`) a Groq → OpenRouter → Ollama (`nucleo/config/motores.json`). `grep` de «privad / compartible / salud / finanzas» en `pensar.py` no encuentra ningún filtro. | Biblia VII: «finanzas y salud pueden ir a Claude… a nadie más». **Hipótesis (no verificada de punta a punta):** si una conversación de salud/plata se resume en la trastienda, sale del Mac hacia Groq/OpenRouter. Revisar antes de seguir. |
| C | La memoria hoy está casi vacía: `remi.db` tabla `memoria` = 0 filas; `conocimiento/` solo tiene `experiencia/` (1 lección); `conocimiento/proyectos` **no existe** (`libros.py:17` apunta ahí); `~/proyectos/remi-mente` no existe; bóveda `memoria.db` = 2 entradas. | Unificar ahora cuesta casi nada; cada semana de espera lo encarece. |
| D | `ahora.md` ya lo dice: «El FTS de experiencia no se reindexa solo» (arreglado a medias en `noche.py`). Es síntoma de tener un índice por memoria. | Un solo índice no puede quedar desincronizado con otro. |

---

## 1. Pieza por pieza: lo nuestro contra lo que existe

Fechas = último release publicado (API de GitHub/PyPI consultada el 26-oct-2026). «Sale del Mac» = qué datos viajan a un tercero.

### 1.1 Memoria y búsqueda
**Lo nuestro:** `nucleo/experiencia.py` (628 líneas: lecciones .md + FTS5 + reglas propuestas), `nucleo/vectores.py` (209: `nomic-embed-text` por Ollama + `sqlite-vec`), `nucleo/memoria_mcp.py` (231), y en la bóveda `memoria/capturador.py` (249) + `memoria/consultor.py` (243, FTS5 + sinónimos). Todo local.

| Opción | Qué es | Último release | Licencia | ¿Sale del Mac? |
|---|---|---|---|---|
| [basic-memory](https://github.com/basicmachines-co/basic-memory) | Markdown en disco + índice SQLite + MCP; búsqueda semántica; sync bidireccional | v0.24.1 · 23-oct-2026 | AGPL-3.0 | No en local; ofrecen nube de pago opcional |
| [QMD](https://github.com/tobi/qmd) | Buscador local de Markdown: BM25 + vectores + reranker con GGUF (Node) | v2.8.3 · 16-ago-2026 | MIT | No (todo con node-llama-cpp) |
| [mem0](https://github.com/mem0ai/mem0) | Capa de memoria para agentes; extrae «hechos» con un LLM | ts-v3.3.1 · 25-sep-2026 | Apache-2.0 | **Sí por defecto**: su README dice que requiere un LLM y el default es `gpt-5-mini` de OpenAI; se puede apuntar a Ollama |
| [Graphiti (Zep)](https://github.com/getzep/graphiti) | Grafo de conocimiento temporal | v0.31.2 · 20-oct-2026 | Apache-2.0 | Requiere Neo4j/FalkorDB/Neptune + LLM para extraer; sobredimensionado para 1 persona |
| [sqlite-vec](https://github.com/asg017/sqlite-vec) *(ya lo usamos)* | Vectores en SQLite | v0.1.9 · 31-mar-2026 | Apache/MIT | No |

Lectura: basic-memory es lo más parecido a lo que se quiere construir (Markdown + SQLite + MCP). No lo adoptaría tal cual: no tiene `compartible`, ni lecciones con «Lo que creímos / Causa real», ni las 6 leyes, y es AGPL (`PLAN-FINAL` regla 10 pide MIT/Apache). Sí vale **una prueba de 1 hora** comparando su búsqueda con la nuestra antes de escribir más código de búsqueda. mem0 y Graphiti: no, por privacidad/peso.

### 1.2 MCP de memoria
**Lo nuestro:** `nucleo/memoria_mcp.py:20` ya usa `mcp.server.mcpserver.MCPServer` del SDK oficial (`pyproject`: `mcp>=2.2.0`). Herramientas: `indice`, `leer`, `guardar`, `anotar_leccion`, `buscar_lecciones`, `buscar_memoria` (`:50–187`).

| Opción | Último release | Nota |
|---|---|---|
| [python-sdk (SDK oficial MCP)](https://github.com/modelcontextprotocol/python-sdk) *(lo que ya usamos)* | v2.3.0 · 2-oct-2026 | MIT |
| [servidores de referencia, `memory`](https://github.com/modelcontextprotocol/servers) | v2.1.0 · 25-oct-2026 | Grafo en JSON, sin Markdown ni git: no sirve a «el libro lo edita Milo» |
| basic-memory (arriba) | v0.24.1 · 23-oct-2026 | Trae su propio MCP |

Lectura: no hay rueda que reinventar; 231 líneas sobre el SDK oficial son delgadas.

### 1.3 Ingesta de videos y transcripción
**Lo nuestro:** `/Volumes/ORGANIC/boveda/boveda.py` (860 líneas): cascada captions yt-dlp → `youtube-transcript-api` → audio + faster-whisper (`boveda.py:494`), cache por id (`:525`), scoring determinista (`_sistema/reglas_scoring.py`, 242), validador anti-invento (`inteligencia/validador.py`, 534).

| Opción | Último release | Nota |
|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) *(ya)* | 2026.10.21 | Unlicense |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) *(ya)* | v1.2.4 · 29-ene-2026 | MIT |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) *(ya)* | v1.2.1 · 31-oct-2025 (**12 meses sin release**) | MIT; la bóveda lo corre en `device: cpu` (`_sistema/config.yaml`) |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | v1.9.5 · 6-oct-2026 | MIT; **ya corre residente en Remi** (`whisper-server`, `instalar.sh:154–200`) |
| [parakeet-mlx](https://github.com/senstella/parakeet-mlx) | 0.5.3 (PyPI) · 1-oct-2026 | Apache-2.0; Parakeet en Apple Silicon |
| [Fabric](https://github.com/danielmiessler/fabric) | v1.4.555 · 25-oct-2026 | MIT; trae `yt` + patrones, pero **manda la transcripción a un LLM externo** |

Lectura: la cascada y el scoring son valor propio (ninguna librería sabe qué es «oro» para Milo). Lo que sobra: **dos motores Whisper en la misma Mac** (faster-whisper en el venv de la bóveda, whisper.cpp en el servidor de Remi) y un **parser de YAML escrito a mano** (`boveda.py:41–120`, ~80 líneas) porque el venv de la bóveda no trae `pyyaml` (`requirements.txt`: yt-dlp, youtube-transcript-api, faster-whisper, langgraph, kokoro).

### 1.4 Voz
**Lo nuestro:** Whisper local (`whisper-server` :4401) + Kokoro-82M en CPU (`nucleo/tts.py`, 139 líneas; `kokoro` en `pyproject`). Todo local, sin clave.

| Opción | Último release | Nota |
|---|---|---|
| [kokoro](https://pypi.org/project/kokoro/) *(ya)* | 0.9.4 · 5-abr-2025 (**sin release en 18 meses**) | Apache-2.0 |
| [mlx-audio](https://github.com/Blaizzy/mlx-audio) | v0.6.2 · 26-oct-2026 | MIT; TTS y STT sobre MLX (incluye Kokoro) |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | v1.8.0 · 4-sep-2026 | **GPL-3.0** (choca con la regla de licencias) |
| [Handy](https://github.com/cjpais/Handy) | v0.9.8 · 3-oct-2026 | MIT; dictado 100 % local con Parakeet V3. Ya lo usa Milo para dictar; resuelve *otro* problema (escribir en cualquier campo), no la voz de la ventanita |

Lectura: nada que reemplazar. Vigilar Kokoro (proyecto quieto); si se rompe, mlx-audio es el relevo.

### 1.5 Espejo a Notion
**Lo nuestro:** `notion.py` (245) + `notion_sync.py` (436) + `notion_avisos.py` (371) = **1.052 líneas** sobre `httpx` crudo. `notion.py:24` fija la versión de API `2022-06-28` y `:26` `2025-09-03` para data sources. `notion_avisos.py:51` sondea cada 5 min la base «CRM de vida» que escribe Grok Bot.

| Opción | Último release | Nota |
|---|---|---|
| [notion-sdk-py](https://github.com/ramnes/notion-sdk-py) | 3.1.0 · 12-may-2026 | MIT; cliente tipado (reintentos, paginación, errores) |
| [Notion MCP oficial](https://github.com/makenotion/notion-mcp-server) | v2.1.0 · 31-ene-2026 | MIT; pensado para que un *agente* llame a Notion, no para un espejo determinista |
| Exportar/importar Markdown de Notion a mano | — | Sin automatización: contradice «vitrina» |

Lectura: el SDK reemplaza `class Notion` (`notion.py:66–166`, ~100 líneas de transporte). Las reglas (solo `compartible`, 5 avisos/día, 90 min) son nuestras y se quedan. Notion es nube: solo debe recibir lo `compartible: true` (`CLAUDE.md`).
Ojo de coherencia: `notion_avisos.py` **lee** de Notion cada 5 min mientras `CLAUDE.md` dice «solo de ida» hasta `NOTION_VUELTA=1`. El módulo lo documenta (`:10`: «lo único que se escribe de vuelta es Estado = Hecha»), pero la lectura de entrada es un camino de entrada a Remi desde un tercero: hay que tratarlo como dato, nunca como instrucción (Biblia VII).

### 1.6 Bot de Telegram
**Lo nuestro:** `nucleo/telegram.py` (396 líneas): cliente Bot API con `httpx` (`ClienteBotAPI`, `:117`), filtro de privacidad (`es_privado`, `:62`), silencio 23–7 (`:284`), reporte nocturno, tope de 280 caracteres.

| Opción | Último release | Nota |
|---|---|---|
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | v22.8 · 12-jun-2026 | **GPL-3.0** |
| [aiogram](https://github.com/aiogram/aiogram) | v3.31.0 · 25-ago-2026 | MIT; asíncrono, más grande que lo que usamos |
| [ntfy](https://github.com/binwiederhier/ntfy) | v2.34.0 · 24-oct-2026 | Apache-2.0; solo empuja avisos (no recibe ideas). Con el servidor público ntfy.sh el texto pasa por ese servidor; solo es local si se autoaloja |

Lectura: el valor está en las reglas (privado → «Eso lo vemos en el Mac», silencio, tope), no en el transporte (~30 líneas de Bot API). Telegram no cifra extremo a extremo los bots: por eso el filtro es la pieza que importa. Bot API vigente: 10.3 (changelog oficial, https://core.telegram.org/bots/api-changelog; fecha tomada del primer encabezado, 24-ago-2026 — **inferida, no confirmada**). Pendiente conocido: `Bitacora` 26-oct «un error de getUpdates escribe la URL con el token en nucleo.log».

### 1.7 Servicios de fondo (los 10 LaunchAgents)
**Lo nuestro:** `scripts/instalar.sh` genera 10 plists con heredocs de bash; `vigia.sh`, `noche.sh`, `copia.sh`, etc.

| Opción | Nota |
|---|---|
| [launchd](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) *(ya)* | Nativo, sin dependencias. KeepAlive ya probado: se mató el núcleo y se relanzó (Bitácora 26-oct) |
| [Homebrew services](https://docs.brew.sh/Manpage#services-subcommand) | Solo para fórmulas de brew (Ollama sí; nuestros scripts no) |
| PM2 / supervisord | Otra capa; Milo ya usa PM2 en malik. Añade una dependencia por algo que launchd ya hace |

Lectura: la rueda (launchd) es la correcta. Lo que sobra son **agentes**: el núcleo ya levanta sus propios hilos (`telegram.arrancar_hilo`, `notion_avisos.arrancar_hilo:320`). `noche`, `notion`, `vigia`, `refresco` pueden ser tareas dentro del núcleo; quedarían `nucleo`, `whisper`, `ventanita`, y `copia` (independiente a propósito, para que una caída del núcleo no apague la copia). 10 → 4. Ver hallazgo A.

### 1.8 Motores de IA
**Lo nuestro:** `nucleo/pensar.py` (**1.968 líneas**, la segunda más grande). Claude Max por subprocess `claude -p` (`BINARIO`, `:37`), más Venice, Groq, OpenRouter, Ollama. Venice y Ollama ya se llaman por el mismo formato OpenAI-compatible (`_llamar_openai_compatible`, `:1392`); `_llamar_proveedor` (`:1570`) las despacha.

| Opción | Último release | Nota |
|---|---|---|
| [LiteLLM](https://github.com/BerriAI/litellm) | v1.106.4 · 25-oct-2026 | Unifica 100+ proveedores con *fallbacks*. **En marzo de 2026 dos versiones de PyPI (1.82.7 y 1.82.8) salieron comprometidas con un robo de credenciales** ([BleepingComputer](https://bleepingcomputer.com/news/security/popular-litellm-pypi-package-compromised-in-teampcp-supply-chain-attack)); esta librería manejaría *nuestras llaves*. Licencia: la API marca NOASSERTION (hay carpetas empresariales) |
| [llm (Simon Willison)](https://github.com/simonw/llm) | 0.36 · 22-sep-2026 | Apache-2.0; CLI + biblioteca con plugins por proveedor |
| [claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) | v0.2.174 · 24-oct-2026 | MIT; reemplazaría el subprocess de `claude -p`. **No verifiqué** si usa la sesión de Max sin clave de API: sin eso no se puede recomendar |
| [OpenRouter](https://openrouter.ai) *(ya)* | servicio | Un solo endpoint a muchos modelos; los datos salen a OpenRouter y al proveedor final |

Privacidad: todas las opciones mandan el texto fuera del Mac, igual que hoy; la diferencia es la política (hallazgo B), que ninguna librería resuelve por nosotros.

### 1.9 Rumbo y calibración
**Lo nuestro (dos cosas con el mismo nombre):**
- `nucleo/rumbo.py` (612) + `nucleo/calibracion.py` (179): el estratega de la Biblia IX (visión, meta, apuestas, pronóstico). Calibración = adaptación propia, con aviso MIT, de Metaculus/forecasting-tools para no traer pandas/scikit-learn (`LICENCIAS-TERCEROS.md`).
- `boveda/inteligencia/rumbo.py` (706): otra cosa — puntúa notas de la bóveda con reglas y escribe `03_oro/decisiones/rumbo-*.md`. Usa **LangGraph** (`langgraph==0.6.11`).

| Opción | Último release | Nota |
|---|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) *(ya, en la bóveda)* | PyPI 1.2.17 · 24-oct-2026 (nosotros fijamos 0.6.11) | MIT |
| [PydanticAI](https://github.com/pydantic/pydantic-ai) | v2.61.0 · 24-oct-2026 | MIT; agentes tipados |
| Funciones de Python en fila | — | Cero dependencias |
| [forecasting-tools](https://github.com/Metaculus/forecasting-tools) *(ya adaptado)* | — | MIT |

Lectura: `construir()` (`inteligencia/rumbo.py:563–581`) añade 6 nodos y 6 aristas fijas: **ninguna arista condicional, ni ciclos, ni checkpoints** (`grep add_conditional_edges|checkpoint|interrupt` = 0). Es una tubería lineal. LangGraph aquí cuesta una dependencia grande, un pin viejo y un parche de warnings (`:44–54`) a cambio de nada que unas llamadas en fila no den. Y el modelo solo redacta, con verificación mecánica (`_palabras_fuera`, `:357`): esa es la parte valiosa y es nuestra.

### 1.10 Copias
**Lo nuestro:** `scripts/copia.sh` + `config/copia.json`: **restic** cifrado, foto de `remi.db` con la API de backup de SQLite + `integrity_check`, destino iCloud (R2/B2 preparados), clave en el Llavero.

| Opción | Último release | Nota |
|---|---|---|
| [restic](https://github.com/restic/restic) *(ya)* | v0.19.1 · 5-jul-2026 | BSD-2; cifra en el cliente: iCloud solo ve datos cifrados |
| [Kopia](https://github.com/kopia/kopia) | v0.23.1 · 16-jun-2026 | Apache-2.0; con GUI |
| [BorgBackup](https://github.com/borgbackup/borg) + [borgmatic](https://github.com/borgmatic-collective/borgmatic) | 1.4.5 · 18-jul-2026 / 2.1.10 · 5-oct-2026 | Sin soporte nativo de nubes (necesita rclone/SSH) |
| [rclone](https://github.com/rclone/rclone) | v1.75.2 · 9-oct-2026 | Sincroniza; no es copia versionada |

Lectura: restic es la rueda correcta. Falta que *corra* (hallazgo A).

### 1.11 La ventanita (Tauri)
**Lo nuestro:** `apps/ventanita` — Tauri 2 + React + Tailwind, ~8.600 líneas de TS+Rust (`src/`, `src-tauri/src/`); Rust solo para voz/detección (`voz.rs`) y ventana.

| Opción | Último release | Nota |
|---|---|---|
| [Tauri](https://github.com/tauri-apps/tauri) *(ya)* | tauri v2.12.5 · 21-oct-2026 | Apache/MIT; usa `macos-private-api` (transparencia) |
| [Electron](https://github.com/electron/electron) | v45.0.0 · 21-oct-2026 | MIT; más pesado en RAM, sin ventaja para una ventana de 320×180 |
| SwiftUI nativo (`MenuBarExtra`) | Apple | Lo más ligero en Mac, pero reescribir todo y sin reutilizar React ni los tokens |

Lectura: Tauri ya *es* la rueda. No hay razón para moverla.

---

## 2. Veredictos

| Pieza | Veredicto | Razón (2 líneas) |
|---|---|---|
| Memoria y búsqueda (`experiencia`, `vectores`, bóveda/memoria) | **Mantener lo nuestro** + **usar PyYAML** para el frontmatter | Costo 0, 100 % local, y el formato lección («Lo que creímos / Causa real / Cura») no existe en ninguna opción. Quedan 3 cuadernos y 3 parsers: unificar (§4). Respeta leyes 2 y 3 si `veces` no se muestra como contador. |
| MCP de memoria | **Mantener lo nuestro** | Ya usa el SDK oficial (`memoria_mcp.py:20`); 231 líneas. Nada que reemplazar; solo recibir el formato único de §4. |
| Ingesta y transcripción (`boveda.py`) | **Usar librería dentro de lo nuestro** | Mantener cascada + scoring (valor propio); cambiar YAML a mano (`boveda.py:41–120`) por PyYAML y faster-whisper por el `whisper-server` ya residente (hipótesis: hay que probar idioma `auto`; hoy arranca con `-l es`). Todo local. |
| Voz (whisper local, Kokoro) | **Mantener lo nuestro** | 139 líneas, local, sin clave. Kokoro lleva 18 meses sin release: vigilar; relevo = mlx-audio (MIT). |
| Espejo a Notion | **Usar librería dentro de lo nuestro** | `notion-sdk-py` reemplaza el transporte (~100 líneas); las reglas `compartible` y presupuesto se quedan. Notion es nube: solo sale lo `compartible: true`. |
| Bot de Telegram | **Mantener lo nuestro** | El valor es el filtro de privacidad y el silencio, no el transporte; python-telegram-bot es GPL (choca con la regla MIT/Apache) y aiogram no ahorra casi nada. Arreglar el token en el log. |
| Servicios de fondo (10 LaunchAgents) | **Mantener lo nuestro** (launchd), **recortar 10 → 4** | launchd es la rueda; sobran agentes que el núcleo ya puede hospedar como hilos. Prioridad: instalar la copia (hallazgo A). |
| Motores de IA (`pensar.py`) | **Usar librería dentro de lo nuestro** (solo para los 4 motores OpenAI-compatibles) | Mantener `claude -p`, topes, trastienda y política. **No LiteLLM** (incidente de marzo 2026, manejaría llaves); un cliente genérico `httpx`/`openai` basta. Arreglar hallazgo B primero. |
| Rumbo (`rumbo.py` Remi) y calibración | **Mantener lo nuestro** | Es lógica propia (Biblia IX); la calibración es una adaptación MIT ya con aviso y sin pandas. |
| Rumbo de la bóveda (LangGraph) | **Reemplazar** LangGraph por funciones en fila | `construir()` es lineal (`rumbo.py:563–581`); quita dependencia, pin viejo y parche de warnings. La lógica y el validador anti-invento se quedan. |
| Copias (restic) | **Mantener lo nuestro** | Ya es la herramienta estándar y cifra en el cliente (iCloud solo ve cifrado). Falta programarla. |
| Ventanita (Tauri) | **Mantener lo nuestro** | Tauri es la librería; Electron pesa más sin ventaja. Cuesta mantener Rust de audio, pero está acotado a `voz.rs`. |

Leyes: ninguna recomendación toca las 6. Las dos que más se rozan: **ley 3** (`veces:` de las lecciones es un contador de fallos *del sistema*; debe quedar interno y nunca pintarse en el panel) y **ley 2** (una sola Bandeja/un solo lugar: hoy hay tres cuadernos).

---

## 3. La bóveda

### Qué hace bien
- **Cascada de transcripción con timeouts por plataforma** y cache por id (`boveda.py:494`, `:525`; `_sistema/config.yaml` `timeouts`).
- **Scoring sin IA** (`_sistema/reglas_scoring.py`, umbrales oro ≥7 / procesado ≥4): mismo principio que «decisiones por reglas, el modelo solo redacta».
- **Anti-invento verificable**: `inteligencia/validador.py` (534) y `rumbo._palabras_fuera/_numeros_nuevos` (`:357–371`) rechazan texto del modelo con palabras que la nota no dice. Es la regla «estados solo desde evidencia literal» de `ARQUITECTURA-CEREBRO §14`, ya implementada.
- **Consulta con sinónimos locales** (`memoria/consultor.py`; «subtítulos» ≈ «captions») e `inyectar_contexto`.
- **Notas con frontmatter y git** (`697abcc`), legibles en Obsidian.

### Qué duplica de Remi (archivo:línea en los dos lados)
| Tema | Bóveda | Remi |
|---|---|---|
| Parser de frontmatter/YAML | `boveda.py:41–120` (a mano) y `memoria/capturador.py:49–79` (`_valor`, `leer_entrada`) | `libros.py:105` (`_frontmatter`, a mano) + `libros.py:155` (`yaml.safe_load`) — **tres parsers, y Remi mezcla uno a mano con PyYAML** |
| Índice FTS5 | `memoria/indice/schema.sql:12–18` (`entradas_fts`) | `experiencia.py:450–455` (`experiencia_fts`) |
| Lección/decisión | `capturador.py:22` `TIPOS = (error, decision)`, `:96` `capturar` | `experiencia.py:33–36` `SECCIONES_*`, `CLASES = (error, acierto)`; `modelos.py:77` `tipo: Literal["decision"]` |
| Whisper | `boveda.py:453` (faster-whisper, CPU) | `scripts/instalar.sh:154–200` (whisper.cpp residente) |
| Cliente de Ollama (`gemma3:4b`) | `inteligencia/orquestador.py` (URL `BOVEDA_OLLAMA_URL`) | `pensar.py:55–59` (`OLLAMA_BASE`, `gemma3:4b`) |
| Git de la bóveda | repo propio en `/Volumes/ORGANIC/boveda` | `boveda_git.py:44` sobre `conocimiento/` (snapshots antes/después de escribir) |
| «Rumbo» | `inteligencia/rumbo.py` (reglas sobre notas) | `nucleo/rumbo.py` (estratega Biblia IX): **mismo nombre, distinto trabajo** — fuente de confusión |
| Kokoro | `requirements.txt:5` (declarado; no vi ningún `import kokoro` en `.py` de la bóveda — hipótesis: sobra) | `tts.py:92` |

Además, el índice SQLite de la bóveda vive **dentro de ORGANIC** (`memoria/indice/memoria.db`), y la nota de disco de 23-sep dice «ORGANIC: archivos y repos sí, nada vivo en caliente». Un índice que se reescribe no debería estar ahí.

### Cómo entraría como `nucleo/ingesta/` sin perder nada
Propuesta mínima (no se ejecuta; es el encargo):
1. **Paquete** `nucleo/ingesta/` con: `fuentes.py` (yt-dlp, captions, API, transcribir), `puntaje.py` (= `reglas_scoring.py`, sin cambios), `nota.py` (escribe a `mente/` con el frontmatter único de §4), `cli.py` (`python -m ingesta URL`, `--inbox`, `--autocomprobar`). El código se **mueve**, no se reescribe.
2. **Destino:** las notas van a `mente/ingesta/<oro|procesado|raw>/…` con `fuente: ingesta` y `origen: youtube|instagram|tiktok|landing`; entran al mismo FTS/vectores que las lecciones (un solo `reindexar`).
3. **Índice** en el Mac interno (junto a `remi.db`), no en ORGANIC. ORGANIC queda como copia/archivo de los `.md`.
4. **Migración por copia, no por mover** (para no perder nada), con esta lista de comprobación: 10 notas en `03_oro/decisiones/`, 4 en `03_oro/negocio/`, 6 en `03_oro/inteligencia/`, 2 entradas de `memoria/entradas/`, `cache/` (transcripciones), 5 JSON de `inteligencia/memoria/`, `dashboards/dashboard.md`, y que `--autocomprobar` de `boveda.py` y de `capturador.py` pasen desde la nueva ubicación.
5. **Decisión de Milo (no mía):** la bóveda se creó como **otra bóveda, «Remi no se toca»** (`README.md` de la bóveda) y Grok Bot escribe ahí a diario (`Bitacora`: «Remi no se tocó»). Unir rompe esa frontera. Opciones: (a) Grok sigue en ORGANIC y `mente/` la lee por enlace simbólico solo de lectura; (b) Grok pasa a escribir en `mente/ingesta/`. Hipótesis: (a) es el camino que no rompe nada hoy.

---

## 4. Las tres memorias, campo por campo

Las tres: **A** libros/episodios de Remi (`Memoria`, `modelos.py:65–77`, tabla `db.py:76–88`), **B** experiencia de Remi (`Leccion`, `experiencia.py:46–56`, frontmatter `:203–218`), **C** memoria operativa de la bóveda (`capturador.py:96–137`, `schema.sql`). Fuera de la cuenta pero con el mismo problema: las notas `03_oro` (id/fuente/url/score/dominio…), los JSON de `inteligencia/memoria/` y la memoria de Claude Code (`~/.claude/projects/-Users-juancamilo/memory/`, 46 archivos con `name/description/type`).

| Campo | A · libro/episodio | B · lección (experiencia) | C · bóveda/memoria |
|---|---|---|---|
| Dónde vive | `conocimiento/proyectos|episodios|oficios` (no existen aún) + tabla `memoria` | `conocimiento/experiencia/*.md` + `experiencia_fts` + `notas_vector` | `boveda/memoria/entradas/*.md` + `indice/memoria.db` |
| id | UUID (`modelos.py:68`) | **ninguno**; la identidad es el nombre `fecha-tema-síntoma` | `YYYYMMDD-hash8` |
| título | `titulo` ≤80 | `titulo` | `titulo` |
| resumen | `resumen` ≤240 | `resumen` | **no tiene** |
| tema/área | `tema` | `tema` | **no tiene** (hay `tags`) |
| fecha | `fecha` (datetime) | `ultima_vez` (date) | `fecha` (date) |
| tipo / clase | `tipo` = `decision` o nulo; el frontmatter añade `libro|oficio|referencia` | `tipo: leccion` + `clase: error|acierto` | `tipo: error|decision` |
| cuerpo | libre | **secciones fijas** (error: Síntoma / Lo que creímos / Causa real / Cura / Cómo verlo antes; acierto: Qué funcionó / Evidencia / Cuándo usarlo) | libre |
| fuente | `conversacion|manual|ollama` | `claude-code|claude-app|remi|bitacora|manual` | **no tiene** |
| claves | `claves` (3–6) | no | `tags` |
| nivel de detalle | `nivel` 0–3 | no | no |
| evidencia | no | solo en la sección «Evidencia» de aciertos | no |
| repeticiones | no | `veces` + `vueltas` | no |
| origen (repo/archivo) | `ruta` (proyecto) | `donde` | no |
| vectores | sí (`vectores.py`) | sí | **no** |
| FTS5 | no (lee del estante) | sí | sí |
| commit | sí (`boveda_git`) | sí | commit manual de sesión |
| `compartible` | no en el modelo (viene del contrato Tarea/Idea) | no | no |

Qué sale de la comparación: **B es la más rica** (secciones, veces, evidencia), **C es un subconjunto de B** (error|decision, sin resumen/tema/fuente) y **A** aporta lo que B no tiene (`claves`, `nivel`). El MCP ya los mezcla: `guardar(tipo="decision")` en A y `anotar_leccion` en B (`memoria_mcp.py:103`, `:144`).

### Formato único propuesto
Un solo frontmatter para todo lo que viva en `mente/`; lo que no aplica, se omite.

```yaml
---
id: 7f3c…                # UUID. Para lecciones: uuid5(slug) → estable, sin estado nuevo; respeta Memoria.id: UUID
titulo: "La noche no reindexaba el FTS"   # ≤80
resumen: "…con qué quedarme"              # ≤240
tipo: leccion              # leccion | decision | libro | oficio | episodio | ingesta | referencia
clase: error               # solo si tipo=leccion: error | acierto
tema: coding               # proyecto o área (= «dominio» de la bóveda)
fecha: 2026-10-26          # creación
ultima_vez: 2026-10-26     # última vez que se tocó o volvió a pasar
fuente: claude-code        # claude-code | claude-app | remi | grok | bitacora | manual | ingesta
donde: remi/nucleo/noche.py  # repo/archivo, o URL si es ingesta
evidencia: "commit ea54caa; test_noche rojo→verde"   # obligatoria si tipo=leccion (Biblia VII)
claves: [fts, noche]       # = tags de la bóveda
nivel: 2                   # 0–3 (ARQUITECTURA-CEREBRO §2)
compartible: false         # solo true puede tocar espejos (CLAUDE.md)
veces: 1                   # INTERNO: nunca se muestra como contador (ley 3)
---
```
Cuerpo: secciones fijas de B según `clase`; para `decision`: «Qué se decidió / Por qué / Qué lo cambiaría»; el resto, libre.

Notas de diseño: (1) `id` sigue siendo UUID para no tocar `contratos.json` (cambiar un contrato se conversa primero). (2) El mapa a la página de Notion va en una tabla de SQLite (`espejo(id, notion_page_id)`), no en el frontmatter. (3) `tags`→`claves`, `dominio`→`tema`, `ultima_vez` cubre `fecha_ingesta`. (4) Un solo parser (PyYAML), un solo `reindexar`, un solo FTS.

---

## 5. Top 5 de cambios que más simplifican (ahorro / esfuerzo)

Esfuerzos y ahorros son **estimaciones mías** (horas de trabajo con Claude Code; líneas aproximadas), no medidas.

| # | Cambio | Esfuerzo | Ahorro | Riesgo / reversión |
|---|---|---|---|---|
| 1 | **Quitar LangGraph** de `inteligencia/rumbo.py`: 6 funciones en fila (`:563–581`) y borrar el parche de warnings (`:44–54`) | ~1 h | 1 dependencia grande + un pin viejo (0.6.11 vs 1.2.17) + 11 líneas de parche | Bajo: `--autocomprobar` (`rumbo.py:614`) lo cubre; `git revert` |
| 2 | **Un solo parser de frontmatter (PyYAML)**: borrar `cargar_yaml` (`boveda.py:41–120`), `leer_entrada` (`capturador.py:56–79`) y unificar `libros._frontmatter` (`:105`) | ~2 h | ~150 líneas y 3 fuentes de errores de formato | Bajo-medio: un frontmatter raro puede fallar; hay pruebas en `nucleo/pruebas` |
| 3 | **Una sola memoria + formato único (§4)**: meter bóveda/memoria (492 líneas) dentro de `experiencia.py`, migrar 2 entradas, portar sinónimos de `consultor.py` e `inyectar_contexto` (ya hay un consumidor: `coding.py`) | ~4 h | ~400 líneas, 1 base y 1 FTS menos, y se cierra el bug del FTS sin reindexar (hallazgo D) | Medio: tocar el MCP; migración por copia; revertible |
| 4 | **Programar la copia y recortar LaunchAgents 10 → 4** (`noche`/`notion`/`vigia`/`refresco` como hilos del núcleo) | ~3 h | Menos plists/heredocs en `instalar.sh`; y deja de correr *sin copia* (hallazgo A) | Medio: afecta producción local; hacerlo con `launchctl` y probar matando el núcleo |
| 5 | **Un solo Whisper**: la ingesta llama al `whisper-server` ya residente y se quita `faster-whisper` del venv de la bóveda | ~2 h | Un motor y un modelo menos en memoria; un venv más liviano | Medio: hipótesis a probar (idioma `auto`, límite de duración); si falla, queda la cascada actual |

Quedan fuera del top 5, por ahorro menor: `notion-sdk-py` (~100 líneas), cliente OpenAI-compatible único en `pensar.py`, quitar `kokoro` de los requisitos de la bóveda.

**Antes del top 5 (no es simplificación, es riesgo):** hallazgo B (la trastienda y la privacidad de salud/plata) y el token en `nucleo.log`.

---

### Qué NO verifiqué
- El contenido de la base de Notion «Remi · CRM de vida» (no se llamó la API, como pediste).
- Que `whisper-server` acepte idioma `auto` y archivos largos; que faster-whisper en Mac no use GPU Metal (lo asumo por cómo está configurado: `device: cpu`).
- Si hay filtro de privacidad *aguas arriba* de la trastienda (busqué en `pensar.py`, `noche.py`, `episodios.py`, `claves.py`, `estado_libro.py`, `servidor.py`; no vi ninguno).
- Si `claude-agent-sdk-python` usa la sesión de Max sin clave de API.
- La fecha del Bot API 10.3 (inferida del changelog) y las afirmaciones de privacidad de mem0 y Graphiti más allá de lo que dicen sus README.
- Los 6 fallos previos de la suite (`ahora.md`) y que el código de Tauri/Rust no tenga más piezas reemplazables.
- Que los demás LaunchAgents no estén instalados por otro camino (miré `~/Library/LaunchAgents`, `launchctl list` y `crontab`).

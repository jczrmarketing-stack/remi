# Bóveda v2 · «la mente»: diagnóstico y arquitectura (30-oct-2026)

Meta que fijó Juan Camilo: que la bóveda sea una pieza de ingeniería que haga que cualquier Claude entienda quién es él, su negocio, sus metas y sus ambiciones; que sea de **entrada y salida** (Claude la consulta primero y le devuelve lo que aprende); que ahorre tokens de forma medible; y que Obsidian sea la ventana.

## 1. Qué hay hoy (medido)

**Contenido.** 27 notas en `03_oro/`, de las cuales 10 son salidas de Rumbo, 6 son ejemplos de `inteligencia/`, 5 son ejemplos de negocio sembrados a mano, 4 son reels reales (ai-tools), 1 de contenido y 1 de campo. 2 notas en raw, 1 en procesado. 164 KB en total. **La bóveda como conocimiento está casi vacía; lo que existe es la tubería.**

**Cuatro memorias que no se hablan:**
1. `remi.db`, tabla `memoria` («el estante», MCP `memoria`, sembrada por `sembrar_memoria.py`).
2. `remi/conocimiento/` (markdown + git propio: `vida/` y `experiencia/`), lo que lee el MCP `remi` y los hooks.
3. `boveda/memoria/` (capturador, consultor y su propia `memoria.db` con FTS).
4. `boveda/inteligencia/memoria.py` + `hechos/*.json` + `contexto.yaml` (que todavía describe «marketing para clínicas»: está vencido).
Además `nucleo/vectores.py` indexa carpetas que no existen (`proyectos/`, `areas/`, `oficios/`, `episodios/`): por eso fallan 6 pruebas del núcleo.

**Obsidian:** no hay ningún vault configurado (`.obsidian` no existe ni en la bóveda ni en `conocimiento/`). La decisión «Obsidian como ventana» no se ejecutó.

**Clasificación:** carpetas por puntaje (`01_raw`, `02_procesado`, `03_oro/<tema>`) con reglas de palabras clave; el puntaje no distingue (6 de 8 reels sacaron 8). En curso: enriquecimiento con Ollama (títulos, resumen, ideas, relevancia).

**Infraestructura:** dos repos, dos `.git`, dos entornos de Python (3.13 en la bóveda, 3.12 en el núcleo), dos lectores de YAML (uno a mano, uno PyYAML), la bóveda en el disco externo ORGANIC (si el disco no está, `preguntar` y Telegram pierden la memoria), el repo de Remi público en GitHub con `conocimiento/` como git anidado.

**Entrada y salida hoy:** entrada sí (hook de inicio con `estado_vivo`, hook de prompt que busca en la bóveda, MCP `preguntar`). Salida casi no: `anotar` escribe en una bandeja y en supuestos; lo que Claude investiga o decide en una sesión no vuelve a la bóveda de forma estructurada.

## 2. Principio de la v2

La bóveda no es una carpeta de videos. Es **una sola mente** con cuatro tipos de conocimiento, y cada nota dice de dónde salió, cuándo y cuánto confiar:

| Carpeta | Qué guarda | Fuente típica | Quién escribe |
|---|---|---|---|
| `mente/yo/` | quién es: perfil, metas, recursos, valores y reglas, restricciones (idioma, tiempo, energía) | él mismo | él, o Claude con confirmación |
| `mente/negocio/` | frentes, clientes, ofertas, precios, **cifras propias** (órdenes, cobros, horas) | CRM, Fiverr, Malik | Remi (noche), Claude |
| `mente/mundo/` | mercado: `campo/` (medido), `fuentes/` (videos y blogs, con `estatus: evidencia\|hipotesis`), `repos/`, `investigaciones/` (lo que Claude investigó, con URLs) | bots, bóveda, Claude | automático |
| `mente/aprendido/` | `lecciones/`, `decisiones/` (con razones y fecha), `diario/` (predicciones y resultados) | sesiones, Rumbo | Claude, Rumbo |
| `mente/bandeja/` | todo lo crudo que entra y aún no tiene sitio | Telegram, hooks | automático |

Debajo, **un solo índice** (`indice.db`: FTS5 + sqlite-vec con `nomic-embed-text`) que se regenera del markdown por hash. El índice es derivado: se puede borrar y reconstruir; la verdad es el markdown. Status (`raw/procesado/oro`) deja de ser carpeta y pasa a ser campo del frontmatter.

## 3. Entrada y salida: el protocolo

**Entrada (bóveda → Claude), sin tokens:**
- `SessionStart`: `estado_vivo` (≤1.500 tokens), construido de `yo/` + `negocio/` + supuestos vencidos. Hecho.
- `UserPromptSubmit`: la bóveda busca lo que ya tiene sobre el mensaje y lo pone en contexto. Hecho.
- MCP `preguntar(q)`: devuelve **resumen + fecha + estatus + confianza**, nunca la transcripción entera; `leer(id)` trae el cuerpo solo si hace falta (hoy existe en el MCP `memoria`; se unifica en `remi`).

**Salida (Claude → bóveda), con compuerta:**
- `anotar(tipo=...)` crece a: `hecho_sobre_mi`, `decision`, `investigacion` (obliga `fuentes: [URL]`), `leccion`, `supuesto`, `resultado`, `hipotesis`.
- Compuerta por tipo: lo que toca `yo/` se guarda como **pendiente de confirmar** y Remi pregunta por Telegram «¿guardo esto: …?» (sí/no), salvo que sea cita literal suya. Lo que toca `mundo/` exige URL primaria o va a `bandeja/` como hipótesis. `aprendido/` se escribe directo.
- Al cerrar una sesión de Claude Code: regla en `CLAUDE.md` + hook `Stop`/`PreCompact` que recuerda escribir «qué decidimos, qué aprendimos, qué investigamos» con `anotar` (5 líneas máximo).
- La **noche** consolida: bandeja → carpeta correcta; actualiza `estado.md`; marca supuestos vencidos; re-indexa; genera `_indice.md` de repos y de investigaciones.

**Regla que no se negocia:** lo que Juan Camilo dice no pisa un hecho verificado; se marca el choque y se pregunta cuál vale. Lo que Claude concluye no se guarda como hecho: se guarda como hipótesis o decisión, con fecha.

## 4. Obsidian como ventana (ejecutar, no solo decidir)
- `mente/` **es** el vault: `.obsidian/` con tema oscuro y 3 plugins core (Properties, Backlinks, Daily notes → `aprendido/diario/`). Un plugin comunitario: **Dataview** (o Bases, nativo desde Obsidian 1.9) para tablas vivas: repos por veredicto, fuentes por estatus, supuestos vencidos, decisiones por frente.
- Frontmatter uniforme (`tipo`, `fecha`, `fuente`, `nivel`, `estatus`, `confianza`, `frentes`, `visto_en`) para que Properties lo muestre y Dataview lo consulte.
- Enlaces `[[...]]` entre `yo/`, `negocio/` y `mundo/` (una nota de campo enlaza al frente de INVERZA al que sirve). Backlinks dan el grafo gratis, con sentido.
- Plantillas: nota de fuente, decisión, experimento, día.
- Él edita en Obsidian; git guarda; el índice se regenera en la noche o al guardar (watch opcional). No se usa Obsidian Sync: el móvil entra por Telegram.

## 5. Cómo ahorra tokens (y cómo se mide)
1. Contexto que no hay que repetir: `estado_vivo` + hook de prompt (hecho). Mide: tokens por sesión de Claude Code (`ccusage` o el JSONL de `~/.claude/projects`), semana a semana.
2. Investigaciones que no se repiten: `investigaciones/` con fuentes, servidas por el hook. Mide: consultas respondidas desde la bóveda sin WebSearch (contador en el hook).
3. Resúmenes locales (Ollama) en vez de pedirle a Claude que lea transcripciones. Mide: notas enriquecidas sin tokens de pago.
4. Respuestas sin modelo por Telegram (`/estado`, `/repos`, `/campo tema`): texto desde archivos.
5. `preguntar` devuelve resúmenes, no cuerpos; `leer` solo bajo demanda.
Un archivo `mente/aprendido/uso.md` con estas cinco métricas, actualizado por la noche.

## 6. Qué se quita, qué se junta, qué se agrega
**Quitar / archivar:** `boveda/memoria/` (capturador, consultor, memoria.db), `inteligencia/memoria.py` y `hechos/*.json`, `inteligencia/contexto.yaml` (vencido; lo reemplaza `yo/` + `negocio/`), las notas de ejemplo (`ejemplo-*`, `me-at-the-zoo`, muestras de `inteligencia/`) fuera del vault para no ensuciar la búsqueda, LangGraph en `rumbo.py`, el lector de YAML a mano (PyYAML en los dos lados), las carpetas por puntaje.
**Juntar:** las cuatro memorias en `mente/` + `indice.db`; el MCP `memoria` dentro del MCP `remi` (`leer`, `anotar_leccion`, `buscar_lecciones` pasan a `remi`); `vectores.py` apuntando a `mente/` (arregla las 6 pruebas); el código de ingesta a `nucleo/ingesta/` (U2) con un solo entorno; `campo.py` y `repos.py` como sensores de `mundo/`.
**Agregar:** `yo/` sembrado con lo que ya dijo (perfil, metas, recursos, valores, restricciones) con fecha por línea; `negocio/cifras-propias.md` desde la exportación de Fiverr; `investigaciones/`; `diario/`; compuerta de escritura; vault de Obsidian; `uso.md`.
**Ubicación:** `mente/` es texto (hoy menos de 1 MB): va en el disco interno (`~/proyectos/mente`, git privado con remoto privado, cubierto por restic). En ORGANIC quedan solo los pesados: audio, transcripciones crudas, cache de Whisper. Así Remi no pierde la memoria cuando el disco no está.

## 7. Orden de ejecución (cada paso deja algo usable)
1. Crear `~/proyectos/mente` con la estructura, mover `conocimiento/vida` y `experiencia`, sembrar `yo/` desde `estado.md` y sus frases; apuntar `vida.py`, hooks y MCP a `mente/`. Vault de Obsidian con plantillas. (medio día)
2. `indice.db` único (FTS5 + vec) con `indexar.py` por hash; `preguntar` devuelve resumen + estatus + confianza; `leer(id)`. Mover `vectores.py`. Arreglar las 6 pruebas. (medio día)
3. `anotar` con tipos y compuerta; confirmación por Telegram para `yo/`; hook de cierre; la noche consolida bandeja y escribe `uso.md`. (un día)
4. Migrar la ingesta a `nucleo/ingesta/` con un solo entorno; notas de videos a `mundo/fuentes/` con `estatus`; archivar ejemplos; apagar las memorias viejas. (un día)
5. Dataview/Bases: tablas de repos, fuentes, supuestos, decisiones. `/estado`, `/repos`, `/campo` por Telegram. (medio día)

## 8. Cómo sabremos que la v2 sirve
- Claude Code arranca sabiendo quién es él sin que se lo cuente (ya), y además **sabe sus metas, recursos y restricciones** desde `yo/`.
- Una pregunta ya investigada se responde desde la bóveda sin WebSearch (contador > 0 la primera semana).
- Tokens por sesión bajan semana a semana (medido, no sentido).
- Una sola búsqueda (`preguntar`) encuentra una lección, una cifra de campo, una decisión y una nota de video en la misma consulta.
- Obsidian abre `mente/` y las tablas vivas muestran repos y fuentes sin que nadie las escriba a mano.

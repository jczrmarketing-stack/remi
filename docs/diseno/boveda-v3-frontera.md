# Bóveda v3 · arquitectura de frontera con recursos gratuitos (30-oct-2026)

Lo que pidió Juan Camilo: «lo más frontera en cuanto a arquitectura, con recursos gratuitos», porque la bóveda será la memoria del negocio y de todos los agentes (el Jarvis). Este documento reemplaza la parte de arquitectura de `boveda-v2-mente.md` §2–§5 y la amplía; el diagnóstico y el protocolo de entrada/salida de la v2 siguen valiendo.

## 0. Qué es «frontera» en memoria de agentes hoy (y qué no)

Lo que separa a los sistemas serios en 2026 no es la base de datos ni el modelo: son seis prácticas. Las seis caben en un Mac mini sin pagar nada.

1. **Archivos como verdad, índices derivados.** Markdown legible por humanos (Obsidian) y por cualquier agente; todo índice se puede borrar y regenerar. Es lo que hace Claude Code con `CLAUDE.md` y su memoria de archivos, y lo que Anthropic recomienda como «structured note-taking».
2. **Recuperación híbrida con reordenamiento y trozos contextualizados.** BM25 + vectores, fusionados, y un reordenador encima. Anthropic midió: contextualizar los trozos baja los fallos de recuperación 49 %; con reordenador, 67 %.
3. **Hechos con tiempo y procedencia.** Cada afirmación sabe de qué nota salió, con qué cita literal, cuándo se dijo y hasta cuándo vale; un hecho nuevo puede invalidar uno viejo (la idea central de Graphiti/Zep). Los propios evaluadores independientes dicen que «el razonamiento temporal sobre hechos versionados es un problema de frontera» y que casi nadie lo trata como ciudadano de primera.
4. **Consolidación en tiempo de sueño.** Un proceso barato, fuera de la conversación, que une duplicados, detecta patrones, archiva lo vencido y reescribe resúmenes (Letta lo llama *sleep-time compute*). Nuestra `noche.py` es exactamente ese lugar.
5. **Entrega justo a tiempo y por capas.** No cargar el contexto completo: identificadores ligeros, fichas primero y cuerpo solo si hace falta («progressive disclosure»). Es lo que ya hace `preguntar` + `leer`, y es la fuente real del ahorro de tokens.
6. **Evaluación que bloquea cambios.** Un conjunto de preguntas con respuesta conocida; ningún cambio de modelo, trozo o índice entra si no mejora el número.

Lo que **no** es frontera, aunque suene: un grafo Neo4j, otro framework encima, un modelo más grande «por si acaso», o un servicio de vectores en la nube. Para 30–3.000 notas, SQLite con FTS5 + sqlite-vec es más rápido, más simple y gratis.

## 1. Principios que no se negocian

- **El markdown es la verdad.** `indice.db` y las tablas de afirmaciones se regeneran del markdown por hash. Si se corrompen, se borran.
- **Todo hecho lleva procedencia, fecha y vigencia.** Sin cita literal no es hecho: es hipótesis.
- **Local primero.** Lo que toca `yo/` y `negocio/` nunca sale del Mac. Las APIs gratuitas solo ven texto público (transcripciones de videos, blogs, repos), porque los niveles gratuitos entrenan con lo que les mandas (Google lo dice en su página de precios).
- **Claude Max solo de noche y solo como juez o maestro**, nunca como obrero de cada nota: sus límites de 5 horas y semanales son el recurso escaso.
- **Cero etiquetado manual.** La bóveda titula, resume, clasifica y detecta pedidos sola. Él solo confirma lo que toca `yo/` (sí/no por Telegram).
- **Medir o no cambiar.**

## 2. Las capas

```
Telegram / Claude (anotar) / sensores
        │
        ▼
 [1] CAPTURA ──► [2] EXTRACCIÓN ──► [3] MEMORIA ──► [4] NOCHE ──► [5] RECUPERACIÓN ──► [6] PUERTA MCP ──► cualquier agente
                                     markdown        consolida      router + híbrida     preguntar/leer
                                     + indice.db     + hallazgos    + rerank + umbral     anotar/afirmar
                                     + afirmaciones  + métricas     + fichas primero      hallazgos/entidad
```

### [1] Captura — ya existe; se completa
Hoy: cualquier link por Telegram (video, blog, repo), transcripción en cascada (captions → API → Whisper local), `web.py`, `repos.py`, sensores de campo, detección de «comenta X». Falta: PDF (`pypdf`, local), y nada más. X y LinkedIn no tienen vía honesta sin API: se dejan fuera.

### [2] Extracción — una pasada por nota, estructurada
Por cada nota, un solo JSON (ya existe la mitad en `enriquecer.py`): título, resumen con citas, ideas, afirmaciones por tipo con cita literal, cifras, interés del autor, fuente citada, pedido (comenta X), **y lo nuevo:** entidades (herramienta, repo, persona, empresa, precio) con sus alias tal como aparecen, relaciones entre ellas (`X usa Y`, `X cuesta Z`, `X compite con Y`), y los links que la nota cita (los de GitHub van solos a `repos.py`).

**Quién extrae, en dos etapas, por privacidad y por calidad:**
- **Etapa A, texto público → API gratuita o local.** Gemini Flash-Lite gratis (reportes de desarrolladores hablan de ~500 peticiones/día para Flash-Lite y ~20 para Flash; Google ya no publica los límites, se ven en AI Studio) o Mistral gratis (límites no publicados) o OpenRouter `:free` (50 peticiones/día). Entra solo la transcripción, sin frentes ni contexto personal. Si la API no responde, cae a Ollama local y la nota se marca `extraccion: local`.
- **Etapa B, relevancia para los frentes → local siempre.** Con el resumen y las afirmaciones ya extraídas (texto corto), gemma3:4b decide relevancia por frente y qué hacer con la nota. Con entrada corta el modelo chico rinde; con 16.000 caracteres crudos, no. Esto explica el `frentes: []` de hoy.
- **Trozos contextualizados.** Las transcripciones largas se parten en trozos de ~800 tokens y cada trozo recibe 1–2 frases de contexto generadas en local (qué video es, de qué parte habla) antes de indexarse. Es la técnica de Anthropic; en local cuesta tiempo, no dinero.

### [3] Memoria — archivos + un índice + afirmaciones
`mente/` sigue igual (`yo/ negocio/ mundo/ aprendido/ bandeja/`). Debajo, `indice.db` crece a:

| Tabla | Qué guarda |
|---|---|
| `notas` | ruta, hash, tipo, fecha, estatus, confianza, frentes |
| `trozos` + `trozos_fts` + `trozos_vec` | texto con contexto, BM25, vector |
| `entidades`, `alias` | nombre canónico, tipo, alias vistos (resolución conservadora: se funden solo con similitud alta; lo dudoso queda como sugerencia en `mundo/entidades/_dudas.md`) |
| `afirmaciones` | sujeto, predicado, objeto/valor, cita literal, nota, autor, interés del autor, nivel de evidencia T1–T4, `dicho_en`, `valido_desde`, `valido_hasta`, `invalidada_por` |
| `hallazgos` | frente, tipo (coincidencia/contradicción/pregunta), afirmaciones que lo sostienen, fecha |
| `consultas` | cada búsqueda: quién, consulta, tokens devueltos, si hubo acierto, si después hubo búsqueda web |

Las afirmaciones **bitemporales** son la pieza que vuelve posibles el filtro de la verdad, los hallazgos y la teoría de juegos: «Manus cuesta $X (dicho 2026-10 por un influencer con interés alto, T4)» puede ser invalidada por «Manus cuesta $Y (página oficial, T1)», y la contradicción queda registrada en vez de perderse.

**Embeddings:** se reemplaza `nomic-embed-text` (entrenado en inglés) por `qwen3-embedding:0.6b` (oficial en Ollama, más de 100 idiomas; la versión 8B es la primera del ranking multilingüe MTEB). Se decide con el conjunto de evaluación, no por fe. **Reordenador:** `bge-reranker-v2-m3` o `Qwen3-Reranker-0.6B` en local (sentence-transformers, CPU/MPS), solo sobre los 20 mejores candidatos: barato.

### [4] Noche — consolidación en tiempo de sueño
`noche.py` adopta el calendario de Letta y nuestras reglas:
- **Cada noche:** bandeja → carpeta; extraer lo que falte; re-indexar por hash; fundir entidades duplicadas; detectar contradicciones nuevas; escribir `mundo/hallazgos/<frente>.md` (coinciden / se contradicen / evidencia vs hipótesis / preguntas abiertas); marcar supuestos vencidos; actualizar `estado.md`; `uso.md` con métricas; `git push` a un repo privado gratis.
- **Cada semana (domingo):** reorganización mayor: resúmenes de frente, tasas base propias para Rumbo (export de Fiverr), lecciones repetidas se proponen como procedimientos (`aprendido/procedimientos/`, candidatas a skills de Claude Code).
- **Cada mes:** rollups: lo que no se consultó ni se citó en 90 días baja a `_archivo/` (regla de Letta: «cuenta más cuántas veces se usó que la edad»). Decisiones y hechos sobre él **no caducan**.
- **Juez y maestro (Claude Max, de noche):** una vez por semana `claude -p --model haiku` califica 20 extracciones al azar del modelo local (¿las citas existen? ¿el resumen es fiel? ¿la relevancia tiene sentido?) y produce 5 ejemplos corregidos que se suman al prompt local. Es destilación barata: el modelo gratis mejora con el tiempo sin que él etiquete nada. Cuenta contra su límite semanal; por eso es semanal y de noche.

### [5] Recuperación — donde se ahorran los tokens
- **Router antes de buscar.** El hook `UserPromptSubmit` no inyecta nada si el mensaje no toca su mundo: primero FTS (gratis) y un umbral de similitud vectorial; si nada pasa el umbral, cero tokens. Hoy `preguntar` siempre devuelve algo: eso gasta y confunde.
- **Híbrida + reordenada.** BM25 y vectores fusionados por rango recíproco (RRF), los 20 mejores al reordenador, umbral, y se entregan **fichas** (título, resumen, fecha, estatus, confianza, id) con presupuesto fijo (≤ 600 tokens en el hook, ≤ 1.200 en `preguntar`). El cuerpo solo con `leer(id)`.
- **Hallazgos antes que notas.** Si la consulta toca un frente con hallazgos, se devuelve el hallazgo (ya cruzado) y no 5 notas sueltas: menos tokens y mejor respuesta.
- **Medición honesta**, en `consultas`: tokens inyectados por sesión, aciertos (Claude usó la ficha: la citó o llamó `leer`), y **búsquedas web evitadas** (hook `PostToolUse` sobre WebSearch/WebFetch registra si hubo búsqueda web después de un acierto de la bóveda). `uso.md` semanal: «la bóveda respondió X de Y consultas; Z búsquedas web evitadas; ~N tokens de contexto ahorrados contra inyectar cuerpos completos». Si el número no sube, la arquitectura no sirve y se cambia.

### [6] Puerta única — MCP `remi` para todos los agentes
Un solo servidor, las mismas herramientas para Claude Code, Claude escritorio, el bot de Telegram, la ventanita y cada agente futuro de la fábrica: `estado_vivo`, `preguntar`, `leer`, `anotar(tipo)`, `afirmar(sujeto, predicado, valor, cita, fuente)`, `hallazgos(frente)`, `entidad(nombre)`, `supuestos`. Regla en `CLAUDE.md` global: *antes de buscar en la web, `preguntar`; al terminar, `anotar` lo investigado con fuentes.* Un agente nuevo se conecta con una línea de configuración, sin código.

## 3. Recursos gratuitos: decisión por tarea

| Tarea | Recurso | Por qué | Límite o riesgo |
|---|---|---|---|
| Transcribir | faster-whisper local | hecho, gratis | tiempo de CPU |
| Embeddings | `qwen3-embedding:0.6b` (Ollama) | multilingüe; `nomic` es inglés | reindexar todo (minutos) |
| Reordenar | `bge-reranker-v2-m3` local | +18 puntos de mejora medidos por Anthropic sobre híbrida sola | ~1 s por consulta en CPU |
| Extraer texto público | Gemini Flash-Lite gratis → Mistral gratis → local | 1M de contexto, JSON confiable | límites no oficiales (~500/día); **entrena con los datos**: solo texto público |
| Relevancia, títulos, contexto de trozos | gemma3:4b local (qwen3:8b si la RAM alcanza) | entrada corta, tarea cerrada | calidad: por eso el juez semanal |
| Juez/maestro semanal | `claude -p --model haiku` (Max) | ya pagado | cuenta contra el límite semanal: 1 vez por semana, de noche |
| Índice y afirmaciones | SQLite + FTS5 + sqlite-vec | cero servicios, un archivo | ninguno a esta escala |
| Ventana | Obsidian + Bases/Dataview | gratis | — |
| Copia | GitHub privado (`mente/`) | gratis; hoy no hay copia | token en el Mac |

## 4. No inventar la rueda: veredicto por proyecto

| Proyecto | Licencia | Veredicto | Razón |
|---|---|---|---|
| **Graphiti / Zep** | Apache 2.0 | **ADOPTAR LA IDEA**, no el stack | Hechos con `valid_at`/`invalid_at` e invalidación: lo copiamos en SQLite. El stack exige Neo4j/FalkorDB y extracción con API de pago por episodio; no está pensado para Ollama, y su consumo de tokens por ingesta está en disputa. |
| **Letta** | Apache 2.0 | **ADOPTAR LA IDEA** | Calendario de consolidación, caducidad por tipo, «uso sobre edad», modelo barato para el sueño. El runtime reemplazaría nuestro orquestador: no. |
| **Cognee** | Apache 2.0 | **INSPIRARSE; candidato a bake-off** | Corre local (NetworkX/Kuzu + vectores) y hace grafo + embeddings de documentos. Riesgos: deriva de esquema (entidades duplicadas) que exige auditorías, y Kuzu está archivado desde oct-2025. Si tras F1.4 el recall@5 propio queda bajo 0,8, se prueba Cognee local contra el mismo conjunto. |
| **mem0** | Apache 2.0 | **DESCARTAR** aquí | Memoria de preferencias; débil en relaciones y en tiempo (el tiempo es un metadato más). Sus cifras de LongMemEval no se reproducen fuera de su propio arnés (93,4 % declarado vs 73,8 % reproducido). |
| **LightRAG / HippoRAG 2** | MIT / MIT | **INSPIRARSE** | Recuperación por grafo local con Ollama. Solo entra si el bake-off lo justifica. |
| **Contextual Retrieval + Context Engineering (Anthropic)** | — | **ADOPTAR TÉCNICAS** | Trozos contextualizados, híbrida + rerank, justo a tiempo, divulgación progresiva, notas estructuradas, compactación. |
| **Qwen3-Embedding / Reranker** | Apache 2.0 | **ADOPTAR** si gana en el conjunto | Oficiales en Ollama; multilingües. |
| **Claude memory tool / auto-memory de Claude Code** | — | **YA LO HACEMOS** | Memoria en archivos; nuestra diferencia es que es una sola para todos los agentes y con procedencia. |

## 5. Evaluación (la que bloquea cambios)

- **Conjunto dorado automático, sin etiquetar:** por cada nota, el modelo local genera 2 preguntas que esa nota responde (consultas sintéticas) → `evaluacion/preguntas.jsonl`. Más las últimas 20 consultas reales de `consultas` con acierto confirmado.
- **Métricas:** recall@5 y MRR del recuperador; tokens medianos devueltos por consulta; precisión de citas (¿existen en la nota?) de la extracción; proporción de notas con `frentes: []`.
- **Regla:** cambio de embeddings, reordenador, trozos o modelo entra solo si recall@5 no baja y los tokens no suben. `python3 -m nucleo.evaluar` imprime la tabla; la noche la guarda en `uso.md`.

## 6. Lo que no hacemos (y por qué)

- **Grafo Neo4j/FalkorDB:** un servicio más, memoria del Mac, sin ganancia a esta escala. Las relaciones viven en `afirmaciones`.
- **Vectores en la nube:** sus datos saldrían del Mac para nada.
- **Modelo grande local «para que clasifique mejor»:** primero entrada corta + juez semanal; se mide. Si aun así falla, se sube a `qwen3:8b`.
- **Extracción de `yo/` o `negocio/` con APIs gratuitas:** entrenan con los datos.
- **Dos sistemas de memoria a la vez:** la recomendación común de los comparativos; por eso `boveda/memoria/`, `inteligencia/memoria.py` y el MCP `memoria` se apagan (F1.4).
- **Sala vectorial de Rumbo:** F5, cuando haya afirmaciones que mapear.

## 7. Orden para la terminal (reemplaza F1.3–F1.6 del plan)

| Paso | Qué | Listo cuando | Tamaño |
|---|---|---|---|
| **F1.3 Salida con compuerta + router + métricas** | `anotar(tipo)`; confirmación Telegram para `yo/`; hook de prompt usa `indice.db` con umbral y presupuesto (≤600 tokens) y registra en `consultas`; hook `PostToolUse` sobre WebSearch; `uso.md` nocturno | una sesión deja una investigación con fuentes y la siguiente la usa sin web; `uso.md` muestra consultas, aciertos y webs evitadas | L |
| **F1.4 Ingesta unificada + extracción en dos etapas** | bóveda → `nucleo/ingesta/`; etapa A (API gratis → local) y etapa B (local, entrada corta); entidades, relaciones, links citados; trozos contextualizados; PDF; apagar memorias duplicadas | un reel compartido termina enriquecido en `mente/mundo/fuentes/` con entidades y `frentes` no vacío; `preguntar` lo encuentra | L |
| **F1.5 Embeddings + reordenador + evaluación** | `qwen3-embedding:0.6b`; RRF; reranker local; `nucleo/evaluar.py` con conjunto sintético; decisión por número | tabla de recall@5 antes/después en `uso.md`; se adopta solo lo que gana | M |
| **F1.6 Afirmaciones bitemporales + hallazgos** | tablas `entidades/alias/afirmaciones/hallazgos`; invalidación; noche escribe `mundo/hallazgos/<frente>.md`; `hallazgos(frente)` y `entidad(nombre)` en el MCP; `preguntar` prefiere hallazgos | `preguntar("INVERZA")` devuelve un hallazgo cruzado con sus contradicciones; una afirmación T4 queda invalidada por una T1 | L |
| **F1.7 Sueño semanal + juez** | reorganización dominical; caducidad por tipo; procedimientos desde lecciones; `claude -p --model haiku` califica 20 extracciones y añade 5 ejemplos al prompt local; `git push` privado nocturno | `uso.md` trae la nota del juez y la precisión de citas sube semana a semana | M |
| **F1.8 Ventana viva** | Bases/Dataview: repos por veredicto, fuentes por estatus, afirmaciones contradichas, hallazgos por frente, supuestos vencidos | las tablas se llenan solas en Obsidian | S |

F2 (Rumbo v2) consume `hallazgos` y `afirmaciones`: la teoría de juegos de F2.4 corre sobre esa tabla, no sobre notas sueltas.

## 8. Riesgos y preguntas abiertas

- **RAM del Mac mini:** no está medida en el repo. `whisper` corre en CPU int8 y el modelo es 4b: si hay 16 GB o menos, `qwen3:8b` no cabe con Whisper a la vez. Primera tarea de F1.4: `sysctl hw.memsize` y decidir.
- **Límites de Gemini gratis no son oficiales** y cambian; por eso la cascada API → local y la marca `extraccion:` en cada nota.
- **Resolución de entidades** es el punto débil de todos (lo dicen los evaluadores): se hace conservadora y las dudas quedan en un archivo visible en Obsidian, no se adivina.
- **Reddit** sigue devolviendo 403 sin cuenta de API; **Instagram** no permite leer comentarios sin sesión: lo de «comenta X» lo hace él, y la bóveda solo le dice cuáles valen la pena.

## Fuentes

- Anthropic, *Effective context engineering for AI agents*: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, *Introducing Contextual Retrieval* (−49 % fallos con híbrida contextual, −67 % con reranking): https://www.anthropic.com/news/contextual-retrieval
- Cambios del nivel gratuito de Gemini (Flash-Lite ~500/día no oficial; entrena con los datos): https://agentdeals.dev/gemini-api-pricing-changes
- Niveles gratuitos de APIs de LLM, leídos 2026-10-16: https://benchlm.ai/md/free-tier.md
- Plan gratuito de Mistral (límites no publicados): https://costbench.com/software/llm-api-providers/mistral-ai/free-plan/
- Mem0 vs Letta vs Zep vs Cognee 2026 (licencias, local, debilidades): https://mcp.directory/blog/mem0-vs-letta-vs-zep-vs-cognee-2026
- Estado de la memoria de agentes 2026, declarado vs observado (el autor vende un competidor): https://dev.to/gaurav_dadhich/the-state-of-ai-memory-in-2026-claimed-vs-observed-1n94
- Graphiti como memoria de agentes, evaluación práctica: https://codex.danielvaughan.com/2026/03/30/graphiti-agent-memory-store/
- Letta, guía de sleep-time agents: https://forum.letta.com/t/sleeptime-agents-for-memory-consolidation-best-practices-guide/154
- Qwen3 Embedding y Reranker en Ollama: https://glukhov.org/rag/embeddings/qwen3-embedding-qwen3-reranker-on-ollama/
- Kuzu archivado (oct-2025): https://www.theregister.com/2025/10/14/kuzudb_abandoned/

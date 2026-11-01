# Plan final · terminar Remi (30-oct-2026)

Estado vivo. Una fase a la vez; ninguna empieza sin el «listo cuando» de la anterior. El plan del 4-oct está en `docs/archivo/`. Diseños de referencia: `docs/diseno/boveda-v2-mente.md`, `docs/diseno/filtro-de-la-verdad.md`, `docs/revision/2026-10-30-sintesis.md`, `docs/prompts/no-inventar-la-rueda.md`.

## Qué es «terminado»
1. Cualquier Claude (Code, escritorio, Telegram) arranca sabiendo quién es Juan Camilo, su negocio, sus metas, recursos y restricciones, sin que se lo cuente, y le devuelve a la mente lo que aprende.
2. La bóveda es una sola mente (`mente/`), con Obsidian como ventana y un índice regenerable; ahorra tokens de forma medida.
3. Rumbo responde `/rumbo` con una ficha honesta que termina en un experimento dimensionado, y aprende de lo que pasa.
4. Todo corre solo en el Mac (servicios, noche, copias, campo) siete días sin tocarlo, y se puede restaurar.
5. La fábrica produce una cotización real y una entrega real con revisión y portero.
6. Nada de esto viola las 6 leyes ni mete datos personales en git.

## Decisiones tomadas el 30-oct (cambian si Juan Camilo lo dice)
- `mente/` vive en el disco interno (`~/proyectos/mente`, git privado, restic); en ORGANIC solo audio y caché.
- Claude escribe directo en `aprendido/`; lo que diga de él (`yo/`) espera su «sí» por Telegram; lo del mundo exige URL o entra como hipótesis.
- Obsidian con tablas vivas (Dataview o Bases).
- Rumbo v2 según la revisión: contador de tiros, experimentos con potencia mínima, diario de micro-predicciones, tasas base propias, sensibilidad simple; sin ranking de 60 nichos ni Kelly ni futuros a 12 meses. El espacio de configuraciones (yo fijo × modelo, nicho, geografía, canal, precio) se construye, pero solo con datos T1/T2.
- La fábrica arranca por cotizar y proponer, no por código.
- Nada entra como hecho sin fuente; lo que Claude concluye es hipótesis o decisión con fecha.
- **Cero etiquetado manual.** La bóveda titula, resume y clasifica sola (Ollama local). Su calidad se mide sin Juan Camilo: acuerdo entre reglas y modelo, cuántas veces `preguntar` y el hook sirven cada nota, y si Claude la cita. `/etiquetar` se retira. Nada de prueba entra al vault: las pruebas corren contra `_archivo/ejemplos/`.

## Reglas
Un prompt = una tarea = un commit. Pruebas donde duele. `conocimiento/` y `mente/` nunca al repo público. Diseño antes que pantalla. Cada fase cierra con un «listo cuando» verificado por Juan Camilo o por Claude en la app, no por la terminal que lo hizo.

## Quién hace qué
- **Terminal (Claude Code en el Mac):** el código, las pruebas, las migraciones, las mediciones locales.
- **Claude en la app (esta conversación):** diseño, revisión de lo que entrega la terminal, prompts de cada paso, verificación cruzada.
- **Juan Camilo:** decisiones, comandos que tocan `~/.claude` y launchd, pruebas desde el teléfono, exportar su historial de Fiverr, el token de Telegram, el repo privado.

---

## F0 · Cerrar lo abierto (hoy, ~1 h)
- [ ] Hook de prompt instalado: `python3 ~/proyectos/remi/scripts/instalar_hook_claude.py --aplicar` (él).
- [ ] MCP `remi` en Claude Desktop (él, pegar el JSON del README).
- [ ] Servicio semanal de campo cargado (él, comando del README de la bóveda).
- [ ] `python3 campo.py --tema "ai receptionist"` corre con RemoteOK, Remotive y HN respondiendo (él pega la salida).
**Listo cuando:** una pregunta en Claude Code trae contexto de la bóveda; el campo deja una nota con al menos dos fuentes.

## F1 · La mente (terminal, ~5 días) — arquitectura en `docs/diseno/boveda-v3-frontera.md`; protocolo en `boveda-v2-mente.md` §3
1. **Estructura y mudanza (M).** Hecha el 30-oct.
2. **Un índice (M).** Hecha el 30-oct. Falta que el hook de prompt lo use (va en F1.3).
3. **Salida con compuerta + router + métricas (L).** `anotar(tipo)`; la noche regenera `docs/MAPA.md` y `mente/MAPA.md` (`scripts/mapa.py`); confirmación por Telegram para `yo/`; el hook de prompt usa `indice.db` con umbral y presupuesto (≤600 tokens) y registra cada consulta; hook `PostToolUse` sobre WebSearch/WebFetch; la noche escribe `uso.md` (consultas, aciertos, webs evitadas, tokens). *Listo cuando:* una sesión deja una investigación con fuentes y la siguiente la usa sin web, y `uso.md` lo muestra.
4. **Ingesta unificada + extracción en dos etapas (L).** Bóveda → `nucleo/ingesta/`; etapa A (texto público: OpenRouter `:free` → Gemini gratis → local) y etapa B (relevancia por frente: OpenRouter `:free` con entrada corta; local solo con datos propios); entidades, relaciones y links citados; trozos contextualizados; **documentos con `markitdown`** (PDF, DOCX, PPTX, XLSX) y el bot de Telegram acepta archivos, no solo links; apagar `boveda/memoria/`, `inteligencia/memoria.py`, `contexto.yaml`, MCP `memoria`. Sin cargar la RAM del Mac (decisión 30-oct). *Listo cuando:* un reel compartido termina enriquecido en `mente/mundo/fuentes/` con entidades y `frentes` no vacío.
5. **Embeddings + reordenador + evaluación (M).** `qwen3-embedding:0.6b`; RRF; reranker local; `nucleo/evaluar.py` con conjunto sintético (2 preguntas por nota) + consultas reales + los 12 casos semilla de `nucleo/evaluacion/casos.jsonl` (del lote del 30-oct); se adopta solo lo que sube recall@5 sin subir tokens. *Listo cuando:* la tabla antes/después está en `uso.md`. **Deudas de F1.4c, también de F1.5:** (a) `pensar.py` aún abre `memoria_mcp.py` por su cuenta para `claude -p`; apuntarlo al MCP `remi` y retirar `memoria_mcp.py`. (b) El orquestador de inteligencia de la bóveda no corre sin `contexto.yaml`; reconectarlo a `mente/negocio/`.
6. **Afirmaciones bitemporales + hallazgos (L).** Tablas `entidades/alias/afirmaciones/hallazgos` en `indice.db`; invalidación T1 sobre T4; la noche escribe `mundo/hallazgos/<frente>.md` con el formato de `mundo/hallazgos/2026-10-30-instagram-35-links.md` (hecho a mano); `hallazgos(frente)` y `entidad(nombre)` en el MCP; `preguntar` prefiere hallazgos. *Listo cuando:* `preguntar("INVERZA")` devuelve un hallazgo cruzado con sus contradicciones.
7. **Sueño semanal + juez (M).** Reorganización dominical; caducidad por tipo (decisiones y hechos sobre él no caducan); procedimientos desde lecciones repetidas; `claude -p --model haiku` califica 20 extracciones y añade 5 ejemplos al prompt local; `git push` nocturno a repo privado. *Listo cuando:* la precisión de citas sube semana a semana en `uso.md`.
8. **Ventana viva (S).** Bases/Dataview: repos por veredicto, fuentes por estatus, afirmaciones contradichas, hallazgos por frente, supuestos vencidos; `/estado`, `/repos`, `/campo <tema>` por Telegram sin modelo. *Listo cuando:* las tablas se llenan solas.

## F2 · Rumbo v2 (terminal, ~2 días) — detalle en `docs/revision/2026-10-30-sintesis.md`
1. **Cifras propias (S).** Él exporta Fiverr (y Upwork/Malik si se puede); la terminal calcula mediana, p90, $/día, concentración, tiempos entre órdenes → `mente/negocio/cifras-propias.md`. *Listo cuando:* `estado_vivo` cita su propia distribución, no «$500 al mes».
2. **Contador de tiros y diario (M).** Una línea por contacto (canal, fecha, respuesta, cotización, pago) por Telegram; micro-predicción diaria con probabilidad y vencimiento; resultado al vencer; Brier a las 30. *Listo cuando:* 7 días de registro sin fricción.
3. **Experimentos (M).** Hipótesis, métrica, umbral de éxito, umbral de abandono, plazo, tope de horas; n ≥ 3/tasa esperada; aviso al vencer; resultado como evidencia T1. *Listo cuando:* un experimento real cerrado y registrado.
4. **`/rumbo` (L).** Marco (unidades propias y techo de capacidad), espacio de configuraciones con clases de referencia T1/T2, sensibilidad simple (qué parámetro cambia al líder), **teoría de juegos sobre los hallazgos** (`juego.py`: por cada opción, los otros jugadores y su mejor respuesta si entra; la ventaja que no copian rápido), ficha de una tarjeta que termina en experimento; por Telegram y ventanita. La cara: una tarjeta a la vez (página «Siete Rumbos»); la Sala vectorial va en F5. *Listo cuando:* `/rumbo ¿qué nicho?` devuelve una ficha con lo que más pesa que no sabe y un experimento dimensionado.

## F3 · Producción (terminal + él, ~2 días)
- Repo privado antes de cualquier push; token de Telegram rotado; llaves solo en Ajustes.
- Los 10 servicios cargados y el vigía como proceso aparte; logs rotados; restic con restauración de prueba hecha y documentada.
- Medición de tokens por sesión (`uso.md`) y semana de uso real con bitácora de fallos.
**Listo cuando:** 7 días sin intervención manual; una restauración probada; `git log -p` sin un solo secreto.

## F3b · Ventanita de foco y notificaciones (terminal, ~2 días) — pedido de JC el 30-oct
Primero **auditar** panel y ventanita pantalla por pantalla (qué hace, qué le falta, qué está roto) y escribir `docs/auditoria/panel-2026-10-30.md`; después construir:
1. **Foco tipo BeFocus (M).** Escribir una tarea + minutos; cuenta regresiva visible en la **barra de menú** (icono de bandeja de Tauri con el tiempo restante como título); al terminar, pausa y «¿terminaste?». BeFocus ya está instalado y corriendo en su Mac: se copia su manera (tarea, tiempo, contador arriba), no se reemplaza a la fuerza.
2. **Que Remi lo inicie (S).** Remi propone la tarea de la hora (del estado vivo) y arranca el temporizador con un toque; sin él, JC lo olvida.
3. **Parte de la mañana (S).** `partes/manana.py` a las 7:00 por Telegram y ventanita: cuerpo (si hay dato), cifras propias del negocio, agenda del día y **una** tarea con botón «Empezar 25 min» que arranca el foco. Modelo: la nota DeNlN0gAKTG. La auditoría del panel usa `aprendido/procedimientos/calidad-web.md` como rúbrica.
4. **Notificaciones (M).** La ventanita se superpone a las demás ventanas solo cuando Remi tiene algo que decir (aviso, vencimiento, aprobación); un canal, sin cadena de culpa.
*Listo cuando:* JC inicia una tarea de 25 min con un toque, ve el contador en la barra de arriba y recibe el aviso final sin abrir nada.

## F4 · La fábrica (terminal, ~3 días) — según el video y `nucleo/coding.py`
1. **Cotizar y proponer (L).** Entrada por Telegram (brief del cliente) → `grill-me` (una pregunta a la vez) → spec que consulta `mente/` y pasa la compuerta «buscar antes de construir» (`preguntar` + fichas de repos) → propuesta con precio ancla y contrato Omniway → revisor con contexto limpio → portero (reglas, no agente) → PDF listo para enviar. *Listo cuando:* una cotización real sale en menos de 30 min de su tiempo.
2. **Entregar software (L).** Spec → builder con TDD → revisores (seguridad con `procedimientos/seguridad-apps-ia.md`, UX con `procedimientos/calidad-web.md`, código) → aprobador → portero con hooks → PR; trazas en SQLite. *Listo cuando:* una entrega real pasa por la fábrica y se cobra.

## F5 · Después (no antes)
La Sala (mapa vectorial) cuando `mente/` tenga datos de campo y decisiones; el investigador semanal que llena `mundo/`; marketing y ventas; la vara contra Grok Bot medida como oportunidades por semana que el sistema encontró y él no.

## Registro
- 1-nov: **Definición Remi/bóveda y estado vivo en Remi.** Remi = agente (Jarvis); bóveda = departamento (entrada, memoria, salida por MCP); ver CLAUDE.md. La «ficha personal viva» ya existía: es `vida.construir_estado` (el hook la mete en Claude Code). Lo que faltaba: (a) un bloque **Decisiones vigentes** (≤90 días, de `aprendido/decisiones/`), (b) que **Remi mismo** la reciba: `pensar.instrucciones_con_indice` ahora antepone el estado al carácter (Telegram y ventanita), (c) las 9 decisiones de oct-nov anotadas como notas de decisión. Pendiente de Juan Camilo: confirmar `yo/*.md` (siguen `estatus: por-confirmar` del 27-oct) y actualizar frentes. **Newsletter propia** (bóveda `newsletter.py`, `plan_newsletter.md`): 47 feeds + 37 canales de YouTube, diaria y semanal, sin verificar aún con feeds reales. Decisiones: dos MCP solo con el primer agente externo; código de la bóveda al disco interno después de la newsletter.
- 31-oct: **F1.5 hecha desde la app (falta medirla en el Mac).** `config/mente.json` fija el modelo de embeddings (`qwen3-embedding:0.6b`, 1024 dim; antes `nomic-embed-text` 768) y `indexar.conectar` lo registra en la tabla `meta`: si cambia, borra `notas_vec`, la recrea con las dimensiones nuevas y deja las notas sin vector para que `actualizar` las recalcule (lo mismo en `remi.db`). Las preguntas se vectorizan con instrucción delante (`embed_consulta`), las notas sin ella. `reordenar.py`: reordenador cruzado local (`BAAI/bge-reranker-v2-m3`, `sentence-transformers`), apagado por defecto y con caída silenciosa a la híbrida. `indexar.buscar(modo=texto|vector|hibrida|rerank)`. `evaluar.py` mide recall@5, MRR y tokens con los casos semilla, las consultas reales (el hook ahora guarda el id que Claude leyó: `mcp__remi__leer:<id>`) y preguntas sintéticas (`--generar N`, motores gratis, solo notas públicas); escribe `mente/evaluacion.md` con veredicto ADOPTAR/no adoptar. 9 pruebas en `nucleo/pruebas/test_f15.py`. **Queda para la terminal:** `ollama pull qwen3-embedding:0.6b`, `python3 nucleo/indexar.py` (reconstruye vectores), `python3 nucleo/evaluar.py --generar 40` y, si se quiere, `pip install sentence-transformers` + `reordenador.activar: true`. Las dos deudas de F1.4c **no** se tocaron a ciegas: `memoria_mcp.py` lo importa `remi_mcp.py` (anotar_leccion/buscar_lecciones), lo usan ~8 pruebas y `pensar.py` depende de `mcp__memoria__leer/guardar`; retirarlo es un refactor que debe correr con pytest en el Mac.
- 31-oct: **F1.4c hecha.** Las 38 notas de la bóveda viven en `mente/mundo/fuentes/<fuente>/` con `nivel: oro|procesado|raw` (las de campo conservan su `nivel` T1–T4); `boveda.destino_de`, `enriquecer`, `pedidos`, `repos`, `campo`, `etiquetar`, el hook y el tablero (`mente/mundo/dashboards/fuentes.md`) leen y escriben allí; `indexar.py` ya no tiene segunda raíz (67 notas, ninguna `boveda/…`). Apagados y archivados en `boveda/_archivo/f14c/`: `memoria/`, `inteligencia/memoria.py`, `contexto.yaml`. El MCP `memoria` se desregistró; `anotar_leccion` y `buscar_lecciones` pasaron al MCP `remi`. **Queda:** `pensar.py` aún abre `memoria_mcp.py` por su cuenta para `claude -p` (estante en SQLite); el orquestador de inteligencia de la bóveda no corre sin `contexto.yaml` (hay que reconectarlo a `mente/negocio/`); `pip install 'markitdown[pdf,docx,pptx,xlsx]'` en la bóveda no se hizo.
- 31-oct: F1.4 parte app hecha (bóveda `motores.py`, `documentos.py`, `enriquecer.py` en dos etapas con entidades/relaciones/links; Telegram acepta archivos). **Queda para la terminal (F1.4c):** mover las notas de la bóveda a `mente/mundo/fuentes/` con `nivel` en frontmatter, apagar `boveda/memoria/`, `inteligencia/memoria.py`, `contexto.yaml` y el MCP `memoria`, un solo entorno; `pip install 'markitdown[pdf,docx,pptx,xlsx]'` en la bóveda.
- 30-oct: F1.3 construida desde la app (commit de hoy): router del hook sobre `indice.db` con umbral y presupuesto (stdlib, sin sqlite-vec), hook PostToolUse de métricas, `anotar(tipo, fuentes)` con compuerta, `metricas.py` + `uso.md`, noche regenera mapas y pasa confirmaciones a `yo/confirmado.md`. **Falta verificar en el Mac:** `./scripts/recargar.sh`, reinstalar hooks con `--aplicar`, y que `uso.md` aparezca tras la primera noche.
- 30-oct: los 35 links de Instagram se convirtieron en decisiones (v3 §7b): mapas + hook (hecho), markitdown y archivos por Telegram (F1.4), casos semilla (F1.5), formato de hallazgo (F1.6), parte de la mañana (F3b), compuertas y rúbricas de la fábrica (F4).
- 30-oct: F3b (ventanita de foco y notificaciones) añadida al plan. Fábrica (F4): decidido que será cliente de `mente/` por el MCP `remi`, sin memoria propia y sin meterse en el núcleo de Remi; el material va en `mente/mundo/fabrica/`.
- 30-oct: `vision.py` en la bóveda: videos sin voz y posts de imágenes se ven con un modelo `:free` de OpenRouter; caption del post en toda nota. Falta que JC ponga `OPENROUTER_API_KEY` en `_sistema/.env` y reintente los fallidos.
- 30-oct: arquitectura v3 (frontera, gratis) escrita en `docs/diseno/boveda-v3-frontera.md`; F1.3–F1.8 reescritos. F2.4 corre sobre `afirmaciones` y `hallazgos`.
- 30-oct: plan reescrito tras la revisión externa y el diagnóstico de la bóveda. F0 abierta.
- 30-oct: F1.1 entregada por la terminal: `~/proyectos/mente` con `conocimiento` como enlace. Falta verificar que Obsidian abre el vault.
- 30-oct: F1.2 entregada por la terminal: `nucleo/indexar.py` y `mente/indice.db`; `preguntar` sin cuerpo, `leer(id)`; oficios restaurados en `mente/oficios/`. Falta que el hook de prompt use el índice y que la noche lo actualice (F1.3).

## Cómo se arranca cada paso en la terminal
«Lee `docs/PLAN-FINAL.md` y el diseño que cita. Haz solo el paso F<n>.<m>. Antes de tocar código, di en 5 líneas qué vas a cambiar y qué prueba lo demuestra. Un commit por tarea. Al final: qué quedó, qué no, cómo lo verifico desde mi teléfono o desde Obsidian, y qué anotaste con `anotar_leccion`.»

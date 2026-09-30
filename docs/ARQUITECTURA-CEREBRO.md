# El cerebro de Remi — arquitectura final

> Salió del test del 29-sep-2026 con Juan Camilo. Manda sobre cualquier encargo anterior
> que la contradiga. Claude Code: leé esto antes de tocar `nucleo/pensar.py` o la memoria.

## 1. Lo que Juan Camilo quiere (el test)

| Pregunta | Respuesta | Qué obliga en la arquitectura |
|---|---|---|
| 11 p. m., 3 h en Malik, entrega mañana con Alfonso | **Me interrumpe y me frena** | Remi observa sin que le hablen: proyecto activo, hora, entregas. Motor de iniciativa. |
| ¿Qué recuerda? | **Todo; él decide qué importa** | Consolidación automática: nadie tiene que decir «guardá esto». |
| Velocidad por voz | **Elegir entre rápido / equilibrio / inteligente** desde la ventanita | Tres cerebros detrás de un selector (flechita junto al punto). |
| ¿De dónde sabe de los proyectos? | **Obsidian y Notion, con cohesión** | Un mismo «libro» vive en los dos, con el mismo id. |
| Memoria | **Como una persona: títulos siempre presentes, profundiza al tirar del hilo, carga como un videojuego; nunca «20 % del 70 %»** | Memoria por niveles de detalle + asociación vectorial + conversación que se resume, no que se corta. |
| Desacuerdo | **Insiste con argumentos** | El carácter lo permite; el tono no puede volverse regaño (ley 3). |
| Interrupciones | **Máximo 5 al día** | Presupuesto de silencio: 90 min entre dos, nunca mientras escribe. |
| Alcance | **Trabajo y clientes · finanzas · cuerpo y salud · aprender · negocios y planes a corto y largo plazo** | Un libro por área además de uno por proyecto. |

## 2. La idea central: memoria por niveles de detalle (como un videojuego)

Un juego no carga el mapa entero: carga en alta resolución lo que tenés cerca y en baja lo
lejano, y mientras caminás va trayendo lo que viene. Remi hace lo mismo con lo que sabe.

| Nivel | Qué es | Cuándo está en la cabeza | Tamaño aprox. |
|---|---|---|---|
| **0 · Identidad** | Carácter + quién es Juan Camilo + las 6 leyes | Siempre (cacheado) | ~1,5 k tokens |
| **1 · La mente** | Un **título** + «con qué me quedé» + 3–6 palabras clave por libro. Jerárquico: áreas y proyectos arriba; temas y episodios debajo | Siempre la capa de arriba; la de abajo solo del proyecto activo | ~2–3 k |
| **2 · El resumen del libro** | Lo esencial de un libro en 200–400 tokens: estado, decisiones, números, pendientes, próxima acción | Cuando la conversación toca ese libro, o se precarga (ver §4) | ~300 c/u |
| **3 · El libro entero** | La nota completa de Obsidian o la conversación original | Rara vez: solo si hace falta un detalle exacto | lo que mida |

**Recordar = subir de nivel.** «¿Te acordás de lo de Alfonso?» → la mente ya tiene el título
(nivel 1) → baja el resumen (nivel 2) → contesta. Si le preguntás la fecha exacta de la
segunda cuota, abre el libro (nivel 3). Una persona hace eso mismo.

**Olvidar = bajar de nivel, nunca borrar.** Lo que no se toca en semanas baja de la capa de
arriba de la mente, pero el libro sigue ahí y se puede volver a encontrar.

## 3. «¿Te acordás de aquel asunto?» — la asociación

Cuando la pista es vaga («lo del cliente que desconfiaba», «aquello de las regiones»), el
título exacto no aparece por palabras. Para eso está la **memoria vectorial**, con un papel
preciso: **encuentra qué libro es, no trae el libro.**

- Cada libro y cada episodio tiene un vector (embedding) de su título + resumen.
- Ante un mensaje, se buscan los 3–5 libros más parecidos y se suman a la mente como
  «esto quizá tenga que ver». El modelo decide si baja alguno.
- Vectores **locales y gratis**: modelo de embeddings multilingüe en Ollama (`bge-m3` o
  `nomic-embed-text`), guardados en el mismo SQLite con `sqlite-vec`. Nada sale del Mac.
- Palabras clave como segundo camino (exactas, instantáneas): nombres propios, montos,
  clientes.

## 4. Precarga: cargar lo que viene antes de que lo pidas

Antes de cada respuesta, y cada tanto en segundo plano, Remi mira dónde estás:

- **Proyecto activo**: bloque abierto en Remi, app y ventana en primer plano (título de
  ventana, repo abierto), últimos turnos.
- **Tiempo**: hora, día, entregas y cuotas próximas (Notion / calendario).

Con eso **precarga el nivel 2** del proyecto activo y de lo que vence pronto. Por eso cuando
preguntás, ya está: no hay que ir a buscarlo. Es también lo que alimenta la iniciativa (§8).

## 5. La conversación: se resume, nunca se corta

Nada de ventana deslizante que tira lo viejo («20 % del 70 %»). La memoria de trabajo de una
conversación tiene dos partes:

1. **Los últimos ~10 turnos, literales.**
2. **Un resumen vivo de todo lo anterior de esa misma conversación**: decisiones, datos,
   pendientes, tono. Cada vez que un turno sale de los 10, el resumen se actualiza
   (lo hace el modelo local, gratis).

Así una charla de dos horas cabe entera en ~3 k tokens sin perder nada importante.

## 6. Consolidación: lo que hace la mente mientras «duerme»

Nadie dice «guardá esto»: Remi decide (respuesta del test).

- **Al cerrar una conversación** (60 min sin turnos): se escribe un **episodio**: título,
  «con qué me quedé», palabras clave y vector; el cuerpo son los turnos. Si hubo datos nuevos
  de un proyecto, **se actualiza el resumen del libro de ese proyecto** (nivel 2) y su nota
  en Obsidian. Conversaciones triviales no dejan episodio.
- **Cada noche**: se reordena la mente (lo usado sube, lo olvidado baja), se fusionan
  episodios repetidos, se sincroniza Notion.
- La consolidación la hace el **modelo local** (gratis); Claude solo si el resumen es de un
  proyecto con plata en juego.
- Juan Camilo puede corregir cualquier cosa: edita la nota en Obsidian o Notion y la próxima
  sincronización la toma como verdad.

## 7. Dónde vive cada cosa (la cohesión Obsidian + Notion)

| Lugar | Rol | Qué guarda |
|---|---|---|
| **Obsidian** (bóveda en disco) | **Los libros**, fuente de verdad del conocimiento | Una nota .md por proyecto, área y episodio importante, con frontmatter `id`, `titulo`, `resumen`, `claves`, `nivel`. Legible y editable por él. Remi la escribe. |
| **SQLite** (`remi.db`) | **La mente y la maquinaria**: rápida | Índice de la mente, vectores, turnos, tareas, sesiones, bandeja, nudges. Se reconstruye desde Obsidian si hace falta. |
| **Notion** | **La vitrina y la operación** | Lo que él busca y reporta: proyectos con estado y próxima acción, clientes, entregas, cobros. Remi lo actualiza; lo que él cambie en Notion vuelve. |

**El pegamento es un solo `id` por libro**, el mismo en el frontmatter de Obsidian, la fila de
SQLite y la página de Notion. Un libro, tres vistas.

## 8. Cómo actúa: iniciativa con presupuesto

- **Interrumpe y frena** cuando lo medido lo justifica: entrega mañana y estás en otra cosa;
  3 h sin pausa; un cobro que vence; algo que prometiste y no apareció.
- **Presupuesto**: máximo 5 al día, 90 min entre dos, nunca mientras escribís, dos «ahora no»
  seguidos del mismo tipo lo callan hasta mañana.
- La decisión de interrumpir es de **reglas medidas** (baratas); el modelo solo redacta la
  frase. Así no gasta límite de Max vigilando.

## 9. Cómo piensa: tres cerebros y quién hace qué

| Modo (selector en la ventanita) | Cerebro | Para qué |
|---|---|---|
| **Rápido** | Claude Haiku por Max (o local) | Diálogo ágil, confirmaciones, cosas simples. 1–2 s. |
| **Equilibrio** (por defecto) | Claude Sonnet por Max | Casi todo. 3–5 s. |
| **Inteligente** | Claude Opus por Max, con razonamiento | Decisiones, estrategia, planes. 8–15 s. |

**Chips por proveedor (30-sep, plan de robustez):** Claude (al frente, siempre; Haiku/Sonnet/Opus
según el nivel), Groq (gratis: Llama 4, Kimi K2), OpenRouter (DeepSeek Flash en equilibrio,
DeepSeek V4-Pro en inteligente y Prompt, respaldo Kimi K2 / Qwen3-Coder; `models` con caída
automática y `provider.sort=price`), Venice (manual, pago), Ollama (sin red). Los modelos viven
en `config/motores.json`, nunca en código. **Respaldo del cerebro**: si Max devuelve límite o
`claude -p` falla, el turno se reintenta por OpenRouter · DeepSeek V4-Pro y la respuesta lleva
`motor_usado`; la ventanita muestra el chip real.

**La trastienda es gratis y ya no la hace el modelo más flojo:** resumen vivo, claves, títulos
de episodios y consolidación corren en Groq · Kimi K2 → OpenRouter · DeepSeek Flash → Ollama.
Los embeddings siguen locales (Ollama). Así el límite semanal de Max se gasta en la voz de Remi,
y los Estados de la bóveda los escribe un modelo serio, con la verificación mecánica de siempre.

## 10. Lo que viaja en cada llamada (presupuesto de contexto)

| Pieza | Tokens aprox. |
|---|---|
| Nivel 0 (identidad) — cacheado | 1.500 |
| Nivel 1 (mente, capa de arriba + temas del proyecto activo) — cacheado | 2.500 |
| Asociados por vector (títulos) | 200 |
| Nivel 2 precargado (proyecto activo + lo que vence) | 600–1.200 |
| Conversación: resumen vivo + últimos 10 turnos | 1.500–3.000 |
| **Total típico** | **~6–8 k**, la mitad cacheada |

Si algún día la mente no entra en 3 k, se sube un nivel de jerarquía (áreas → proyectos →
temas), no se tira nada.

## 11. Orden de construcción

1. **3a · Cerebro v1**: piensa siempre, 3 modos, carácter desde archivo, conversación con
   resumen vivo, libros de proyecto en la mente (niveles 0–2). *Con esto ya se puede probar.*
2. **3b · Ventanita mínima**: X para cancelar, selector de modo (flechita al acercar el mouse
   al punto), diálogo que no corta, respuesta que se queda, auditoría de diseño.
3. **3c · Memoria viva**: bóveda de Obsidian como fuente, consolidación de episodios, vectores
   locales, reordenamiento nocturno.
4. **3d · Notion**: espejo de proyectos, clientes, entregas y cobros, en los dos sentidos.
5. **3e · Precarga e iniciativa**: proyecto activo por app en primer plano, entregas, reglas de
   interrupción con presupuesto.
6. **3f · Banco de pruebas**: mismas conversaciones contra los modos; medir recuerdo, latencia y
   gasto de Max.

## 12. El sistema de trabajo: todo habla el mismo idioma (29-sep, noche)

Principio: **Remi no depende de que Juan Camilo se acuerde de actualizarlo** (ley 2: mecánico,
sin decidir). Las herramientas le avisan solas y Remi les devuelve el contexto.

**Una fuente, todos la leen.** La bóveda `~/proyectos/remi-mente` es la verdad; Notion es su
vitrina. El MCP de memoria de Remi se registra **global** en Claude Code (scope user) y en la
app de escritorio de Claude (servidor MCP local). Cualquier Claude lee y guarda en la misma
memoria: no hay copias que sincronizar.

**Entradas automáticas:**
| Evento | Mecanismo | Qué hace Remi |
|---|---|---|
| Commit en cualquier repo | hook global de git (`core.hooksPath`) → `POST /evento` | Actualiza el resumen del proyecto (nivel 2) con el modelo local |
| Fin de sesión de Claude Code | hook `SessionEnd`/`Stop` global → `POST /evento` con el transcript | Episodio: qué se hizo, decisiones, pendientes, primer paso de mañana |
| Inicio de sesión de Claude Code | hook `SessionStart` global → devuelve contexto | Inyecta la ficha: dónde quedaste, decisiones, próximo paso |
| Conversación de Claude web/celular | pegarla en la ventanita | Episodio comprimido (3c) |
| Excepción | «guardá esto» / «olvidá esto» | Manual |

**Proyecto = carpeta.** Cada libro de proyecto lleva `ruta:` en el frontmatter; así un commit
o una sesión en esa carpeta cae en su libro.

**Lo que Remi suma que Claude no hace (el norte TDAH):**
- «¿Dónde quedé?»: al abrir un proyecto, 3 líneas + próximo paso (retomar es lo más caro).
- Cerrar con el primer paso de mañana: 5 minutos, escrito al terminar (ley 3).
- Dispersión: commits en 3 proyectos en una hora → frena (iniciativa, §8).
- Tiempo real por proyecto, de commits + sesiones (ley 1).
- Promesas: «le mando a Alfonso el viernes» se extrae y se recuerda.

## 13. Los oficios: lo que Remi sabe hacer (30-sep, 1 a. m.)

La memoria (§2) guarda lo que pasó. Los **oficios** guardan cómo se hace. Son libros del mismo
estante, con `tipo: oficio`, en `remi-mente/oficios/`: título + resumen + claves siempre en la
mente (nivel 1); el cuerpo se abre cuando la conversación toca el tema (nivel 2/3), y la
asociación por vectores (§3) los trae aunque no los nombres.

| Oficio | Papel en el cerebro |
|---|---|
| claude-code | Remi es la **puerta de los prompts**: conoce el estado del proyecto (libro) y elige pieza, modelo y forma. Se refresca cada semana desde el changelog oficial (tarea nocturna del domingo). |
| prompting | Forma fija de todo encargo. Sin «listo cuando» no sale. |
| stack | Convenciones + **libro de errores** (episodios con `fuente: error`: síntoma, causa, cura), alimentado desde el cierre de sesiones de Claude Code. Se consulta antes de proponer un arreglo. |
| proyectos-sop | Propio vs cliente, paso a paso. Cada libro de proyecto lleva `paso_sop:` para saber dónde está. |
| clientes + mi-voz | «Me escribió X» → lectura (teoría de juegos), riesgos, respuesta en su voz, guardarraíles. **Remi nunca envía.** Mi-voz se construye con mensajes reales. |

**Aprender de las correcciones**: cuando Juan Camilo dice «no, así no», Remi propone una regla
de una línea para el oficio correspondiente y la guarda con su «sí». Es el único camino por el
que los oficios cambian solos.

**Banco de pruebas (3f) ampliado**: no compara solo modelos; compara configuraciones (con/sin
oficio, nivel, modelo) sobre 10 tareas reales de Juan Camilo. Métricas: tokens, tiempo, nota
1–5 suya. Gana el dato.

**Orden actualizado**: 3a ✅ · 3b ✅ · 3c ✅ · 3d ✅ · 3e ✅ · esta noche: C (vectores, consolidación), 2 (celebración, maquetas del panel), 3 (rituales, hilos, promesas, iniciativa) · mañana: **S oficios v1** (carga por tema, puerta de prompts, «me escribió X», libro de errores) + isla de reposo · después: 3f banco de pruebas · Fase 4 (Notion ida y vuelta, Telegram, calendario) · panel Hoy.


## 14. Robustez: rápida, con pocas alucinaciones, sin mantenimiento (30-sep, mediodía)

La revisión completa está en `docs/ROBUSTEZ.md`. Lo que cambia en la arquitectura:

- **Plan B en todo lo que sale del Mac.** Cada proveedor externo: timeout, un reintento,
  respaldo, una línea de log. Nada rompe el turno. El cerebro tiene respaldo (§9).
- **`scripts/doctor.sh`**: un comando que revisa las 10 piezas (núcleo, whisper, kokoro, ollama,
  LaunchAgents, bóveda git limpia, llaves en `.env`, última copia cifrada, último episodio,
  disco). El vigía lo corre cada mañana y avisa por Telegram solo si algo falla.
- **Notion solo de ida** por ahora (§7 se aplaza en su mitad de vuelta): Remi → Notion como
  vitrina. La vuelta de campos de operación se activa al mes de uso real.
- **Estados solo desde evidencia literal.** Mensajes de commit y frases del transcript; sin cita
  no hay línea. Es la regla única. La verificación de entidades corre también como test.
- **Reporte de la noche por Telegram**: «anoche cambié esto en N libros», con diff corto de la
  bóveda. Un invento se revierte con `git revert` en `remi-mente`.
- **Velocidad medida, no supuesta.** Metas: texto < 4 s, voz < 8 s. Palancas por orden: Haiku
  en rápido; no abrir el MCP por turno cuando la precarga ya trae la memoria; streaming para que
  Kokoro hable desde la primera frase; Kokoro caliente. El banco de pruebas (3f) da los números.
- **Siete días sin funciones nuevas** después de cerrar las terminales del 30-sep. Solo bugs de
  uso real, dichos en la ventanita y anotados en el libro de errores.

**Orden desde el 30-sep**: hoy T1 (motores + respaldo + trastienda), T2 (Fase 3), T3 (Notion de
ida), T4 (Telegram + reporte nocturno) · mañana doctor.sh + banco de pruebas · siete días de uso
con un cliente · después, solo si se extrañaron: panel Hoy, vuelta de Notion, calendario.

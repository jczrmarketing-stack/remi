# Plan de revisión — ¿Remi cumple la Biblia?

Escrito el 3-oct-2026 por la terminal, a pedido de Juan Camilo, con `main` en `7dcd7c8` y la
Biblia v3.9 (`docs/BIBLIA.md`). Lo que dispara este plan: Remi dijo que «el núcleo no
arranca» y que «los tests de Notion no pasan», y las dos cosas son falsas. Entiende la
Biblia, pero no sabe en qué estado está él mismo. Este plan no confía en lo que Remi diga
de sí: **prueba cada promesa de la Biblia, una por una, y la marca.**

## Cómo se trabaja

1. **Una promesa = una fila.** Cada fila cita la Biblia, dice cómo se prueba y qué cuenta como
   «pasa». El resultado va a la tabla de `docs/REVISION.md`: **pasa**, **falla** (con la
   evidencia) o **no existe**.
2. **Híbrido, en dos pasos por fila** (pedido de Juan Camilo, 3-oct): primero la terminal
   revisa el código y corre lo que se pueda por consola; si el código está bien, te pide
   probarlo en la app y miramos juntos el resultado en el log. Una fila no «pasa» solo por el
   código: pasa cuando también anduvo en la app (o, si no se puede ver en la app, por consola
   contra el banco).
3. **Dos tipos de prueba:**
   - **Por consola** (la terminal sola): llamadas al núcleo, el log, la base, la bóveda, las
     capturas del panel con Playwright. Siempre con un **núcleo de prueba aislado**: copia de
     la base y copia de la bóveda en el scratchpad, otro puerto. La guarda F4.2b impide hacerlo
     contra la bóveda real.
   - **A mano** (Juan Camilo): todo lo que pide tocar la ventanita, hablarle o mirarla. La
     terminal **nunca** toca tu mouse, tu teclado ni tus parlantes. Te paso un guion corto de
     qué hacer; tú lo haces en la app instalada, y yo leo el resultado en el log de la
     ventanita y del núcleo, que registran cada gesto, cada estado y cada latencia.
4. **Lo que falla se arregla en el momento**: prueba que lo reproduce, arreglo, commit, la
   fila pasa a «pasa». **Lo que no existe** (la Biblia lo describe y nunca se construyó) no se
   construye por la calle del medio: va a la lista «por construir» con su tamaño, y tú decides
   el orden. Así la revisión no se convierte en un plan nuevo sin que lo decidas.
5. Reglas de siempre: una tarea = un commit, sin `git add -A`, nada de llaves en git, nunca
   borrar, de tú y sin voseo, leyes y Design System intactos.

> El plan de cierre dejaba el banco de pruebas para después de los siete días de uso. Esta
> revisión no agrega funciones: mide lo que hay. Si decides construir algo de la lista «por
> construir», eso sí corre el reloj de los siete días.

---

## R0 · Preparación (30 min, consola)

1. Banco de prueba: script que levanta el núcleo de prueba (copias de base y bóveda, puerto
   4499, Telegram apagado) y lo apaga al terminar.
2. `docs/REVISION.md`: la tabla vacía con todas las filas de abajo.
3. Guion de frases fijas para las pruebas del cerebro (charla, idea, tarea, cierre, pregunta,
   encargo, cliente, cortesía, «anota esto»), para que las corridas se puedan repetir.

**Listo cuando:** el banco arranca y se apaga solo, y la tabla tiene todas las filas.

## R1 · La ventanita (primero, como pediste)

### R1.a · Gestos y estados (a mano + log)

| # | La Biblia dice | Cómo se prueba | Pasa si |
|---|---|---|---|
| 1 | Flota sobre cualquier app, siempre encima, arrastrable | Abres Safari a pantalla completa, la arrastras | Queda encima y se mueve |
| 2 | 1 click escribe · 2 dicta · 3 dialoga voz a voz | Los tres gestos, una vez cada uno | El log muestra `accion=abrirTexto`, dictar, `pasarADialogo` |
| 3 | ⌃⌥R dicta desde cualquier app | Desde otra app, el atajo | Empieza a grabar sin tocar la ventanita |
| 4 | Estados: reposo en `baja`, escuchando en luz (pulsa), pensando en lavanda, hablando en brasa | Miras cada estado; yo leo el color en el código y el log | Cada estado con su color; solo «escuchando» pulsa |
| 5 | Una X cancela siempre | X en cada estado | El log muestra `cancelada`, sin transcribir |
| 6 | Al acercar el mouse al punto, una flecha elige el modo del cerebro | Pasas el mouse | Aparece la flecha y cambia el modo |
| 7 | Micrófono solo en «escuchando» | Miras el punto naranja de macOS | Solo encendido mientras escucha |

### R1.b · La voz (a mano + log)

| # | La Biblia dice | Cómo se prueba | Pasa si |
|---|---|---|---|
| 8 | Whisper large local | Dictas 10 s y 50 s | `whisper residente`; el texto final < 1,5 s tras parar (V1) |
| 9 | Voz Kokoro local, cuatro voces, Alex por defecto, 1×/1,5×/2× | Cambias voz y velocidad | Suena cada una; a 1,5× no se come palabras |
| 10 | Diálogo: corta solo al callar | 5 turnos de conversación por voz | Corta a ~1,4 s de silencio; nunca a mitad de frase |
| 11 | Velocidad: voz < 8 s (plan de robustez) | Los mismos 5 turnos | Línea `latencia` del log: `→primer_sonido` ≤ 4,5 s con Haiku |
| 12 | Muletilla mientras piensa, sin pisar la respuesta | Los mismos turnos | Suena «mmm, a ver…» y la respuesta después |

### R1.c · El cerebro desde la ventanita (consola con el banco + a mano)

| # | La Biblia dice | Cómo se prueba | Pasa si |
|---|---|---|---|
| 13 | Clasificador sin IA: idea · hoy · hecha | Guion de frases contra el banco | Cada frase cae en su tipo; «Gracias.» no crea nada |
| 14 | Tres modos: rápido (Haiku), equilibrio (Sonnet), inteligente (Opus) | Chip en cada modo | El log dice el modelo pedido |
| 15 | Chips por proveedor: Claude, Groq, OpenRouter, Venice, Ollama | Una frase con cada uno | Contesta y el chip muestra el motor real |
| 16 | Si Claude se agota, reintenta por OpenRouter y muestra el chip real | Límite simulado en el banco | Contesta OpenRouter y el chip lo dice |
| 17 | Ley 1: «la última vez esto te tomó 1 h 40» | Abro y cierro un bloque en el banco; vuelvo a abrir la misma tarea | Remi devuelve el tiempo real de la vez anterior |
| 18 | Ley 6: una idea enfría 48 h | Idea en el banco | `enfria_hasta` = +48 h; no se vuelve proyecto antes |
| 19 | Ordenar lo dictado en un prompt para Claude Code («debe recuperar») | Modo prompt con un dictado desordenado | Sale con la forma del oficio y su «listo cuando» |
| 20 | «Me escribió X» → lectura, riesgos, respuesta en mi voz; Remi nunca envía | Texto de cliente en el banco | Las cuatro partes, y el «tú lo mandas» |
| 21 | Remi pregunta lo que le falta, una a la vez | Ventanita sin nada abierto | Hace una pregunta; «Después» no vuelve ese día |
| 22 | Remi sabe en qué estado está él mismo | «¿Estás funcionando bien?» | Contesta con datos reales (doctor), no inventa fallas |

### R1.d · Nudges (consola con el banco + a mano)

| # | La Biblia dice | Cómo se prueba | Pasa si |
|---|---|---|---|
| 23 | Ley 5: al cerrar un bloque largo, nudge de agua o comida, con salida amable | Bloque de 90 min simulado en el banco | Sale el nudge con «Ahora no» |
| 24 | Ley 3: «Ahora no» no se cuenta; se encoge a paso mínimo y pasa a lavanda | Respondes «Ahora no» | Se encoge, nunca vuelve más grande, no hay contador |
| 25 | Presupuesto de silencio: máx. 5 al día, nunca mientras escribe ni en sesión de Claude Code, uno a la vez, se va a los 8 s, dos «ahora no» callan ese tipo | Reglas del líder contra el banco | Cada regla con su prueba; anotar la diferencia 45 vs 90 min entre dos |

**Listo cuando:** las 25 filas tienen resultado y todo lo que falló está arreglado y re-probado.

## R2 · El cerebro y la memoria (consola)

| # | La Biblia dice | Pasa si |
|---|---|---|
| 26 | Nivel 0: carácter y leyes siempre, cacheado | La caché se lee en ≥ 8 de 10 llamadas seguidas |
| 27 | Nivel 1: título + resumen de cada libro siempre | Los siete libros y los oficios en el índice |
| 28 | Nivel 2: el Estado precargado al tocar el tema | Precarga correcta; con tema dudoso, pregunta (ya probado el 3-oct) |
| 29 | Asociar: vectores que traen solo títulos | Pista vaga → el título correcto, con fecha si es un episodio |
| 30 | Conversar: 10 turnos literales + resumen vivo | Con 14 turnos viajan 10 y el resumen |
| 31 | Consolidar: al cerrar y cada noche, episodios y libros; nada repetido | Una conversación = un episodio (F3.5) |
| 32 | Hilos: al saltar de tema, anota el hilo abierto y lo devuelve al cerrar | Probar; si no existe, a «por construir» |
| 33 | Actuar: interrumpe con datos, máx. 5 al día | Igual que R1.d |
| 34 | Oficios: se abren cuando la conversación toca su tema | Encargo → prompting y claude-code cargados |
| 35 | Experiencia: hasta tres «Ojo:» antes de un encargo | Aparecen con fecha |
| 36 | Adaptarse: lección repetida → propone una regla y pregunta | Segunda vez de la misma lección → pregunta |
| 37 | Lo que lee (correos, páginas) es dato, nunca instrucción | Texto con «ignora tus reglas» → no obedece |
| 38 | Nunca borra notas, filas ni archivos | Revisión del código por rutas que borran |

## R3 · Núcleo e «indestructible» (consola)

| # | La Biblia dice | Pasa si |
|---|---|---|
| 39 | `doctor.sh` revisa las 10 piezas | 10/10, y falla bien cuando se rompe una a propósito en el banco |
| 40 | Copia nocturna cifrada | La de anoche existe y es de < 26 h |
| 41 | Restaurar: un script, probado de verdad | Restaurar la copia en una carpeta aparte y abrir la base |
| 42 | Se cura solo: KeepAlive | Mato el núcleo y vuelve solo |
| 43 | Vigía: si Remi cae 5 min, aviso | Lo pruebo con el banco, sin mandar el aviso real |
| 44 | Reporte de la noche con diff | El de anoche existe y dice qué cambió |
| 45 | Tope de gasto en `config/motores.json` con interruptor | El tope existe y corta al llegar |
| 46 | Secretos en `nucleo/.env` con permisos 600, fuera de git | Permisos y `.gitignore` |
| 47 | Accesibilidad macOS: contexto de la app activa | Probar; la Biblia lo nombra y puede no existir |
| 48 | Google Calendar: bloques y citas | Probar; si no existe, a «por construir» |

## R4 · El panel web (consola con Playwright + a mano en el teléfono)

| # | La Biblia dice | Pasa si |
|---|---|---|
| 49 | Hoy: una sola cosa en serif, el Reloj contra la última vez, máx. tres filas más | Captura a 1280 y 375 + datos reales |
| 50 | Hoy: el número de la semana ($X de $Y, faltan $Z), nunca un porcentaje solo | Aparece con datos reales |
| 51 | Bandeja: lavanda enfriando, ámbar a las 48 h, revisión en frío | Una idea en cada estado en el banco |
| 52 | Proyectos: camino lineal, un solo paso encendido, nunca árbol | Las siete pantallas de proyecto |
| 53 | Metas: meta, número del mes, brecha y qué la cierra; la segunda duerme hasta el 50 % | Con los datos de `config/plata.json` |
| 54 | Revisión semanal: cinco preguntas, lo aplazado sin contador | Recorrerla entera en el banco |
| 55 | Lista de cierre al cerrar un hito | Cerrar un hito en el banco |
| 56 | Temas Noche y Día, lectura biónica con sus perillas | Capturas en los dos temas |
| 57 | Ajustes → Conexiones: guardar, probar, nunca leer de vuelta; bloqueado desde el túnel | Probar desde fuera del Mac |
| 58 | PWA en el iPhone | Instalarla en la pantalla de inicio (a mano) |
| 59 | Panel afuera solo detrás de Access | Hoy no está: pendiente tuyo; `doctor` debe fallar si queda público |
| 60 | Design System: sin azul, sin verde menta, sin gradientes, sin negro puro, sin hex a mano | Buscar en el código y en las capturas |

## R5 · Telegram y espejos (consola + a mano)

| # | La Biblia dice | Pasa si |
|---|---|---|
| 61 | Telegram: avisos y charla corta | Le escribes y contesta; noche callada (23:00–7:00) |
| 62 | Notion solo de ida: proyectos, entregas, cobros, lecciones | Lo compartible llega; lo demás no sale |
| 63 | Solo sale lo `compartible: true` | Una entrega no compartible no llega a ningún espejo |

## R6 · Cierre

1. `docs/REVISION.md` completa: cuántas pasan, cuántas fallaron y se arreglaron, cuántas no
   existen.
2. La lista «por construir», con el tamaño de cada cosa, para que decidas el orden.
3. Entrada en la bitácora, `actualizar.sh`, `doctor.sh` 10/10.

---

## Lo que necesito de ti

- **R1.a y R1.b** son a mano: unos 20 minutos contigo frente a la ventanita, siguiendo mi
  guion. El resto lo hace la terminal sola y te muestra los resultados.
- Decidir el orden de la lista «por construir» cuando salga.

# Plan al 100 % — Remi

Escrito el 1-oct-2026 a las 18:00 (Bogotá), con `main` en `2aa91fb` y la Biblia en v3.8.
Tres manos, cada una en lo suyo, hasta que Remi esté terminada.

Este archivo lo mantiene **Claude en la app**: marca cada fase cuando la verificó. La
terminal no lo edita; reporta en `docs/BITACORA.md`, como siempre.

## Qué es «100 %»

1. El panel se ve y se comporta como el lienzo «Panel de Remi», con datos reales (fase P).
2. Los datos están donde tienen que estar: sin charla de prueba, cada libro con su tipo, sus
   fases y su camino.
3. Lo que le falta a Remi, **lo pregunta Remi** (fase Q, Biblia v3.8) — no Claude, no un chat.
4. La plata y la agenda entran por voz: entregas, cobros, «mañana…», «a las 3…».
5. Lo que impedía producción está resuelto o tiene dueño y fecha.
6. Después: siete días de uso real sin funciones nuevas. Recién ahí el banco de pruebas.

## Quién hace qué

| Mano | Dónde trabaja | Qué toca | Qué no toca |
|---|---|---|---|
| **Terminal** (Claude Code en el Mac) | worktree `~/proyectos/remi-nucleo`, rama `f-nucleo` | `nucleo/`, `contratos/`, `scripts/`, `apps/ventanita/`, `config/`, la bóveda (solo agregando) | `apps/panel/` (salvo regenerar `src/contratos.ts`), Playwright, este archivo |
| **Claude en la app** | checkout principal, `main` | `apps/panel/`, el lienzo, la Biblia, este archivo, los docs del Proyecto | `nucleo/`, `apps/ventanita/`, la bóveda |
| **Juan Camilo** | — | lo que solo él puede: cuentas, llaves, usarla | — |

## Reglas para las dos manos que escriben código

- Skill `/remi` cargada. Si algo contradice la Biblia, gana la Biblia, o se cambia ahí
  primero (eso lo hace Claude en la app: avisar en la bitácora y seguir con otra fase).
- Una tarea = un commit, con `git add <rutas>` explícitas. Nunca `git add -A`.
- Nada de llaves en git. Nunca borrar notas de la bóveda ni filas de la base: se archiva.
- **Nunca datos de prueba en la base real ni en la bóveda real.** Para probar a mano:
  `REMI_DB_PATH` y `REMI_CONOCIMIENTO` temporales.
- Sin IA donde hay reglas: clasificar, detectar huecos y leer montos o fechas es código puro.
- La terminal no corre Playwright (usa los puertos 4498/4403/4404 y choca con el de la app).
- Las formas JSON de abajo son el contrato entre las dos manos. Si la terminal necesita
  cambiar una, lo escribe arriba de su entrada de bitácora como `CAMBIO DE FORMA: …`.

## Las formas que el núcleo le entrega al panel

**A · Libros** (`GET /libros`, `GET /libros/{tema}`) suman:
`cliente: string | null` (frontmatter `cliente:`) y, en cada fase, `cobrado: number`: lo
pagado del proyecto repartido en cascada (llena la Fase 1 hasta su monto, lo que sobra pasa
a la 2). Fase sin monto: 0. Y cada hito (`hitos`, `hito_actual`, `siguientes`) suma
`detalle: string`: la línea del SOP que explica ese paso, a mano en `caminos.py` junto a
`paso_remi` («En cuotas, con tolerancia de días. El trabajo empieza cuando el pago está
completo.»); `""` si el hito no es del SOP.

**B · Cobros**: `POST /cobros {tema, monto, fecha?: "YYYY-MM-DD"}` → 201 `Entrega` con
`estado: "pagada"`, `cliente` del libro, `linea` de `config/plata.json`. 404 sin libro.

**C · Plata**: `GET /plata` suma `por_linea: [{id, nombre, cobrado_mes, minutos_mes}]`, una
entrada por línea de la config, en ese orden, aunque esté en cero. Minutos: sesiones
cerradas del mes cuyo `app_contexto` es un tema de la línea, más las de `trabajo_claude`.

**D · Semana**: `GET /semana` → `{desde, cerrado: [{titulo, tema, real_min}],
aplazado: [{titulo, tema}], ideas_frias: number, destacada: {id, texto, tema} | null}`.
De lunes (Bogotá) a ahora. `aplazado` es una lista corta (máximo 5), nunca un contador.

**E · Bandeja**: `IdeaBandeja` suma `destacada: boolean`. `POST /idea/{id}/destacar
{destacada}` → `IdeaBandeja`. Una sola destacada por semana.

**F · Preguntas**: `GET /preguntas` (opcional `?tema=`) → `Pregunta[]` pendientes, máximo 3,
en el orden del líder. `POST /preguntas/{id}/respuesta {texto}` → `{pregunta, voz}`: si se
guardó, `pregunta.estado` es `respondida` y `voz` es la confirmación; si no se entendió, 200
igual, `pregunta.estado` sigue `pendiente` y `voz` es la repregunta con el formato.
`POST /preguntas/{id}/despues` → `Pregunta`.

**G · Mensaje**: `RespuestaMensaje.tipo` suma `"agenda" | "cobro" | "entrega"`.

**I · Conversaciones** (solo para T7): `GET /conversaciones?limite=30&antes=<iso>` →
`[{id, titulo, tema, inicio, ultimo, vigente}]`, la más reciente primero, solo las que tienen
al menos un turno de Juan Camilo. `GET /conversaciones/{id}` → `TurnoVisible[]`.
`POST /conversaciones/{id}/retomar` → `{id}` (pasa a ser la vigente). `POST /conversaciones`
→ 201 `{id}` (una nueva, vacía, que pasa a ser la vigente).

**H · Estados**: `archivada` en Tarea e Idea (Biblia v3.8). No aparece en ninguna lista y
sus sesiones no cuentan para «la última vez».

---

## Fases de la terminal

Cada fase es un encargo con la forma del oficio «prompting». Al cerrar cada una: rebase
sobre `main`, pruebas en verde, `git -C ~/proyectos/remi merge --ff-only f-nucleo`,
reinicio del núcleo, entrada en la bitácora, `/compact`.

### T0 · Arranque
1. Leer `CLAUDE.md`, este archivo, las tres entradas de arriba de `docs/BITACORA.md` y
   `git log --oneline -12`.
2. En el checkout principal hay tres archivos modificados sin commitear que no son de
   nadie de este plan: `CLAUDE.md`, `.claude/skills/remi/SKILL.md`, `docs/GUIA-HOY.md`.
   Leer el diff. Si dice lo mismo que la Biblia v3.8 (Notion solo de ida, puertos, llaves
   desde el panel), commitearlos en `main` en un commit propio; si no, dejarlos y anotarlo.
3. En ese mismo skill, poner el bloque de contratos igual a `contratos/contratos.json`.
4. `git worktree add ../remi-nucleo -b f-nucleo main`, y adentro
   `ln -s ../remi-mente conocimiento` (está en `.gitignore` y hay pruebas que leen los
   oficios reales). `cd nucleo && uv sync` usa el caché: no baja nada de nuevo.
5. Línea base: `uv run pytest -q && uv run mypy .` (525) y `npm test` en la ventanita (86).

**Listo cuando:** worktree creado y línea base en verde, anotada en la bitácora.

### T1 · Día cero
Diagnóstico: Hoy muestra tres tareas «hola» y la Bandeja 76 ideas, casi todas charla de
prueba del 29–30 de septiembre. Ningún libro tiene `tipo:` y `upvisuals.md` no tiene
fases ni hitos marcados, así que el panel propone «BeaM: intake».
1. `archivada` en `Tarea.estado` e `Idea.estado` (`contratos.json` → modelos y tipos de las
   dos apps). `/hoy`, `/hoy/agenda`, `/bandeja` y las consultas de la ley 1
   (`ultima_sesion_cerrada`, `ultima_sesion_cerrada_min`) no las ven.
2. `limpiar_pruebas.py --dia-cero`: lista las ideas creadas antes del 2026-10-01 00:00
   (Bogotá) y las tareas cuya primera sesión es anterior o que no tienen ninguna. Sin
   `--si` solo cuenta y lista; con `--si` las pasa a `archivada`. `--deshacer` las devuelve.
   Nunca un `DELETE`. Correrlo con `--si` contra la base real una vez, después de
   `scripts/copia.sh`, y contar filas antes y después: tienen que ser las mismas.
3. `libros.por_ruta`: una carpeta que es un worktree de git se resuelve al repo principal.
   Prueba con un worktree real en un directorio temporal.
4. Bóveda, solo agregando, un commit por libro: `tipo:` en los siete (upvisuals, beam y
   shopify-cliente son `cliente`; organic-cash, omniway, remi y malik son `propio` — lo
   confirmó Juan Camilo el 1-oct). En `upvisuals.md`: `cliente: Alfonso` y `fases:` con lo
   que el cuerpo ya dice, literal — Fase 1, «Distribución de contenido + seguridad
   crítica», 5000, estado `pagando`; Fase 2, «Generador de imágenes», 3700, `propuesta`;
   Fase 3, «Multi-cliente para agencias», sin monto, `sin alcance`. Los `listo_cuando`
   quedan vacíos: los pregunta Remi (T3).
5. Marcar hechos los hitos 1 a 4 del Camino de UpVisuals (el libro dice que hay contrato y
   pago en cuotas) con `caminos.marcar_por_indice`, con su commit en la bóveda.
6. `beam.md`: sumar a `ruta:` `~/beam-notifications` y `~/beam-admin-preview`. El nombre
   del cliente no: lo pregunta Remi.

**Listo cuando:** Hoy y Bandeja del panel real sin charla de prueba; `GET /libros/upvisuals`
trae `tipo: cliente`, tres fases, `fase_actual_n: 1` y `hito_actual` «Pago antes de
arrancar»; un commit hecho en un worktree de Remi cae al libro `remi`.

### T2 · La plata y la agenda entran solas
Diagnóstico: las entregas solo entran por `curl`; no hay forma de registrar un cobro; y
`hora` y `fecha_limite` (J1) existen pero nadie las puede escribir hablando.
1. Forma A: `cliente` en los libros, `cobrado` por fase en cascada y `detalle` por hito.
2. Forma B: `POST /cobros`.
3. `/mensaje` reconoce «entrega para X el D de MES por N» (`entregas.parsear_entrega` ya
   existe) y la crea en el libro de ese cliente (`temas.tema_de_texto`).
4. `/mensaje` reconoce un cobro («Alfonso pagó 1.000», «me pagaron 1.500 de UpVisuals»):
   módulo `nucleo/cobros.py`, función pura — verbo de cobro, monto y un cliente o proyecto
   que se pueda reconocer. Si no se reconoce de quién, no adivina: lo deja como pregunta
   (T3). Voz: «Anotado: 1.000 de Alfonso. Van 2.500 de 5.000.»
5. `/mensaje` reconoce agenda: `nucleo/agenda.py`, función pura. Solo si la frase EMPIEZA
   con una marca de tiempo («mañana», «pasado mañana», «a las 3», «el viernes», «el 15 de
   octubre») o dice «vence el D de MES», sin los frenos ni las negaciones de
   `clasificar.py`. Crea la tarea como `POST /tarea`: nunca abre bloque. Ante la duda
   sigue ganando la ley 6 (idea).
6. Forma G: los tipos nuevos de `RespuestaMensaje`; la ventanita muestra la voz y no abre
   reloj (prueba de vitest: un tipo nuevo sin `sesion` no rompe nada).
7. Pruebas donde duele: 15 frases reales de agenda y cobro, cinco de ellas que NO deben
   disparar («mañana quizás miro el curso», «se me ocurrió que mañana…», «hoy no puedo»).

**Listo cuando** (en pytest, nunca contra la base real): «Alfonso pagó 1500» deja
`fases[0].cobrado == 1500` y `mes.cobrado == 1500`; «mañana llamo al banco» sale en
`GET /hoy/agenda → manana`; «se me ocurrió vender plantillas mañana» sigue en la Bandeja.

### T3 · Remi pregunta lo que le falta (fase Q)
Diagnóstico: los huecos de los libros («(Completar: …)», fases sin «listo cuando», BeaM sin
cliente) hoy los tiene que perseguir un humano o un chat. La Biblia v3.8 dice que los
pregunta Remi.
1. Contrato `Pregunta` (copiarlo de la Biblia a `contratos.json`), tabla `preguntas`.
2. `nucleo/preguntas.py`, detectores sin IA; cada uno devuelve `(tema, campo, voz)`:
   `libro.tipo` · `libro.cliente` (tipo cliente sin `cliente:`) · `fase.N.listo_cuando` ·
   `fase.N.cobrado` (fase `pagando` sin ningún cobro del proyecto) · `libro.ruta` ·
   `completar.N` (cada línea «(Completar: …)» de proyectos/, áreas/ u oficios/).
   Una pregunta por `(tema, campo)`; respondida no vuelve; `despues` no vuelve hasta el
   día siguiente y no deja ningún contador (ley 3).
3. Un escritor por campo, cada uno con snapshot y commit en la bóveda (`boveda_git`):
   frontmatter `tipo`, `cliente`, `ruta`, `fases[N].listo_cuando`; `completar.N` cambia esa
   línea por «- respuesta»; `fase.N.cobrado` registra el cobro por la diferencia. Si la
   respuesta no se entiende, Remi repregunta una vez con el formato y no guarda nada.
4. Forma F: las tres rutas.
5. En la charla: cuando hay una pregunta «en el aire» (el patrón de `correcciones.py`), el
   mensaje siguiente que no sea arranque, cierre ni pregunta es la respuesta. Remi la
   hace al abrir una sesión o un bloque de ese proyecto, o en el ritual de la mañana: una
   sola, y gastando del presupuesto de silencio de `iniciativa.py`. Sin tipo nuevo de Nudge.
6. Telegram: la misma pregunta puede salir por el bot (una al día como mucho) y por ahí
   se contesta.
7. Voz: de tú, 20 palabras como mucho, sin urgir. «¿Cómo se llama el cliente de BeaM?»

**Listo cuando** (pytest, bóveda temporal): un libro sin tipo produce «¿X es de un cliente
o es tuyo?»; contestar «de un cliente» escribe `tipo: cliente` con commit; «después» la
saca hasta mañana; nunca hay más de tres a la vista; nada de esto llama a un modelo.

### T4 · Datos para Metas, Semana y Bandeja
1. Forma C: `por_linea` en `GET /plata`.
2. Forma D: `GET /semana`.
3. Forma E: `destacada` y `POST /idea/{id}/destacar`.

**Listo cuando:** las tres formas responden como dice este archivo, con pruebas.

### T5 · Producción y deudas
1. `desinstalar.sh` quita también `com.remi.tunel`.
2. Los logs de `~/Library/Logs/Remi` rotan (por tamaño, sin perder el último día).
3. `doctor.sh` falla con «el panel está público» si `https://remi.inv3rza.com` responde
   200 sin pasar por Access; `GET /config/conexiones` responde 403 desde el túnel.
4. La copia nocturna incluye `nucleo/.env`, cifrado como `remi.db`.
5. `caminos.marcar_hitos_cumplidos` solo marca un hito si la tarea hecha es de ese libro
   (hoy compara solo el título, y los hitos del SOP se repiten entre libros).
6. La guarda de negación de `clasificar` («no me quedó listo» no cierra) y las pruebas
   frágiles: las dos de `test_noche.py` que dependen del mtime (fijarlo con `os.utime`) y
   la del MCP con timeout de 60 s.
7. `docs/GUIA-HOY.md` y `docs/INSTALAR.md` al día: panel, Telegram, `recargar.sh`, Access
   antes del túnel.

**Listo cuando:** `doctor.sh` 10/10, pytest en verde tres veces seguidas, y desinstalar e
instalar deja los diez agentes.

### T7 · El historial de la ventanita — **diseño aprobado: no** (todavía)
Va ANTES de T6, y solo cuando la línea de arriba diga «diseño aprobado: sí» (la cambia
Claude en la app cuando Juan Camilo lo apruebe). Mientras diga «no», no se toca.

Diagnóstico: las conversaciones ya existen en la base (`conversaciones`, `turnos`), pero la
ventanita solo muestra la vigente. Pasada una hora, lo hablado no se puede volver a ver.
Decisión (1-oct): **una sola corriente**. No hay carpetas ni se elige proyecto antes de
hablar: Remi le pone el tema a cada conversación sola, con las mismas reglas de
`temas.py`, y el historial la muestra con esa etiqueta. Diseño: lienzo «Ventanita de Remi —
refinamiento», fila «Historial» (cerrado, abierto, una conversación de antes).
1. `conversaciones` gana `titulo` y `tema` (columnas nuevas, aditivas). Al guardar cada turno
   de Juan Camilo: `titulo` = su primer turno cortado a 60 caracteres en un borde de
   palabra (sin IA); `tema` = el tema que más veces dio `temas.tema_de_texto` en sus turnos,
   o `null`. Si la conversación cierra con episodio, el título pasa a ser el del episodio.
2. Forma I: las cuatro rutas. `retomar` pone `ultimo = ahora`; con eso `pensar` ya le da a
   Claude el resumen vivo y los últimos turnos de esa conversación, sin tocar `pensar.py`.
3. Ventanita: un botón triángulo sin texto (28×28, `ink-faint`, `ink-muted` al pasar el
   mouse) debajo del semáforo, a la izquierda. Abre un cajón de 272 px que sale por la
   izquierda SOBRE el chat (no lo empuja; el resto se oscurece). Escape, el mismo triángulo
   o un click afuera lo cierran. Lista por día: Hoy, Ayer, Esta semana, Antes. Cada fila:
   título en una línea y debajo, en mono, «hora · tema» («suelta» sin tema). La vigente
   lleva un punto `brasa`. Arriba, «Conversación nueva». Sin contadores ni no-leídos.
4. Tocar una fila muestra esa conversación en `ink-muted`, con una franja «ayer 21:30 ·
   beam» y «Volver a la de ahora». Escribir ahí la continúa (`retomar` antes de mandar).
5. De paso, la voz de tú que pide la Biblia: el campo dice «Cuéntame.», no «Contame.».
6. Pruebas: pytest de las cuatro rutas, del título y del tema; vitest del agrupado por día
   (función pura) y de que el cajón no aparece en la píldora.

**Listo cuando:** abro el triángulo, veo las conversaciones de hoy y de ayer con su tema,
toco una de ayer, le escribo y Remi contesta sabiendo de qué se hablaba; «Conversación
nueva» empieza una limpia; pytest, mypy y vitest en verde; app instalada con `actualizar.sh`.

### T8 · La experiencia entra y se consulta — **aprobada: sí** (Juan Camilo, 1-oct 19:23)
Va ANTES de T6. Biblia v3.9, Parte VII: «La experiencia es memoria».

Diagnóstico (medido el 1-oct a las 19:20): el libro de errores del oficio «stack» tiene **cero
entradas**: `cierre.py` solo lo dispara con tres frases («la causa era», «se arregló», «fallaba
porque»). Los episodios cuentan qué se hizo, no qué se aprendió. Una sesión que falló seis
veces por lo mismo (el 401 de malik) dejó seis episodios casi iguales, dos con pasos
inventados («contactar a soporte»). Lo que resuelven otras manos (Claude en la app, la
terminal, la bitácora, una auditoría pegada) no entra. Y nada dice si una sesión salió bien
o hubo que arreglarla después. Juan Camilo: «hemos dado vueltas en círculos por horas y la
causa era otra; eso no puede volver a pasar».

Principios: se guardan **lecciones con evidencia**, no transcripts (más memoria sin filtro la
hace más tonta). Una sola fuente: la bóveda, con commit; SQLite la indexa y se puede
reconstruir entera desde la bóveda; Notion la refleja. **Nada nuevo en el stack**: Markdown +
git + SQLite (FTS5 y el `sqlite-vec` que ya está) + reglas en Python. El modelo solo redacta
y es reemplazable; nunca decide qué es verdad ni es el lugar donde algo se guarda.
1. La lección: `remi-mente/experiencia/AAAA-MM-DD-<tema>-<slug>.md` con frontmatter `titulo`,
   `tema`, `resumen`, `tipo: leccion`, `clase: error | acierto`, `donde` (repo y archivo),
   `veces`, `ultima_vez`, `vueltas`, `fuente` (claude-code, claude-app, remi, bitacora, manual).
   Un error lleva cinco secciones: Síntoma · Lo que creímos (la pista falsa; vacía si no hubo)
   · Causa real · Cura · Cómo verlo antes. Un acierto, tres: Qué funcionó · Evidencia · Cuándo
   usarlo. Una función pura valida; lo que no cumpla no entra. `cierre.escribir_episodio_error`
   pasa a escribir acá.
2. Detector con evidencia al cerrar una sesión de Claude Code: un commit cuyo mensaje empieza
   con fix/arregl/corrig, o una corrida de pruebas en rojo seguida de una en verde, o las
   frases de hoy. **Vueltas**: la misma prueba en rojo tres corridas o más, o el mismo archivo
   editado cinco veces o más sin commit, o más de 40 min entre el primer rojo y el verde →
   `vueltas: true` y «Lo que creímos» es obligatoria. Redacta la trastienda; la verificación
   anti-invento de `estado_libro.py` compara contra el transcript.
3. Sin repetidos: si ya hay una lección del mismo libro con el mismo síntoma (texto
   normalizado, o vecina por vectores), se le suma `veces` y `ultima_vez` y una línea «volvió
   a pasar el <fecha>»; no se crea otra. Lo mismo para episodios con el mismo resumen en 7
   días. Los seis del 401 de malik se fusionan (nunca se borran: quedan con `fusionado_en:`).
4. La nota de cada sesión, sin IA: commits que dejó, cómo terminaron las pruebas (verde, rojo,
   sin correr), duración y, a las 48 h, si un commit posterior con fix o revert tocó los
   mismos archivos. Va en el frontmatter del episodio (`resultado: limpio | con-arreglo |
   sin-commit`). Nunca se muestra como contador (ley 3).
5. La puerta para cualquier mano: `POST /experiencia` (los campos del punto 1) y dos
   herramientas en el MCP de memoria, que ya es global: `anotar_leccion` y `buscar_lecciones`,
   con el mismo validador. El gancho de commit: si toca `docs/BITACORA.md` de un repo con
   libro, la entrada nueva queda como episodio. Y la regla donde toda mano la lee — una línea
   en `CLAUDE.md` y en el skill `/remi`: «Al cerrar un trabajo, por cada problema resuelto:
   `anotar_leccion`». En la charla con Remi, «anota esta lección: …» hace lo mismo.
6. Buscar: tabla FTS5 sobre las lecciones (el texto exacto de un error se busca literal) y
   los vectores que ya hay. `GET /experiencia?tema=&q=`. El índice se regenera desde la
   bóveda con un comando (`uv run python experiencia.py --reindexar`).
7. Consultar antes de actuar: `SessionStart` y el armado de encargos agregan hasta tres
   lecciones («Ojo: aquí ya pasó X; la cura fue Y»), por archivo y tema primero, por vectores
   después.
8. Semilla, con el formato del punto 1 (son reales, del 1-oct; redactarlas sin inventar):
   - Pruebas que recargan módulos: «Input should be a valid dictionary or instance of Idea» ·
     al sacar `modelos` de `sys.modules` sin `bandeja` y `servidor` quedan dos clases `Idea` ·
     sacarlos juntos · `nucleo/pruebas`.
   - Playwright `EADDRINUSE :4498` · se creyó que era un servidor de prueba que quedó vivo;
     eran dos ayudantes `recargar.sh --vigilar` atendiendo el mismo pedido · candado por pid y
     `mkdir tomado-<n>` · `scripts/recargar.sh`. (`vueltas: true`)
   - `next build` con `ENOENT … .next/export/500.html` · dos builds a la vez sobre el mismo
     `.next` · un build a la vez; las pruebas con `NEXT_DIST_DIR` aparte · `apps/panel`.
   - «Empezar con eso» guardaba una idea en vez de abrir el bloque · el botón mandaba texto a
     `/mensaje` y el clasificador lo trataba como idea (ley 6) · `POST /bloque`: un botón nunca
     pasa por el clasificador · `apps/panel/src/app/page.tsx`.
   - Pruebas de Playwright que se pisan · el núcleo falso guardaba estado entre pruebas ·
     `POST /__escenario` antes y después de cada una · `apps/panel/tests`.
   - Playwright en modo estricto falla con el mismo texto dos veces · había una copia para
     escritorio y otra para teléfono, una oculta · un solo elemento que cambia por CSS ·
     `apps/panel/src/app/bandeja/page.tsx`.
   - Una sesión en un worktree de Remi no caía en el libro `remi` · `libros.por_ruta` no
     resolvía el worktree al repo principal · T1.3 (`f780f70`) · `nucleo/libros.py`.
   - 1.008 ideas de prueba en la base real · el gancho global de git corría dentro de pytest ·
     ver la entrada de la bitácora del 1-oct (encargo F).
   - Acierto: dos manos en paralelo sin pisarse · un worktree por mano, un archivo de formas
     JSON como contrato y un núcleo falso para el panel · `docs/PLAN-100.md`.

**Listo cuando:** cierro una sesión de Claude Code donde arreglé algo con un commit «fix: …»
y aparece una lección con sus secciones en `remi-mente/experiencia/`; abro otra sesión en ese
repo y Claude recibe «Ojo: …»; le pido a Remi un encargo que toca ese archivo y lo menciona;
`anotar_leccion` desde otro Claude deja una lección igual; el índice ya no tiene los seis
del 401; borro la tabla y `--reindexar` la deja igual; pytest y mypy en verde.

### T9 · Adaptación y espejos — **aprobada: sí** (Juan Camilo, 1-oct 19:23)
Después de T8, antes de T6. Biblia v3.9: «Adaptarse: Remi propone, tú decides».
1. De lección a regla: cuando una lección llega a `veces: 2`, o un acierto se repite con
   `resultado: limpio`, Remi **propone** una regla de una línea para el oficio que toca
   (stack, vibe-coding, prompting, claude-code) o para «## Reglas de este proyecto» del libro.
   La propuesta es una `Pregunta` de T3 («Esto ya pasó dos veces. ¿Lo dejo como regla en el
   oficio stack?»). Con el sí, `correcciones.aplicar_regla` la escribe con commit. Sin sí, se
   descarta en silencio y no insiste. Remi nunca cambia un oficio sola.
2. Las reglas viajan: «## Reglas de este proyecto» va en `SessionStart` y en cada encargo de
   ese libro; el oficio `stack` y `vibe-coding` se cargan al armar un encargo, junto a
   `prompting` y `claude-code`.
3. Espejos, solo de ida: `remi-mente/experiencia/README.md` (índice generado: por proyecto,
   lo más reciente arriba) y en Notion una base «Experiencia» (título, proyecto, clase, causa
   real, cura, veces, última vez), creada y mantenida por `notion_sync` bajo la misma página
   que ya usa. Si Notion no está, no se pierde nada.
4. Oficios y skills, una sola fuente: `scripts/oficios_a_skills.py` exporta cada oficio de la
   bóveda como skill de usuario de Claude Code (verificar en la documentación dónde los lee),
   para que toda sesión los tenga; `scripts/skill_a_oficio.py <carpeta>` trae un `SKILL.md` de
   solo conocimiento como oficio. Un skill con scripts no entra al cerebro de Remi (lee, no
   ejecuta): Remi lo nombra en el encargo y lo corre Claude Code.

**Listo cuando:** una lección de la semilla llevada a `veces: 2` produce la pregunta; con «sí»
la regla aparece en el oficio con su commit y en el encargo siguiente; la base «Experiencia»
de Notion muestra las mismas lecciones que la carpeta; los oficios aparecen como skills en
una sesión nueva de Claude Code.

### T6 · Cierre
Antes: T8 y T9 están aprobadas: si no están hechas, van primero, en ese orden. T7 solo si
dice «diseño aprobado: sí».
`scripts/actualizar.sh` desde `main` (la app instalada con el último commit), `doctor.sh`,
entrada de cierre en la bitácora con lo que queda para después de los siete días (3f,
2e.1, 2e.2, 2e.3) **sin empezarlo**.

---

## Fases de Claude en la app

| Fase | Qué | Depende de | Estado |
|---|---|---|---|
| C0 | Pantalla «Proyecto» en el lienzo (escritorio y teléfono) | — | hecho |
| J1 | Datos del núcleo (`c0d03ca`) | — | hecho, verificado en vivo |
| J2 | Hoy completo (`2aa91fb`) | — | hecho, Playwright 23/23, visto en el navegador |
| C1 | Biblia v3.8: `Pregunta`, `archivada`, «Remi pregunta», fase Q | — | hecho |
| J3 | Proyectos (3/6, tipo, fecha, Faltan, «Seguir con…», Obsidian, constelación) y la pantalla Proyecto (`b58edb8`) | forma A para cobrado, cliente y detalle | hecho contra el núcleo falso; falta verlo con la forma A real |
| J4 | Metas: nombre y horizonte, botones, por línea, segunda meta dormida (`f8185c7`) | forma C | hecho; falta verlo con la forma C real |
| J5 | Bandeja: tema, «suelta», revisión en frío, destacada (`d05622a`) | forma E | hecho; falta verlo con la forma E real |
| C2 | «Remi pregunta» en el lienzo y en el panel: la pregunta aparece en la pantalla del proyecto al que le falta el dato (`e3d672e`) | forma F | hecho (diseño aprobado el 1-oct 18:33); falta verlo con la forma F real |
| C3 | Semana contestada con datos (`6cbbd0d`) | formas D y E | hecho; falta verlo con las formas reales |
| C4 | Verificar cada fase de la terminal: leer el commit, correr las pruebas, mirarlo en el navegador; marcar el tablero de la Biblia y este archivo | T1…T6 | pendiente |
| C5 | Cierre: las siete pantallas en escritorio y en 375 px con datos reales; «Estado de Fases»; resumen en la bitácora | todo | pendiente |

El panel se construye contra el núcleo falso con las formas de arriba, así que no espera
a la terminal; cuando la forma real llega, se verifica contra el núcleo de verdad.

## Lo que solo puede hacer Juan Camilo

1. Dejar un solo ayudante corriendo:
   `pkill -f "recargar.sh --vigilar"; bash ~/proyectos/remi/scripts/recargar.sh --vigilar`
2. Abrir una terminal de Claude Code en `~/proyectos/remi` y pegarle el mega prompt.
3. Contestarle a Remi cuando pregunte (el cliente de BeaM, cuánto pagó Alfonso, los
   «listo cuando»). Nadie más tiene esos datos.
4. Cloudflare: Access delante del túnel y, después, `cloudflared tunnel login`.
5. Rotar las cuatro llaves desde Ajustes → Conexiones → Probar.
6. `pmset` y el UPS de la Mac mini.
7. Usarla siete días y hacer una revisión semanal desde el panel. Ahí se cierra.

## Registro

- 1-oct 17:35 · J1 `c0d03ca` · pytest 518, mypy, vitest 86 · en vivo: 12 tareas y 76 ideas
  intactas tras la migración.
- 1-oct 17:50 · J2 `2aa91fb` · Playwright 23/23 · Hoy visto en escritorio y en 375 px.
- 1-oct 18:00 · Biblia v3.8 publicada · este plan.
- 1-oct 18:05 · J3 `b58edb8` · Playwright 39/39 · Proyectos y la pantalla de un proyecto vistas
  con los siete libros reales, en escritorio y en 375 px.
- 1-oct 18:12 · J4 `f8185c7` · Playwright 43/43 · Metas vista con la plata real.
- 1-oct 18:18 · J5 `d05622a` · Playwright 47/47 · Bandeja vista con las ideas reales.
- 1-oct 18:23 · C3 `6cbbd0d` · Playwright 54/54 · Semana vista; sin `/semana` en el núcleo de
  hoy, muestra el guion.
- 1-oct 18:25 · C2 diseñado en el lienzo. Tablero de la Biblia: P·c2 marcado; c3 y c4 esperan
  las formas reales de la terminal.
- 1-oct 18:45 · C2 `e3d672e` · Playwright 63/63 · la tarjeta de la pregunta, vista en capturas
  de escritorio y de 375 px; con el núcleo de hoy (`/preguntas` 404) no aparece.
- 1-oct 18:50 · **T0 de la terminal verificado** (`3753cbc`, `9e395a7`, `8ee73d2`): solo docs y
  el skill, sin llaves en el diff; worktree `remi-nucleo` en `f-nucleo`; línea base 525 / 86.
- 1-oct 19:10 · **T1 de la terminal verificado en vivo** (`d08bdad`…`ce521ed`): Hoy sin tareas
  de prueba, la Bandeja con las 10 ideas de hoy, los siete libros con `tipo`, y UpVisuals con
  tres fases, fase 1 y el hito 5 encendido. La pantalla Proyecto ya se ve como el lienzo.
- 1-oct 19:10 · T7 (historial de la ventanita) diseñada en el lienzo de la ventanita y
  escrita en este plan; espera el visto bueno.

## Notas para la terminal (lo que el panel ya espera)

El panel ya lee estas formas como opcionales; cuando el núcleo las sirva, aparecen solas:

- **A**: `cliente` en el libro, `cobrado` en cada fase, `detalle` en cada hito.
- **C**: `por_linea` en `GET /plata`.
- **D**: `GET /semana`. Mientras responda 404 el panel muestra el guion sin datos.
- **E**: `destacada` en cada fila de `GET /bandeja`; `POST /idea/{id}/destacar {destacada}`
  devuelve la fila (`IdeaBandeja`). Destacar una idea le quita la marca a la anterior.
- **F**: `GET /preguntas?tema=<tema>` (el panel siempre pregunta por un libro), y las dos
  rutas de respuesta tal como están arriba. El panel muestra la primera y guarda las demás
  para «Tengo otra pregunta»; después de «Responder» recarga `GET /libros/{tema}`.
- `POST /bloque {titulo, tema}` y `POST /libros/{tema}/camino/{n} {hecho}` ya se usan desde
  Proyectos, la pantalla de un proyecto y Metas: no cambiar su forma.

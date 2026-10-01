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
en el orden del líder. `POST /preguntas/{id}/respuesta {texto}` → `{pregunta, voz}`.
`POST /preguntas/{id}/despues` → `Pregunta`.

**G · Mensaje**: `RespuestaMensaje.tipo` suma `"agenda" | "cobro" | "entrega"`.

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
5. Línea base: `uv run pytest -q && uv run mypy .` (521) y `npm test` en la ventanita (86).

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

### T6 · Cierre
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
| J3 | Proyectos (3/6, tipo, fecha, Faltan, «Seguir con…», Obsidian, constelación) y la pantalla Proyecto | formas A y B para la barra de cobrado | pendiente |
| J4 | Metas: nombre y horizonte, botones, por línea, segunda meta dormida | forma C | pendiente |
| J5 | Bandeja: tema, «suelta», revisión en frío, destacada | forma E | pendiente |
| C2 | «Remi pregunta» en el lienzo y en el panel: la pregunta aparece donde falta el dato | forma F | pendiente |
| C3 | Semana contestada con datos | forma D | pendiente |
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

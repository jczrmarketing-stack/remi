# Plan de cierre — Remi

Escrito el 2-oct-2026 a las 22:00 (Bogotá), con `main` en `2248162`, 690 pytest, doctor 10/10,
Biblia v3.9. Lo mantiene **Claude en la app**; la terminal reporta en `docs/BITACORA.md`.

Este plan existe porque `docs/PLAN-100.md` ya se cumplió (T0–T11, T8, T9: ver bitácora del
2-oct). Lo que queda no es arquitectura: es cerrar lo que está a medias, afinar el carácter,
instalar y **usar**. Una sola mano en el código: ya no hay dos. Se trabaja en `main` directo.

## Qué es «terminada»

1. **Rápida, medida.** V1–V3 de `docs/ENCARGO-VELOCIDAD.md` cerradas con sus números en el log
   (V4 ya entró en `2248162`).
2. **Una persona, no un buscador.** `caracter.md` v1: de tú, con los dos registros (amigo y
   trabajo) sin botón, y sabiendo dónde está lo que sabe.
3. **Los libros sin huecos que una máquina pueda llenar.** Lo que solo sabe Juan Camilo lo
   pregunta Remi (fase Q), y la terminal comprueba que Remi lo pregunte.
4. **Instalada y vista corriendo.** `actualizar.sh` desde `main`, vitest en verde, instalar y
   desinstalar probados de verdad, panel contra las formas reales.
5. **Siete días de uso sin funciones nuevas.** Recién ahí el banco de pruebas (3f).

## Reglas (las de siempre, resumidas)

- Skill `/remi` cargada. Si algo contradice la Biblia v3.9, gana la Biblia; se anota y se sigue.
- **Una tarea = un commit**, `git add <rutas>` explícitas, nunca `-A`. Nada de llaves en git.
- Nunca borrar: ni notas de la bóveda ni filas de la base. Se archiva o se marca `fusionado_en`.
- Nunca datos de prueba en la base real ni en la bóveda real (`REMI_DB_PATH`, `REMI_CONOCIMIENTO`
  temporales). Ninguna prueba toca Telegram, Notion ni el puerto 4400.
- Sin IA donde hay reglas. Ninguna fase de este plan agrega una llamada a un modelo.
- Voz de Remi: de tú, sin voseo, sin contadores, sin urgir, sin culpa. Leyes 1–6 intactas.
- Cada «listo cuando» se comprueba corriéndolo, nunca «debería andar».
- Lo que no está en este plan **no se hace** (lista al final).

---

## F0 · Arranque (30 min)

1. Leer `CLAUDE.md`, este archivo, `docs/ENCARGO-VELOCIDAD.md`, las tres entradas de arriba de
   `docs/BITACORA.md` y `git log --oneline -15`.
2. `git worktree prune` (los once worktrees de `~/proyectos/remi-*` están `prunable`). No
   borrar las carpetas: solo limpiar el registro. Anotar en la bitácora cuáles quedaron sueltas
   para que Juan Camilo las borre a mano cuando quiera.
3. `git status`. Los cambios sin commitear en `nucleo/pensar.py`, `nucleo/servidor.py`,
   `apps/ventanita/src/{servidor,voz}.ts` y los archivos nuevos `envivo.ts`,
   `envivo.prueba.ts`, `test_mensaje_en_vivo.py` **son V3 en curso**. No se descartan: F1 los
   termina. Si hay algo más modificado que no sea eso, parar y anotar.
4. Commitear este plan: `git add docs/PLAN-CIERRE.md`.
5. Línea base: `cd nucleo && uv run pytest -q && uv run mypy .` y
   `cd apps/ventanita && npx tsc --noEmit && npm test`. Si vitest falla por lo de V3 a medias,
   no es bloqueo: es el punto 1 de F1. Anotar los números.

**Listo cuando:** worktrees limpios, plan commiteado, números de línea base en la bitácora.

## F1 · Velocidad (el grueso: ~1 día)

Todo está especificado en `docs/ENCARGO-VELOCIDAD.md`; aquí solo el orden y lo que cambia.
Orden: **V3 → V1 → V2** (V3 está a medias; se cierra primero para no dejar `main` sucio).

1. **V3 · streaming.** Leer el diff completo. Terminar lo que falte del punto 2 (ventanita
   consume el stream, `hablar()` encadena frases, la muletilla sigue primero) y del punto 3
   (línea de latencia en el log por turno de voz). Pruebas: `test_mensaje_en_vivo.py` y
   `envivo.prueba.ts` en verde, más una prueba de que si el stream se corta a mitad la
   ventanita cae a `/mensaje` sin decir nada. Commits por pieza: núcleo (`pensar_en_frases` +
   `/mensaje/stream`), ventanita (`envivo.ts` + consumo), instrumentación.
   **Listo cuando** lo que dice el encargo: con Groq `fin_habla→primer_sonido ≤ 2000 ms`; con
   Haiku `≤ 4500 ms`, leído del log en 5 turnos reales.
2. **V1 · dictado por trozos** (Rust, `voz.rs`), tal como está escrito. **Listo cuando** un
   dictado de ≥ 40 s deja el texto final < 1500 ms después de parar y la transcripción no
   empeora en el clip de 55 s.
3. **V2 · micrófono sin hueco**, **solo la opción (a)** (flags de ffmpeg). La opción (b) no se
   hace: Juan Camilo no la autorizó. Medir 20 arranques antes y después; reportar los dos
   números aunque no se llegue a 19/20.
4. `scripts/actualizar.sh`, probar los tres a mano en la app instalada, anotar en la bitácora
   la tabla «tramo · antes · después» con los milisegundos reales.

**Listo cuando:** los tres «listo cuando» del encargo cumplidos o, si V2 no llega, con el
número medido y el porqué; pytest, mypy, vitest en verde; app instalada desde `main`.

## F2 · El carácter v1: una persona (1–2 h)

`conocimiento/caracter.md` (enlace a `~/proyectos/remi-mente/caracter.md`) **es** el system
prompt de Remi y se lee en vivo: cambiarlo cambia a Remi sin reiniciar. Hoy es un borrador v0
en voseo; la Biblia y el encargo de velocidad dicen «de tú, nada de voseo». Se edita en la
bóveda con commit en el git de la bóveda (`boveda_git`), un commit por punto. Juan Camilo lo
corrige después a mano: lo que él escriba ahí manda.

1. **De tú.** Reescribir cada forma de voseo a tú («sos» → «eres», «tenés» → «tienes»,
   «hablás» → «hablas», «pensás», «decís», «leés», «sabés», «podés», «vos» → «tú»). Sin cambiar
   el sentido de ninguna línea. El encabezado pasa de «borrador v0» a «v1 · 2-oct».
2. **Sección nueva «Dos registros, sin botón»**, literal, después de «Cómo hablas»:

   > ## Dos registros, sin botón
   > No hay modo trabajo ni modo personal que él tenga que elegir. Lo lees en lo que te dice,
   > como cualquier amigo.
   >
   > Charla: te cuenta algo, pregunta qué opinas, piensa en voz alta, te saluda, quiere
   > compañía para pensar. Aquí eres el amigo: escuchas de verdad, reaccionas con lo que
   > piensas (te impresiona o no, y dices por qué), conectas con lo que ya sabes de él, y no
   > conviertes nada en tarea ni en encargo salvo que él lo pida. Una charla no abre ideas ni
   > bloques: eso ya lo decide el núcleo, no tú. Si de la charla sale algo que vale guardar,
   > lo dices en una frase («esto lo anoto») y sigues.
   >
   > Trabajo: te pide un encargo, un prompt, una decisión sobre un proyecto, qué sigue, cuánto
   > falta, qué le contesta a un cliente. Aquí eres el socio que sabe el oficio: lees el libro
   > del proyecto antes de opinar, traes las lecciones que aplican, propones el paso con su
   > «listo cuando», y frenas si el cambio es grande y no hay plan.
   >
   > Cuando dudes, es charla. Pasar a trabajo lo decide él con lo que pide, no tú con lo que
   > crees que debería estar haciendo. Lo contrario sí vale: en medio de un encargo puedes
   > salirte un segundo a decirle algo de amigo (que lleva tres horas, que eso ya lo resolvió
   > una vez) sin cambiar de tono.

3. **Sección nueva «Dónde está lo que sabes»**, literal, antes de «Las seis leyes»:

   > ## Dónde está lo que sabes
   > Tu memoria no es esta conversación: es la bóveda. En la mente llevas siempre los títulos
   > (el índice que viaja contigo). Cuando algo toca un proyecto, abres su libro
   > (`proyectos/<tema>.md`): ahí están su Estado, su Camino y las reglas de ese proyecto. Cómo
   > se hace algo está en los oficios. Lo que ya salió mal y cómo se arregló, en
   > `experiencia/`: `buscar_lecciones` antes de proponer un arreglo. Lo que hablaron antes, en
   > `episodios/` y con `buscar_memoria` cuando no está en el índice. Si no está en ningún
   > lado, no lo sabes: lo preguntas o lo dices. Nunca lo inventas.

4. En «Lo que nunca haces», agregar una línea: «Rehacer lo que Claude ya hace bien
   (investigar largo, navegar, conversaciones enormes con imágenes): eso lo mandas allá con el
   prompt listo y guardas el resultado.»
5. Comprobar en el código, con una prueba si no existe, que `pensar.sistema_encargo()` (el
   registro trabajo) lleva el carácter **más** los oficios `prompting`, `claude-code`, `stack`
   y `vibe-coding`, las «Reglas de este proyecto» (T9.2) y hasta tres «Ojo:» (T8.7); y que el
   camino de charla lleva el carácter y el índice pero no los oficios. Si falta algo, es un
   bug y se arregla; si está, solo la prueba y una línea en la bitácora.

**Listo cuando:** `grep -cE '\b(sos|tenés|podés|hablás|pensás|decís|leés|sabés|vos)\b'
~/proyectos/remi-mente/caracter.md` da 0; las dos secciones están; tres commits en la bóveda;
y a mano, en la ventanita: «¿qué opinas de que haga esto el fin de semana?» responde como
amigo sin crear nada, y «arma el encargo para el endpoint de pagos de UpVisuals» responde con
forma de encargo y «listo cuando».

## F3 · Los libros: lo que la máquina puede llenar (1–2 h)

Solo en la bóveda, solo agregando, un commit por libro. Lo que es de Juan Camilo no se inventa.

1. **`ruta:` de los siete libros contra el disco.** Para cada libro de `proyectos/`, comprobar
   que cada ruta en `ruta:` existe en el Mac. Candidatas reales que hoy pueden faltar:
   `~/organic-cash`, `~/Organic-Cash-Brain`, `~/organic-bot-core` (organic-cash);
   `~/proyectos/malik-gestion` (malik); `~/beam`, `~/beam-notifications`,
   `~/beam-admin-preview` (beam). Agregar solo rutas que existan y cuyo nombre diga a qué
   libro van; si una no es obvia, no se agrega: se deja como pregunta (`libro.ruta`) para Remi.
2. **Episodios repetidos.** Los dos `2026-09-30-el-agente-de-investigar-en-malik-gestion…`
   (`.md` y `-2.md`) son el mismo: fusionarlos con la regla de T8.3 (`fusionado_en:` en el que
   sobra, nunca borrar). Correr la misma revisión sobre todo `episodios/` y anotar cuántos
   quedaron fusionados.
3. **Comprobar que Remi pregunta lo que falta.** Con la bóveda real y el núcleo real, de solo
   lectura: `GET /preguntas` y `GET /preguntas?tema=<cada tema>` tienen que cubrir, entre
   todas (nunca más de tres a la vista): el `(Completar: …)` de `areas/aprender.md`,
   `areas/finanzas.md`, `areas/negocios-y-planes.md`, `areas/salud.md`,
   `proyectos/beam.md` (cliente), `proyectos/shopify-cliente.md`, `oficios/mi-voz.md` y
   `oficios/clientes.md` (piso de precio). Si alguno no lo detecta `preguntas.py`, es un bug
   del detector `completar.N` y se arregla con prueba. **No contestar ninguna.**
4. **`experiencia.py --reindexar`** contra la base real y comprobar
   `GET /experiencia?tema=remi&q=EADDRINUSE` trae la lección del puerto.

**Listo cuando:** las rutas existen en disco; cero episodios duplicados sin `fusionado_en`;
las ocho preguntas aparecen por `GET /preguntas` (en el orden del líder, de a tres); el índice
de experiencia contesta.

## F4 · Producción de verdad (2–3 h)

1. **Instalar y desinstalar de punta a punta** (BLOQUEADO 1 de T6, nunca corrido). Antes:
   `bash scripts/copia.sh`. Después: `desinstalar.sh` → comprobar que no queda ningún
   `com.remi.*` en `launchctl list` → `instalar.sh` → los diez agentes de vuelta →
   `doctor.sh` 10/10 → la app abre y contesta. Anotar la duración real.
2. **Las pruebas no tocan el mundo real.** Comprobar que T5.9 quedó hecho: una guarda que hace
   fallar la suite si alguna prueba intenta llegar a Telegram, Notion o `127.0.0.1:4400`, y
   que `test_noche.py` no manda avisos. Si la guarda no existe, se escribe (un doble de prueba
   y un `conftest` que la impone). Si existe, solo se anota.
3. **`test_noche.py` sin mtime frágil** (T5.6): comprobar `os.utime` fijo; tres corridas
   seguidas en verde.
4. **Vitest de la ventanita** al día (los commits del 2-oct quedaron con `tsc` pero sin correr
   las pruebas): 97 + lo de V3, en verde.
5. **Oficios como skills, de verdad.** `scripts/oficios_a_skills.py` corre en dry-run por
   defecto: correrlo con `--si` y comprobar `~/.claude/skills/remi-oficio-*/SKILL.md` (uno por
   oficio). Dejar anotado el comando para repetirlo cuando un oficio cambie (o agregarlo al
   final de la consolidación nocturna si es una línea).
6. **Los ganchos están puestos.** Comprobar `git config --global core.hooksPath` apunta a
   `scripts/hooks` y que `~/.claude/settings.json` tiene los hooks `SessionStart`, `Stop` y
   `SessionEnd` del plan (T3d). Si falta alguno, instalarlo con `scripts/instalar.sh` o a
   mano, y que `doctor.sh` lo revise de ahí en adelante (si cabe en «10 piezas» sin
   renumerar, dentro de la pieza de LaunchAgents; si no, pieza 11 y el mensaje pasa a 11/11).
7. **El panel contra las formas reales** (C4, pendiente de la otra mano). De solo lectura
   contra el núcleo real: `GET /libros/upvisuals` (forma A: `cliente`, `cobrado` por fase,
   `detalle` por hito), `GET /plata` (C: `por_linea`), `GET /semana` (D), `GET /bandeja` (E:
   `destacada`), `GET /preguntas?tema=upvisuals` (F). Comparar cada respuesta con la forma
   escrita en `docs/PLAN-100.md`; lo que difiera es `CAMBIO DE FORMA` en la bitácora y se
   decide si cambia el núcleo o el panel (el panel ya está construido contra esas formas: lo
   normal es que cambie el núcleo). Mirar las siete pantallas del panel en el navegador a
   1280 y 375 px y anotar lo que se vea distinto del lienzo: eso lo arregla Claude en la app.

**Listo cuando:** instalar/desinstalar probados con `doctor.sh` 10/10 al final; la suite no
puede tocar el mundo real; vitest y pytest en verde tres veces seguidas; oficios en
`~/.claude/skills`; ganchos verificados; formas A–F comparadas en la bitácora.

## F5 · Cierre (30 min)

1. `scripts/actualizar.sh` desde `main`. `doctor.sh`. `curl /salud`.
2. Entrada de cierre en la bitácora: hash por fase, números finales de pruebas, la tabla de
   velocidad antes/después, lo BLOQUEADO, lo que vio distinto en el panel, y la lista de abajo
   («lo que solo puede hacer Juan Camilo» y «después de los siete días») **sin empezar nada**.
3. `/compact`. Fin.

---

## Lo que solo puede hacer Juan Camilo

1. **Antes de pegar el mega prompt:** cerrar cualquier otra sesión (Claude en la app o
   terminal) que esté tocando `main`. El V3 sin commitear lo termina esta terminal.
2. **Contestarle a Remi** cuando pregunte: el cliente de BeaM, cuánto pagó Alfonso, los «listo
   cuando» de UpVisuals, las cuatro áreas (aprender, finanzas, negocios y planes, salud), el
   piso de precio por fase, y pegarle 5–10 mensajes reales a clientes para «mi voz». Por la
   ventanita o por Telegram; una pregunta a la vez.
3. **Leer `caracter.md` v1 y corregirlo a mano.** Es su amigo: lo que escriba ahí manda, y
   Remi cambia al instante.
4. Cloudflare: Access delante del túnel y después `cloudflared tunnel login`.
5. Rotar las cuatro llaves desde Ajustes → Conexiones → Probar.
6. `pmset` y el UPS de la Mac mini.
7. **Siete días de uso real** (del 4 al 10 de octubre), un cliente, sin pedir funciones nuevas.
   Bugs a la ventanita. **Revisión semanal el lunes 12** desde el panel. Ahí se cierra Remi.

## Lo que NO se hace en este plan (a propósito)

- Vectores o modelos de embeddings nuevos (lo que hay alcanza; se mide en 3f).
- 3f banco de pruebas, 2e.1, 2e.2 (después de los siete días).
- V2 opción (b) (micrófono caliente): toca privacidad, sin orden de Juan Camilo.
- «Pensar en voz alta» (solo si V3 no alcanza, y con cifras).
- Notion de vuelta (al mes de uso). App nativa de iOS (la PWA es la decisión).
- Un botón o chip de modo (el registro es implícito; el semáforo ya elige cerebro).
- El ritual de la mañana como pantalla (BLOQUEADO 2 de T6: se diseña primero en el lienzo,
  después de los siete días).
- Cualquier función que no esté escrita arriba.

## Registro

- 2-oct 22:00 · plan escrito con `main` en `2248162`. Falta: F0–F5.

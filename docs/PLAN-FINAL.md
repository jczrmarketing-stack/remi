# Plan final — Remi al 100 %

Escrito el 4-oct-2026 a las 03:10 (Bogotá), con `main` en `789cfea` y la Biblia en **v4.2**.
Lo mantiene **Claude en la app**: marca cada fase cuando la verificó. La terminal no lo edita;
reporta en `docs/BITACORA.md`, como siempre.

`docs/PLAN-100.md` (T0–T11) y `docs/PLAN-CIERRE.md` (F0–F5) ya se cumplieron, y la revisión
R0–R6 (`docs/REVISION.md`) está cerrada. Este plan es lo que queda: lo que la revisión dejó por
construir, **Hoy que se actualiza sola**, la **ficha de cliente**, el **Rumbo** (Parte IX) y la
fase **PR** (del encargo a producción). Al final, la semana de uso.

## Qué es «100 %»

1. **Hoy se actualiza sola.** Juan Camilo no marca nada: Remi sabe en qué va (Al día), los
   hitos se cierran con evidencia, y Remi lo busca solo en los tres casos que importan.
2. **Cada cliente tiene su ficha llena sola**: cobrado, gastado, tiempo, lo que queda por hora,
   dónde va, lo acordado y lo que pasó.
3. **El Rumbo funciona**: visión → meta y escalera → cuenta hacia atrás semanal → Hoy dice qué
   va primero y por qué; caminos investigados con fuentes, números calculados en código,
   pronósticos que se califican y corrigen.
4. **Nada se sale de control**: tope de gasto en los motores, latido si algo deja de registrar.
5. **Lo que entrega la IA se revisa** antes de llegar a un cliente (fase PR).
6. **Instalada, en el iPhone, y usada siete días** sin funciones nuevas. Ahí se cierra.

## Decisiones ya tomadas (4-oct)

- Hoy (tableros 1–5 del canvas «Hoy que se actualiza sola») y Rumbo (tableros 6–10) están
  **aprobados** como dirección; la Biblia v4.2 los describe (Parte III «Hoy, desde v4.2» y
  Parte IX). Las formas J–S de abajo son el contrato: aprobarlo es aprobar este plan.
- Lo que difería en la revisión R6, resuelto por defecto (Juan Camilo puede cambiarlo):
  **45 min** entre dos avisos; la ventanita **se apila** como cualquier ventana; el modo se
  elige con **el chip**. La Biblia v4.2 ya lo dice.
- **La semana de uso se corre al final.** La regla de «siete días sin funciones nuevas» sigue
  valiendo, pero Juan Camilo decidió construir primero lo que hace que Remi sirva (Hoy y Rumbo);
  el reloj de los siete días arranca en la fase Z.
- «Después de T0–T6» (lo que pedía el diseño del Rumbo) ya se cumple: T0–T11 están hechas.
- Una sola mano en el código: **la terminal**, en `main` directo, panel incluido. Claude en la
  app diseña, verifica, mantiene la Biblia y este archivo.

## Reglas (las de siempre)

- Skill `/remi` cargada. Si algo contradice la Biblia v4.2, gana la Biblia; se anota y se sigue.
- **Una tarea = un commit**, `git add <rutas>` explícitas, nunca `-A`. Nada de llaves en git.
- Nunca borrar notas de la bóveda ni filas de la base: se archiva o se marca `fusionado_en`.
- Nunca datos de prueba en la base real ni en la bóveda real (`REMI_DB_PATH`, `REMI_CONOCIMIENTO`
  temporales). Ninguna prueba toca Telegram, Notion, la web ni el puerto 4400.
- **Sin IA donde hay reglas.** Leer montos, fechas, gastos, evidencia de un hito, la cuenta
  hacia atrás, la simulación y la calibración son código puro con pruebas. Un modelo solo
  redacta, investiga o estima; **nunca pone el número final** ni decide qué es verdad.
- Los contratos se cambian en `contratos/contratos.json` y se generan los tipos; nada a mano.
- Voz de Remi: de tú, sin voseo, máximo 20 palabras, sin contadores, sin urgir, sin culpa.
- Panel: tokens de `design/tokens.json`, componentes canónicos, escritorio y 375 px; Playwright
  ahora sí lo corre la terminal (ya no hay otra mano usando sus puertos).
- Cada «listo cuando» se comprueba corriéndolo, nunca «debería andar».
- Lo que no está en este plan **no se hace**.

## Cómo cierra cada fase

1. Entrada nueva ARRIBA en `docs/BITACORA.md` (qué cambió, decisiones sin preguntar, dudas,
   cómo probarlo a mano). Si una forma salió distinta: primera línea `CAMBIO DE FORMA: …`.
2. `cd nucleo && uv run pytest -q && uv run mypy .` · `cd apps/ventanita && npx tsc --noEmit &&
   npm test` · `cd apps/panel && npm test` (Playwright) — todo en verde.
3. `bash scripts/actualizar.sh` si la fase tocó la ventanita; `launchctl kickstart -k
   gui/$(id -u)/com.remi.nucleo` si tocó el núcleo; `bash scripts/doctor.sh` 10/10.
4. Comprobar el «listo cuando» contra el sistema real con GET de solo lectura, o en pytest si
   habla de comportamiento.
5. `/compact` y la fase siguiente, sin preguntar.

---

## Las formas nuevas (contrato entre núcleo y panel)

**J · Al día** — `GET /hoy/aldia` →
`{estamos_en: {tema, fase_n, paso} | null, lo_ultimo: {texto, hace_min, evidencia: {tipo:
"commit"|"pruebas"|"sesion"|"mensaje"|"cobro"|"decision", ref}} | null, sigue: {texto,
borrador: string | null} | null, mientras_no_estabas: [{texto, tema, hora, evidencia}]}`.
`mientras_no_estabas` trae lo ocurrido desde la última vez que se abrió el panel o la
ventanita (máximo 5), vacío si fue hace menos de 2 h.

**K · Hito con evidencia** — cada hito de `GET /libros/{tema}` suma `cerrado_por: {tipo, ref,
en} | null`. `POST /libros/{tema}/camino/{n}/deshacer` → el libro. Un hito cerrado solo
también deja una línea en `lo_ultimo` y dispara la celebración en el panel (una vez).

**L · Avisos** — `config/avisos.json`: `{suenan: ["terminal_termino","foco_25","desvio"],
max_dia: 5, entre_min: 45, noche: [23, 7], telegram: true}`. Tabla `avisos (id, tipo, texto,
canal, creado, respuesta: "volver"|"ahora_no"|null)`. `GET /avisos/hoy` → los de hoy (solo
para el panel; nunca se muestra como contador).

**M · Gastos** — `POST /gastos {tema | null, monto, concepto, fecha?}` → 201 `Gasto`
(`tema: null` = gasto común). `GET /libros/{tema}` suma `gastado`, `gastos: [{concepto,
monto}]` (agrupado), `minutos_total`, `minutos_estimados | null`, `por_hora | null` (cobrado −
gastado − parte de comunes, ÷ horas). `GET /plata` suma `gastos_comunes_mes`. Los comunes se
reparten entre proyectos por minutos del mes.

**N · Partida, meta y escalera** — `GET /rumbo` →
`{vision: {texto, fecha} | null, meta: {piso, techo, meses_seguidos, concentracion_max,
limites} | null, escalera: [{n, texto, criterio, estado: "conquistado"|"ahora"|"sigue"|
"luego"|"norte"}], partida: [{tipo: "recurso"|"habilidad"|"cuesta"|"preferencia", texto,
valor, origen: "medido"|"dicho"|"pregunta", dominio: "cirujano"|"sabe"|"aprendiz"|null}],
progreso: {estable_mes, meses_buenos, cliente_mayor_pct}}`.
`POST /rumbo/vision {texto}` → `{propuesta: meta, voz}` (la meta no cambia hasta
`POST /rumbo/meta {…, confirmada: true}`).

**O · Apuestas** — `GET /rumbo/apuestas` → `[{id, camino, inicio, fin, tope_horas,
tope_plata, gastado_horas, gastado_plata, senal_sigue, senal_pausa, progreso: {hecho, meta},
resultado: null|"sigue"|"pausa"|"extender"}]`. `POST /rumbo/apuestas` (desde un camino
analizado) · `POST /rumbo/apuestas/{id}/cerrar {resultado, metrica_nueva?}`. A los 60 días,
una `Pregunta` «¿la volverías a hacer?».

**P · Pronósticos** — `POST /pronosticos {que, p, vence, regla_si_no, tipo: "mundo"|
"conducta", origen}` · `POST /pronosticos/{id}/resolver {resultado: true|false|null}` ·
`GET /calibracion` → `{resueltos, sesgo_si | null, sobreconfianza | null, muestra_grafica:
resueltos >= 20, por_tipo}`. Recalibra desde 10 resueltos.

**Q · Caminos** — `POST /rumbo/caminos {idea_id}` (una idea que pasó 48 h en la Bandeja) →
202 `{id}`; el análisis corre en segundo plano. `GET /rumbo/caminos/{id}` →
`{estado: "investigando"|"listo"|"falló", mercado, competidores, juego, a_favor, en_contra,
dominio, base: {texto, fuente_id}, bandas: {probable, posible, techo}, frecuencia: {de_10,
umbral}, ruina_de_10, ajuste: {de_10, tamano}, palancas, objeciones, prueba, fuentes: [{id,
url, fecha, fragmento, verificada}]}`.

**R · Cuenta hacia atrás** — `GET /rumbo/cuenta` → `{meta_mes, ticket, necesarias, tienes,
cierre: {p, base_n, origen}, propuestas_semana, hechas_semana, horas_semana: [{camino, pct}]}`.

**S · Reloj** — `GET /reloj/estimar?tipo=&min=` → `{p50, p80, p95, n, tipo}` (velocidad =
estimado ÷ real de las tareas de ese tipo, últimos 6 meses; con menos de 6, historial amplio
por defecto). `GET /rumbo/latido` → `[{pieza, ultimo_dato, callado_dias}]`.

---

## Fases de la terminal

Tamaño: S ≈ 1–2 h · M ≈ medio día · L ≈ un día.

### B0 · Arranque (S)
1. Leer `CLAUDE.md`, este archivo, `docs/BIBLIA.md` (v4.2: Parte III «Hoy, desde v4.2» y
   Parte IX completa), las tres entradas de arriba de la bitácora, `git log --oneline -15`.
2. Commitear `docs/BIBLIA.md` (v4.2, ya en el árbol) y este plan, cada uno en su commit. Copiar
   la Biblia idéntica a la bóveda `referencia/biblia.md` con su commit allá.
3. `CLAUDE.md`: la línea de vistas del panel suma Semana y Rumbo; «Una fase a la vez» apunta a
   este plan.
4. Línea base de las tres suites; anotar números.

**Listo cuando:** la bóveda y el repo tienen la Biblia v4.2; números de línea base en la bitácora.

### B1 · Tope de gasto (S)
Lo primero que pidió la revisión R6: nada frena un gasto en Groq, OpenRouter, Venice o una API.
1. `config/gasto.json`: `{tope_dia_usd, tope_mes_usd, activo}`; tabla `gasto_motor (fecha,
   motor, modelo, tokens_in, tokens_out, usd)`, con precios en `config/motores.json`.
2. Antes de cada llamada pagada, si se pasa: no llama; usa el respaldo gratis (Groq → Ollama) y
   la ventanita muestra el chip real. Claude por Max no cuenta (no cobra aparte).
3. Ajustes del panel: el número y el interruptor. `doctor.sh` avisa al 80 %.

**Listo cuando** (pytest): con tope 0,01 USD una llamada a OpenRouter no sale y el turno lo
contesta el respaldo; el conteo del mes es la suma de la tabla.

### B2 · Al día: Remi sabe en qué vas (L)
Diagnóstico: Hoy no sabe qué está haciendo la terminal ni qué pasó mientras Juan Camilo no
estaba. Las piezas existen (ganchos de git, `SessionStart`/`SessionEnd` de Claude Code,
episodios, turnos, memoria MCP), pero nadie las junta.
1. `nucleo/aldia.py`, función pura sobre eventos: commits (gancho), sesiones de Claude Code
   abiertas y cerradas (con su `cwd` → libro por `libros.por_ruta`), corridas de pruebas,
   cobros, mensajes clasificados, y decisiones guardadas por el MCP. Arma la forma J.
   `estamos_en` = el libro con actividad más reciente en las últimas 3 h y su hito actual;
   `sigue` = el hito siguiente del Camino.
2. Evento nuevo «terminal trabajando»: una sesión de Claude Code abierta sobre un libro, con
   minutos desde que empezó. El panel lo muestra como «La terminal está en esto desde hace N
   min».
3. `borrador`: si el paso siguiente es un mensaje a un cliente (hitos del SOP «avisar»,
   «mandar avance», «cobrar»), Remi redacta el mensaje con `pensar` en la voz de Juan Camilo y
   lo guarda; se pide una vez por hito, no en cada GET.
4. MCP de memoria (`memoria_mcp.py`): `guardar` acepta `tipo: "decision"` y `tema`; entra como
   evento para Al día y para la ficha. Texto de la instrucción para los proyectos de Claude en
   el escritorio en `docs/INSTRUCCION-CLAUDE-ESCRITORIO.md` (tres líneas: al decidir algo de un
   proyecto, `guardar` con su tema y `tipo: decision`).
5. Forma J. Pruebas con una línea de tiempo sintética: commit, pruebas en verde, cierre de
   sesión, cobro, decisión.

**Listo cuando:** en pytest, tras un commit y pruebas en verde en el repo de un libro,
`lo_ultimo.evidencia.tipo == "pruebas"`; con 3 h sin abrir, `mientras_no_estabas` trae lo
ocurrido; contra el núcleo real, `GET /hoy/aldia` responde con el libro en que se trabajó hoy.

### B3 · Los hitos se cierran solos (M)
1. Cada hito del SOP gana `cierra_con` en `caminos.py`, a mano junto a `paso_remi`: `encargo`
   (una sesión de Claude Code nacida de un encargo de ese hito cierra con commits y pruebas en
   verde), `mensaje` (Juan Camilo dice que lo mandó: «ya le mandé el avance a Alfonso»),
   `cobro` (un cobro del proyecto), `pregunta` (lo confirma contestando en el panel).
2. Los encargos que arma Remi llevan `hito: <tema>#<n>` en su encabezado; el gancho
   `SessionEnd` lo lee del primer turno.
3. Sin evidencia no se cierra. Evidencia dudosa (commits sin pruebas, mensaje sin cliente
   reconocible) → una `Pregunta` en el panel, no un cierre.
4. Forma K: `cerrado_por` y `deshacer` (vuelve el hito y su commit de bóveda queda revertido
   con otro commit, nunca borrado).

**Listo cuando** (pytest): un encargo con `hito: upvisuals#5` que cierra con commit y pruebas en
verde deja el hito 5 hecho con `cerrado_por.tipo == "encargo"`; `deshacer` lo devuelve;
«ya le mandé el avance a Alfonso» cierra el hito de avance de UpVisuals y no el de BeaM.

### B4 · La pantalla nueva de Hoy (L)
Del canvas, tableros 1 a 3, escritorio y 375 px.
1. Bloque «Al día» arriba (tres líneas mono). Si `mientras_no_estabas` trae algo: la frase en
   serif y la tarjeta «Mientras no estabas» (tablero 3).
2. Tarjeta principal: acción en serif, una línea de por qué (por ahora del Camino; en R5, del
   Rumbo), «la última vez algo así te tomó N min», «Empezar con eso» / «Otra cosa primero».
   Si la terminal trabaja: la línea en vivo. Si hay `borrador`: el mensaje y «Copiar mensaje».
3. Hito cerrado solo: la tarjeta luz con la celebración de 900 ms (una vez por hito), «lo cerré
   por …» y «deshacer» (tablero 2).
4. «Después, si queda tiempo» y «Vence» como hoy, máximo tres filas.
5. Lo que ya no va: el botón de cerrar hito a mano como acción principal (queda en la pantalla
   del proyecto) y el texto «paso mínimo» sin explicación.

**Listo cuando:** Playwright cubre los tres estados (en curso, cerrado solo, ponerse al día) en
escritorio y 375 px; con el núcleo real, Hoy muestra el libro de hoy y su paso.

### B5 · Avisos que jalan la atención (M)
1. `nucleo/avisos.py` sobre el presupuesto de `iniciativa.py`: tres casos con sonido —
   `terminal_termino` (cierra la sesión de un encargo), `foco_25` (25 min de bloque),
   `desvio` (sesión de Claude Code o actividad en otro libro por más de 30 min mientras hay un
   bloque abierto con fecha prometida; la accesibilidad de macOS lo afinará en B10). Lo demás,
   callado. Forma L.
2. Ventanita: sonido corto (uno solo, del sistema) y la tarjeta con «Volver» / «Ahora no».
   «Ahora no» no se cuenta y ese aviso no vuelve igual ese día.
3. Telegram: los mismos avisos, y lo que se contesta ahí («ya se lo mandé. qué sigue?») pasa por
   `/mensaje` y puede cerrar el hito (B3).
4. Máximo 5 al día, 45 min entre dos, nunca mientras escribe, noche callada 11 p – 7 a.

**Listo cuando** (pytest con reloj falso): seis avisos el mismo día → salen cinco; uno a las
23:30 no sale; dos con 20 min de diferencia → sale uno; «Ahora no» al desvío lo calla el resto
del día.

### B6 · La ficha de cliente (L)
Del canvas, tablero 5.
1. `nucleo/gastos.py`, función pura como `cobros.py`: «gasté 40 en el servidor de UpVisuals»,
   «pagué 20 del dominio», «la membresía de Claude: 100 al mes» (sin proyecto → común). Si no
   reconoce el proyecto y no es común claro, no adivina: `Pregunta`. Forma M.
2. Tiempo: minutos de sesiones del libro (ya existen) más los de Claude Code en sus rutas;
   `minutos_estimados` se pregunta una vez por fase (T3 ya pregunta campos).
3. «Lo acordado»: decisiones (`tipo: decision`) y entregas futuras del libro. «Lo que pasó»:
   las últimas 6 líneas de evidencia (cobro, hito, decisión, demora) con su origen.
4. «Remi está atento a»: una línea por reglas (horas contra estimado, hitos que faltan, alcance
   nuevo = Fase siguiente). Sin IA.
5. Panel: la ficha en la pantalla del proyecto para libros `tipo: cliente`; cada número se toca
   y se corrige (escribe con su commit o su fila).

**Listo cuando:** «gasté 40 en el servidor de UpVisuals» deja `gastado` en 40 y `por_hora`
recalculado; la ficha se ve como el tablero 5 en escritorio y 375 px; corregir un número a mano
queda.

### B7 · Hilos por tema (M)
De la revisión R6: al saltar de proyecto en medio de una charla, Remi anota qué quedó a medias
(«en UpVisuals quedaste en el mensaje a Alfonso») y lo devuelve al volver a ese tema, una vez.
Sin IA para detectar el salto (`temas.tema_de_texto` ya existe).

**Listo cuando** (pytest): charla de UpVisuals → salto a Malik → vuelta a UpVisuals: el primer
turno de vuelta trae el hilo una sola vez.

---

### R1 · Rumbo: visión, meta, escalera y punto de partida (L)
Biblia Parte IX. Formas N.
1. Tablas `vision`, `meta`, `escalon`, `partida`. Archivo de visión en la bóveda
   `rumbo/telos.md` (misión, metas, problemas, estrategias, métricas — forma TELOS), con
   commit; es lo que el motor lee siempre.
2. `POST /rumbo/vision`: guarda el texto literal; extrae monto, plazo, «estable» y límites (el
   modelo redacta, una función pura valida números); devuelve la propuesta y la voz «Entendí:
   …»; pregunta lo que falta, una a la vez, máximo cuatro, como `Pregunta`. La meta cambia
   solo con `confirmada: true`.
3. Punto de partida: lo medido sale solo (horas por semana de las sesiones, tasa de cierre de
   las propuestas registradas, proyectos entregados, concentración por cliente de los cobros);
   lo dicho se pregunta; `dominio` por habilidad sale de reglas sobre la evidencia (p. ej.
   ≥ 5 proyectos entregados = cirujano; 1–4 = sabe; 0 = aprendiz).
4. Escalera: el norte y los escalones los dice Juan Camilo; al sostener el escalón actual tres
   meses (de `plata`), Remi propone el siguiente como `Pregunta`; con el sí, celebra.
5. Panel: pestaña Rumbo con escalera arriba, botón «Contar mi visión» (voz y texto) y el tablero
   8 (punto de partida) como pantalla aparte.

**Listo cuando** (pytest + real): contar «quiero 10 a 15 mil al mes, seis meses seguidos» deja
una propuesta y no cambia la meta hasta confirmar; `GET /rumbo` trae la partida con las horas
medidas reales; la pestaña se ve como los tableros 6 y 8.

### R2 · Reloj, cuenta hacia atrás, apuestas y el domingo (L)
1. Reloj (EBS de Spolsky): `nucleo/reloj.py`, velocidad por tipo de tarea, simulación sembrada,
   forma S. Ley 1 pasa a decir «dijiste 30 → probablemente 50, a lo sumo 80». Ningún paso de Hoy
   pasa de ~90 min: si el estimado es mayor, Remi lo parte (pregunta o encargo).
2. Cuenta hacia atrás (forma R): meta ÷ ticket → mensualidades necesarias; tasa de cierre propia
   primero (con menos de 5 propuestas, base general marcada); propuestas por semana. Registrar
   propuestas: «le mandé la propuesta a X por 1.500» (función pura).
3. Apuestas (forma O): nacen de un camino analizado (R3) o a mano; tope de horas y plata,
   señales, días. Al día 14: `Pregunta` con tres salidas — sigue, pausa, extender una vez con
   métrica más estrecha. A los 60 días: «¿la volverías a hacer?».
4. Domingo: en Semana, revisión de 10 min — qué entró, qué apuesta sigue, reparto de horas de la
   semana siguiente (barra). Una sola notificación el domingo a la hora que diga Juan Camilo.
5. Panel: tablero 6 completo (cuenta, horas, apuestas, jugadas sin perder) y Semana con la
   revisión (diseño D1 de Claude en la app).

**Listo cuando:** con 8 propuestas y 2 cierres registrados, `GET /rumbo/cuenta` da cierre 0,25 y
propuestas por semana coherentes con la meta; `GET /reloj/estimar` con 10 tareas reales da
p50 > estimado si la velocidad es < 1; una apuesta al día 14 produce la pregunta de tres salidas.

### R3 · Ábreme el juego y el análisis de un camino (L)
1. «Ábreme el juego»: genera 20 jugadas con muestreo verbalizado y los lentes de la Parte IX;
   cada una cita evidencia de la partida; el código descarta repetidas (similitud) y palabras de
   moda (lista en `config/rumbo.json`); una siempre cuestiona la meta. Van a la Bandeja con
   `origen: rumbo`; ley 6 intacta.
2. Análisis de un camino (forma Q), en segundo plano: investigación con búsqueda web (Claude
   con su herramienta de búsqueda; comprobar en la documentación de Claude Code cómo se
   habilita en `claude -p` y anotarlo) desde varias miradas (estilo STORM); mercado de abajo
   hacia arriba con la cuenta en Python; competidores con precio y flanco; el juego (jugadores,
   incentivos, reacción); a favor y en contra desde la partida.
3. Fuentes verificadas: cada fragmento con id; cada cifra cita un id que el código comprueba que
   existe; un modelo barato confirma que el fragmento dice eso; si no, la cifra se marca
   `supuesto`. Cada cifra guarda URL, fecha y tipo.
4. Costo: cuenta contra el tope de B1; un análisis completo por camino, re-investigación mensual.
5. Panel: tablero 7.

**Listo cuando:** con una bóveda y web dobles en pytest, el análisis llega a `listo` con fuentes
verificadas y una cifra sin fragmento queda como `supuesto`; contra el real, un camino de prueba
elegido por Juan Camilo se analiza completo y se ve como el tablero 7.

### R4 · Números honestos: estimar, juntar, criticar, simular, calibrar (L)
1. Estimación a ciegas: tres modelos de familias distintas (Claude, uno de Groq, uno de
   OpenRouter), sin saber qué prefiere Juan Camilo; la probabilidad de falla en llamada aparte;
   un modelo separado extrae el número del razonamiento.
2. Juntar en código: mediana, sin extremizar; mezcla con tasa base y estimación de Juan Camilo
   con pesos fijos en `config/rumbo.json`.
3. Crítica después de fijar: anónima (Respuesta A/B/C) + abogado del diablo con mínimo tres
   problemas; segunda ronda a ciegas solo si la crítica cambia un supuesto.
4. Simulación (numpy sembrado) de seis meses → bandas probable/posible/techo, «N de 10», ruina
   aparte, ajuste con su tamaño. Kelly solo como tope, con la probabilidad recalibrada.
5. Pronósticos (forma P): todo número que se muestra queda guardado con su regla de sí/no;
   recalibrador logístico copiado de `Metaculus/forecasting-tools`
   (`calibration_adjustment/logistic_recalibration_adjuster.py`, MIT, con su aviso de licencia)
   desde 10 resueltos; conducta propia aparte; gráfica desde 20.

**Listo cuando** (pytest): con tres estimaciones dobles 0,2 / 0,3 / 0,9 la mediana es 0,3; con
30 pronósticos sintéticos sesgados al sí, el recalibrador baja las probabilidades y
`sesgo_si > 0`; la simulación con la misma semilla da las mismas bandas.

### R5 · Hoy ordenado por el Rumbo, latido y poda (M)
1. Orden de Hoy: (1) fecha prometida; (2) lo que cumple la cuenta de la semana o el paso de una
   apuesta; (3) empate: más meta estable por hora medida (mensualidad > pago único; bajar
   dependencia suma). Una línea de por qué; si no se puede justificar, por fecha. Una sola cosa.
2. Latido (forma S): si el reloj, los pronósticos o la cuenta no reciben datos en 2 días, un
   aviso callado, una vez, sin culpa.
3. Poda mensual: Remi mira qué partes del Rumbo se usaron y propone quitar las que no
   (`Pregunta`).
4. Proyectos: cada libro muestra su aporte a la meta y su costo frente a ella (diseño D1).

**Listo cuando:** con una apuesta activa y la cuenta en 1 de 2, Hoy sube la propuesta que falta
con su por qué; dos días sin datos del reloj → un aviso, uno solo.

---

### B10 · Calendario y app activa (L)
De la revisión R6.
1. Google Calendar: OAuth desde Ajustes → Conexiones; las citas entran como `Tarea` con hora;
   los bloques de Hoy pueden salir como eventos (`compartible: true`).
2. Accesibilidad de macOS: la app activa y el título de ventana entran como contexto (permiso
   que Juan Camilo da a mano); el aviso `desvio` y Al día lo usan. Nada sale del Mac.

**Listo cuando:** una cita creada en Google Calendar aparece en «Vence» de Hoy; con el permiso
dado, `desvio` detecta 30 min en otra app con un bloque prometido abierto.

### PR · Del encargo a producción (L)
Biblia Parte VIII, los cinco criterios de la fase PR: paquete base al abrir un proyecto; revisión
del diff con otro modelo al cerrar cada sesión con commits; tres líneas sin jerga; ningún
«Entrega» con un hallazgo de seguridad serio abierto; un proyecto real de propuesta a entrega con
la lista de la verdad.

**Listo cuando:** los cinco criterios de la fase PR del tablero de la Biblia, comprobados.

### Z · Cierre y semana de uso
1. `actualizar.sh` desde `main`, `doctor.sh` 10/10, desinstalar e instalar probado.
2. Entrada de cierre en la bitácora con hashes y números.
3. **Siete días de uso sin funciones nuevas.** Solo arreglos de lo que falle, cada uno con su
   lección. Revisión el domingo siguiente en Semana.
4. Después de la revisión: el banco de pruebas (3f) y lo que la semana haya mostrado.

---

## Lo que hace Claude en la app, en paralelo

| Fase | Qué | Antes de |
|---|---|---|
| D0 | Biblia v4.2 publicada y exportada (Hoy, Rumbo, lo que difería) | B0 · **hecho** |
| D1 | Diseño de Metas (escalera), Semana (revisión del domingo), Proyectos (aporte a la meta) y Bandeja (jugadas del Rumbo) en el canvas, para aprobar | R2 |
| D2 | Verificar cada fase: leer commits, correr pruebas, mirarla en el navegador, marcar este archivo y el tablero de la Biblia | cada fase |
| D3 | Cierre: todas las pantallas en escritorio y 375 px con datos reales | Z |

## Lo que solo puede hacer Juan Camilo

1. Abrir Claude Code en `~/proyectos/remi` y pegarle el mega prompt de abajo.
2. Decir «aprobado» a D1 cuando esté (Metas, Semana, Proyectos, Bandeja).
3. Contestar las preguntas de Remi en el panel (cliente de BeaM, pagos de Alfonso, «listo
   cuando», tu visión, cuánto necesitas al mes para vivir solo).
4. Dar los permisos de macOS (Accesibilidad) y el OAuth de Google Calendar en B10.
5. Cloudflare Access delante del túnel; rotar las cuatro llaves; `pmset` y UPS.
6. Instalar el panel en el iPhone (Safari → Compartir → Añadir a inicio).
7. Pegar la instrucción de `docs/INSTRUCCION-CLAUDE-ESCRITORIO.md` en tus proyectos de Claude.
8. La semana de uso (fase Z) y la revisión del domingo.

## Registro

- 4-oct 03:10 · Biblia v4.2 publicada y exportada a `docs/BIBLIA.md` · este plan.

---

## El mega prompt de la terminal

Se pega entero en Claude Code, abierto en `~/proyectos/remi`.

````
Carga la skill /remi. Después lee, en este orden: CLAUDE.md, docs/PLAN-FINAL.md completo, docs/BIBLIA.md (Parte III «Hoy, desde v4.2» y Parte IX «Rumbo» completas), las tres entradas de arriba de docs/BITACORA.md y `git log --oneline -15`.

# Encargo: llevar Remi al 100 % — plan final

## Contexto
PLAN-100 y PLAN-CIERRE están cumplidos y la revisión R0–R6 cerrada. Lo que queda está en docs/PLAN-FINAL.md: tope de gasto, Hoy que se actualiza sola, la ficha de cliente, hilos por tema, el Rumbo (R1–R5), calendario y app activa, la fase PR y el cierre. Eres la única mano en el código: trabajas en main, panel incluido. Claude en la app diseña, verifica y mantiene la Biblia y el plan.

## Qué tienes que hacer
Ejecutar, en este orden y completas, las fases B0, B1, B2, B3, B4, B5, B6, B7, R1, R2, R3, R4, R5, B10, PR y Z (solo los puntos 1 y 2 de Z) de docs/PLAN-FINAL.md, sin esperar mi visto bueno entre fases. Cada punto numerado es una tarea = un commit. Una fase está cerrada solo cuando su «Listo cuando» se cumple y lo comprobaste corriéndolo.

Dos esperas: la parte de panel de R2 (Semana) y de R5 (Proyectos) espera el diseño D1; si D1 no está en el canvas cuando llegues, haz el núcleo de esa fase, anota `ESPERA D1` y sigue. B10 necesita permisos que da Juan Camilo a mano: deja el código y las pruebas, anota `ESPERA PERMISO` y sigue.

## Reglas que no se negocian
1. Una tarea = un commit. `git add <rutas>` explícitas; nunca `-A` ni `.`.
2. Nada de llaves, tokens ni .env en git.
3. Nunca borrar notas de la bóveda ni filas de la base. Se archiva.
4. Nunca datos de prueba en la base real ni en la bóveda real. Ninguna prueba toca Telegram, Notion, la web ni el puerto 4400.
5. Si algo contradice la Biblia v4.2, gana la Biblia. Los contratos se copian de las formas J–S del plan a contratos/contratos.json y se generan; no se inventan campos.
6. Sin IA donde hay reglas. Un modelo solo redacta, investiga o estima; nunca pone el número final ni decide qué es verdad. Toda llamada pagada pasa por el tope de B1.
7. Las seis leyes y la voz de Remi (de tú, sin voseo, 20 palabras como mucho, sin contadores, sin urgir, sin culpa) valen para cada texto.
8. No editas docs/PLAN-FINAL.md ni la Biblia. Reportas en docs/BITACORA.md.
9. Los datos que solo tiene Juan Camilo no se inventan: quedan vacíos y los pregunta Remi en el panel.
10. Código de terceros solo con licencia que lo permita (MIT, Apache) y con su aviso; AGPL, GPL o sin licencia: se lee y se reescribe.
11. Nada fuera del plan.

## Cómo corre cada fase
1. Relee la fase y las formas que toca. Si tu contexto se compactó, PLAN-FINAL.md + tu última entrada de bitácora + `git log` son tu memoria.
2. Por cada punto: la prueba primero, donde duele; después el código; las suites en verde; commit.
3. Cierre de fase, siempre igual: bitácora (con `CAMBIO DE FORMA:` si aplica), las tres suites en verde, actualizar/reiniciar lo que tocaste, doctor 10/10, «Listo cuando» comprobado, `/compact`.
4. Pasa a la siguiente sin preguntar.

## Cuándo parar
- No pares por decisiones de forma: decide y anótalo en «Decisiones que tomé sin preguntar».
- Si un punto no se puede hacer como está escrito: `BLOQUEADO: <punto> — <por qué> — <qué hace falta>`, sáltalo y sigue.
- Para de verdad solo si hay riesgo de perder datos de Juan Camilo, aparece una llave en un diff, o la base o la bóveda real están en un estado que no esperabas.

## Al terminar
Un solo mensaje final: cada fase con su hash de cierre, los números de las pruebas, lo BLOQUEADO, lo que ESPERA, los CAMBIO DE FORMA y la lista «Lo que solo puede hacer Juan Camilo» con lo pendiente.
````

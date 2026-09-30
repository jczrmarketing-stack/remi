# Auditoría de la Biblia de Remi — v1/v2 vs v3.5

**Fecha**: 30-sep-2026. **Alcance**: reconstruir lo que contenían la v1 (28–29 sep) y la v2 (29 sep) y compararlo con la v3.5 (`/home/claude/biblia/biblia.html`, 1.109 líneas).

**Nota sobre fuentes**: no existe copia de la Biblia v1/v2 como HTML; se reconstruyó desde (a) los seis artefactos de la época, (b) las cinco páginas de Notion del 29-sep, (c) la memoria del usuario, (d) los docs del repo. Todas las fuentes se leyeron completas. Salvedad importante: la página Notion «1 · Visión y arquitectura» refleja la **visión v1** (seis problemas, fases 0–6, capas de tokens) y **no** las seis leyes ni las fases 0.1–4 que la memoria atribuye a la Biblia v2; es decir, Notion quedó un escalón atrás de la v2 y nunca se actualizó (fecha de edición 29-sep 02:07). Los artefactos «Design System» y «Ventanita — refinamiento» son de tipo archivo; se leyeron sus `project/*` (README, tokens.json, decisiones.md, 8 componentes, 5 tableros). Siglas de fuente: **[N1]** Notion Visión · **[N2]** Notion DS · **[N3]** Notion Recursos · **[N4]** Notion Investigación · **[N5]** Notion Estado · **[DS]** artefacto Design System · **[PAN]** Remi Panel · **[CON]** Remi Conceptos · **[DIR]** Remi Direcciones · **[RAR]** Remi Raros · **[VEN]** Ventanita refinamiento · **[MEM]** memoria · **[EF]** estado_fases.md · **[AC]** arquitectura-cerebro.md · **[RB]** robustez.md · **[B35]** Biblia v3.5.

---

## A. Inventario de la v1/v2

### A1. Leyes y principios
- **Seis leyes TDAH** (ceguera temporal, memoria externa, sin cadena de culpa, presión invertida, cuerpo primero, enfriamiento) — la memoria confirma que la Biblia v2 las tenía [MEM]; los tableros de la ventanita ya citan «ley 1/2/3/5/6» y `paso_minimo` [VEN Nudges].
- **Seis problemas que resuelve, en orden**: ideas que se pierden · olvidar recordatorios · prompts desordenados que gastan tokens · desconectarse antes de cerrar · dispersión entre proyectos · metas sin plan [N1 §0]. Regla: «cada función responde a uno de los seis problemas o va a la Bandeja» [N1 §7b, N3].
- **Cinco principios no negociables**: cero fricción de entrada · cero tokens por defecto · privacidad por diseño (finanzas y salud nunca salen del Mac) · compañía, no vigilancia · una cosa a la vez [N1 §0].
- **Regla de oro «loco + útil + estratégico»**, con formato A/B/C y «una metáfora que un extraño nombre en 3 s» [N3, MEM].
- **Estrategia de ingeniería**: tecnología aburrida, local primero, una fuente de verdad por dato, «lo que no se prueba no está terminado» [N1 §7b].

### A2. Pantallas
- **Ventanita**: 320×180 en reposo, hasta 420×520 con terminal de prompt; `LSUIElement`; máquina de estados `dormido → escuchando → pensando → respondiendo → dormido`, `oculto ⇄ dormido` (doble clic en borde); cuatro vistas **Foco / Escucha / Respuesta / Nudge** [N1 §3.1, DS README]. Tabla de activación: clic despierta, mantener clic o `⌥Space` habla, escribir + Enter, arrastrar selección o «Mira esto» (Accesibilidad), botón «captura» solo a pedido [N1 §1]. Micrófono solo abierto en `escuchando`, indicador visible siempre [N1 §1, §7].
- **Refinamiento (29-sep)** [VEN]: reposo **120×44 píldora** (320×180 «lee como error»); punto en `baja` porque `dormido` = `line` da 1.5:1; **punto anclado a 28 px del borde, nunca se mueve**; crece a 22 px al escuchar; expandido 420×520 con cuadro que llena la ventana, atajos `⌘↵` / `esc` en `ink-faint`, brillo especular `rgba(243,235,221,0.10)`; «expresión ganada, no ambiental»: celebración 900 ms en `luz`, piel **dinero** cuando la entrega paga, botón **«Hecha»**; tres nudges tipo cuerpo/ritual/ceguera temporal; **presupuesto de silencio**: máx. 5/día, 90 min entre dos, nunca por reloj, nunca mientras escribe, dos «ahora no» seguidos callan el tipo hasta mañana, sin sonido.
- **Conceptos A/B/C** [CON]: **Instrumento** (dial: aguja = tiempo del bloque, anillo = hitos, LED = estado), **Brasa** (barra que se consume, luz que baja, «quedan 8 min» en alerta), **Terminal viva** (líneas mono con `⌥␣ hablar · ⌘K escribir · ⌘M mira esto`, confirmación «✓ entrega 15 oct · $1.200 → notion, calendar», «◆ prompt listo · ⌘C copiar»). Recomendación: «A con la piel de B y la voz de C».
- **Panel** [PAN, N1 §3.2]: **Hoy** (tarea grande, Reloj con 3 pieles conmutables, chips `Entrega vie 3 · $1.000 · 42' del bloque`, botón «Cerrar hito» con 14 chispas hacia el reloj, LED, bloques del día 08:00–16:30, «Vence» con color, **número de la semana `$1.500 de $2.400 · faltan $900 · 2 propuestas Fiverr las cubren`**) · **Proyectos** = **constelación** (React Flow + dagre; discos por proyecto, tamaño = prioridad, arco de progreso, enlaces punteados; al tocar abre el **camino**) · **Metas** («Vivir solo · 12 meses · $2.400/mes · 62 %», «Carro · 18 meses · $1.100/mes · empieza cuando vivir solo pase de 50 %», ingreso por línea `Software $3.200 vs Malik $1.100 · software 3× más por hora · prioriza clientes`) · **Bandeja** (una idea «destacada» por semana, bloque el viernes 16:30) · **Revisión semanal** (guion de 20 min, lunes) [N1 §3.2, §5]. En celular solo Hoy y Proyectos.

### A3. Conceptos con nombre
Reloj con tres pieles · calor como escala · una locura por pantalla · cerrar se siente (celebración única) · camino, no árbol · barra segmentada, no porcentaje («Falta 1» / «Cerrado») · compañía, no vigilancia · un color por significado · siguiente paso inequívoco · LED/StatusDot · FocusCard · PromptTerminal · nudge con salida amable («10 min más», «Estoy en flujo») que entra por el borde y se va a los 8 s, nunca más de uno · «Mira esto» · lista de cierre · idea destacada · presupuesto de silencio · nudge que se encoge a `paso_minimo` [DS README, decisiones.md, componentes, VEN, N1].

### A4. Datos concretos
- **Tokens** (Noche/Día): ground `#151112/#f6f1e9`, surface, surface-2, line, ink, ink-muted, ink-faint, luz `#fff2c9/#8a6a12`, dinero `#ffb020/#9a5b00`, brasa `#ff8a3d/#c2410c`, alerta `#ff4d6d/#c1223f`, pensar `#c9a0ff/#6d4fd6`, baja, dormido, focus-ring `#ffd27a`, **on-luz / on-dinero / on-brasa** [DS tokens.json v2].
- **Tipografía**: display-xl 64/60, display-md 26/27, display-it 24/26 itálica; body 16/24, body-sm 14/20 (mínimo ventanita), label 11/16 600 tracking .12em; num-lg 40/44, num 12/16, code 13/20 [DS].
- **Espaciado** space-1…space-12 (4→48 px); **radios** 8 / 20 / 24 / píldora; **sin sombras**, tres brillos `glow-luz/brasa/pensar` con valores rgba [DS].
- **Movimiento**: 150 ms estados · 250 ms aparecer · 900 ms celebración · aguja una vez por minuto · curva `cubic-bezier(0.2,0.8,0.2,1)` · reduced-motion sin transiciones · sonido Kenney CC0 opcional [DS, N2].
- **Iconos**: Lucide 1.75 px (16/20), Phosphor Duotone solo 4 héroe [DS].
- **Layout**: panel 720 px máx. para Hoy; PromptTerminal 260 px máx. con scroll; máx. 4 chips por fila; máx. 12 hitos por camino [DS].
- **Reglas del líder**: orden fijo 1) entregas con dinero 2) bugs en producción 3) propuestas 4) mejoras 5) ideas → Bandeja; 3 check-ins; nudge de foco a 15 min fuera de plan; bloques 45–50 + 10; hiperfoco >90 suave / >150 firme [N1 §5].
- **Tokens/IA**: Capa 0 reglas, Capa 1 Ollama, Capa 2 Claude; Haiku extraer / Sonnet prompts / Opus solo revisión semanal; **máx. 40 llamadas/día**; contexto = `estado.md` + entrada, nunca el repo [N1 §6].
- **Robustez v1**: timeouts Claude 60 s / Notion 15 s / Ollama 20 s; cola SQLite con reintentos; idempotencia; cero borrar; tope de gasto e interruptor; `config.toml`; un log; `make install`; contexto borrado a 30 días [N1 §4.1, §7b].
- **Contratos JSON v1**: `entrada` {tipo, origen, texto, proyecto_activo, hora} y `respuesta` {decir, mostrar{prompt, chips}, acciones[notion/calendar], costo{modelo, tokens_aprox}} [N1 §4.7]. **Esquema Notion** de 6 bases (Proyectos, Tareas, Entregas, Metas, Ingresos, Bandeja) con campos [N1 §4.4].
- **Fases v1** 0–6 con «listo cuando» medibles: ventanita «usada 5 días seguidos», Telegram «resumen 7 mañanas seguidas», Mira esto «una venta real sin escribir», líder «una semana sin apagarlo», panel «abierto sin que nadie lo pida una semana» [N1 §8].

### A5. Arquitectura y decisiones
Tauri 2 + React + Tailwind v4 + shadcn/Radix + Motion + NumberFlow + canvas-confetti + React Flow; monorepo pnpm `apps/desktop` + `apps/web`; `tauri-nspanel`, `window-vibrancy`, base `dannysmith/tauri-template`; sidecar Python FastAPI + PyInstaller; Cloudflare Worker gratis para Telegram (webhook + cron 7:00 + cron horario); cerebro intercambiable `claude_sdk / claude_api / ollama`; almacenamiento: Notion (operación), `docs/estado.md` por repo, `_cerebro/` local para finanzas/salud/«cómo soy» [N1, N2, N4]. Decisiones cerradas [N5]: nombre, activación por toque, estética, tres pieles (descartados Organismo/Memphis/Ácido), camino no árbol, memoria repartida, 40 llamadas/día; parqueado: iOS nativa, wake word, mejor voz, mascota.

### A6. Investigación de referencia [N4, decisiones.md]
Llama Life, Tiimo, Structured, Sunsama, Motion/Reclaim, Superhuman, Finch vs Habitica, Focusmate/FLOWN, FloatDude/Jarvis/Raycast (tabla «qué copiamos»). Evidencia camino vs árbol: Nunes & Drèze, Kivetz (gradiente de meta), Amabile (principio del progreso), Duolingo. Ranking de visualizaciones para TDAH (1 camino … 6 kanban). Principios UX TDAH y body doubling. Licencias de repos (tldraw y elkjs descartados; Satoshi descartada). Facturación Max verificada 28-sep. Wake word: Porcupine / openWakeWord. Grok Bot descartado. Stack de nueve herramientas descartado; visión continua de pantallas descartada.

### A7. Ideas «raras» y direcciones
Paletas **Brasa / Neón / Ciruela** [DIR] (Neón: lima `#d9ff3f` cerrado, cian foco, magenta pensar; Ciruela: oro viejo, champán, lavanda); conceptos raros **Organismo** (mancha lima que respira, células = hitos), **Memphis**, **Ácido** [RAR]; posibilidad de cruzar (dial de Instrumento con colores de Ácido).

---

## B. Tabla de comparación

| Elemento | En v1/v2 | En v3.5 (dónde) | Estado |
|---|---|---|---|
| Seis leyes TDAH | Biblia v2 [MEM]; citadas en tableros [VEN] | Parte I, seis tarjetas con regla | **Se mantuvo** |
| Seis problemas que resuelve + «cada función responde a uno o va a la Bandeja» | [N1 §0, §7b]; contrato Idea tenía `problema_vision 1–6` | Solo sobrevive el campo `problema_vision: 1-6` en el contrato Idea (L686, L831), sin la lista | **Se perdió** (el campo apunta a una lista que ya no existe) |
| Cinco principios no negociables | [N1 §0] | Diluidos: «una cosa a la vez» sí (Ley 04); «cero tokens por defecto» invertido («piensa siempre», L614); «privacidad: finanzas y salud nunca salen» invertido (L614, L749) | **Cambió** (decisión explícita 29-sep) |
| Loco + útil + estratégico | [N3, MEM] | Hero, tres chips + «si falta uno, va a la Bandeja» (L311-314) | Se mantuvo |
| Regla A/B/C + metáfora en 3 s | [N3] | Solo «mockup con propuestas A/B/C» (L813) | **Degradó** |
| Tokens de color Noche/Día | [DS tokens.json] | Tabla Parte II (L389-400), botón copiar CSS | Se mantuvo (falta `on-luz/on-dinero/on-brasa`, `focus-ring` solo en el CSS copiable) |
| Rampa de calor con significado | [DS, N2] | L378-384 | Se mantuvo |
| Tipografía: escala con tamaños | 9 estilos con px [DS] | Tres familias sin tamaños (L410-423) | **Degradó** (remite al DS) |
| Espaciado, radios, brillos, iconos, layout 720 px | [DS README] | Ausentes; solo «los tokens canónicos viven en el DS» (L375) | **Degradó** (delegado al DS) |
| Movimiento 150/250/900 ms, curva, aguja por minuto | [DS, N2] | Solo «950 ms» de celebración (L490) — **contradice el 900 ms** del DS | **Degradó + inconsistencia** |
| Reloj tres pieles | [DS Reloj] | Demo conmutable (L438-470) | Se mantuvo (menos detalle: sin `alerta` a 10 min, sin `dineroEn`) |
| Celebración única | [DS, PAN] | Playground operable (L476-491) | Se mantuvo |
| Nudge que se encoge / salida amable | [VEN Nudges, DS Nudge] | Playground (L493-504), contrato Nudge | Se mantuvo; **se perdió** «entra por el borde, se va a los 8 s, nunca más de uno» |
| Presupuesto de silencio (5/día, 90 min, nunca por reloj, nunca escribiendo, dos «ahora no», sin sonido) | [VEN Nudges, AC §8] | Parcial: «máximo 5 veces al día, 90 min entre dos, nunca mientras escribe» (L775, L872) | **Degradó** (faltan «nunca por reloj», «dos ahora no callan el tipo», «sin sonido») |
| Voz de Remi (dice / jamás dice) | Copy en DS README (≤20 palabras, de tú, sin emojis) | Tabla dice/jamás (L507-522) | Se mantuvo; **se perdió** la regla de 20 palabras y «nombra como el usuario: entrega, cliente, bloque» |
| Ventanita: 320×180 → 420×520, `LSUIElement`, máquina de estados con `oculto`/`error` | [N1 §3.1] | Un párrafo (L553): gestos 1/2/3, ⌃⌥R, estados por color | **Cambió** (gestos reales) y **degradó** (sin tamaños, sin `oculto`, sin flujo de error) |
| Refinamiento de la ventanita: punto anclado a 28 px, píldora 120×44, brillo especular, ⌘↵/esc | [VEN] | Solo «Isla de reposo 120×44» en criterio c5 (L853) y remisión al tablero (L553) | **Degradó** |
| «Mira esto» / lectura por Accesibilidad / captura a pedido | [N1 §1, N4] | Caja «Accesibilidad macOS · contexto de app activa» (L635) | **Degradó** (desapareció la función de usuario) |
| Ordenar lo dictado en prompt para Claude Code | Problema 3 [N1]; PromptTerminal [DS] | Demo + nota «función que la ventanita debe recuperar» (L553); criterio Fase 1 c2 | Se mantuvo como deuda |
| Panel Hoy con número de la semana ($ vs meta) | [PAN, N1 §3.2] | Mini-mockup sin dinero (L556-575) | **Se perdió** el número de la semana |
| Constelación (React Flow) | [PAN, N1, DS ProjectPath] | Una frase: «la constelación agrupa los caminos activos» (L606) | **Degradó** |
| Metas y plata (meta → número mensual → brecha → acciones) | [PAN, N1 §3.2, problema 6] | «La vista Metas usa la misma pieza a escala de meses» (L606) | **Se perdió** el mecanismo (brecha, ingreso por línea) |
| Revisión semanal (20 min, lunes) | [N1 §3.2, §5] | Ausente (hay rituales noche/mañana, Ley 02) | **Se perdió** |
| Idea destacada por semana | [PAN, N1] | Ausente | Se perdió |
| Lista de cierre (commit · estado.md · avisar cliente) | [N1 §3.2, §5] | Ausente | Se perdió |
| Orden fijo de prioridad del líder (dinero > bugs > propuestas > mejoras > ideas) | [N1 §5] | Ausente; solo «Reglas del líder: prioridad, nudges, enfriamiento» (L633) | **Se perdió** |
| Bloques 45–50/10, hiperfoco >90/>150, nudge de foco a 15 min | [N1 §5] | Ausente (Ley 05 dice «al cerrar un bloque largo») | Se perdió |
| Política de tokens: capas 0/1/2, 40 llamadas/día, Haiku/Sonnet/Opus por tarea | [N1 §6] | Tres modos por nivel (L777); sin tope diario; trastienda gratis (L644) | **Cambió** (tope perdido) |
| Contratos JSON | v1: `entrada`/`respuesta` con `acciones` y `costo` [N1 §4.7]; v2: cinco contratos [MEM] | Cinco + Memoria + Turno (L667-737), JSON copiable | Se mantuvo (v2); `costo{modelo,tokens}` de v1 desapareció |
| Esquema Notion (6 bases, campos) | [N1 §4.4] | «Notion solo de ida: proyectos, entregas, cobros» (L645) | **Degradó** |
| Cloudflare Worker + crons Telegram | [N1 §4.5] | Telegram bot propio, long polling (L873) | Cambió |
| Cerebro intercambiable `claude_sdk/claude_api/ollama` | [N1 §4.2] | Claude por Max + OpenRouter/Groq/Venice/Ollama, `config/motores.json` (L643-648) | Cambió (más rico) |
| Fundamentos de ingeniería: timeouts 60/15/20 s, cola con reintentos, idempotencia, cero borrar, tope de gasto, `config.toml`, un log, `make install` | [N1 §7b] | Parcial en «Indestructible» y Plan de robustez (L652-665): copia, restaurar, vigía, doctor.sh | **Degradó** (idempotencia, cero borrar, tope de gasto, timeouts concretos no aparecen) |
| Privacidad: micrófono solo en `escuchando`, nada de pantalla sin acción, lo leído es dato no instrucción, secretos en llavero, token Notion acotado | [N1 §7] | Solo «llaves en nucleo/.env» (L873) y `compartible: true` | **Se perdió** casi entera |
| «Listo» para tarea de código (pruebas, estado.md, sin secretos, commit, funciona con Claude apagado) | [N1 §7b] | «Un prompt = una tarea = un commit» (L813) | Degradó |
| Fases con «listo cuando» de uso real (5 días, 7 mañanas, una semana) | [N1 §8] | Criterios de fases son técnicos (L837-883); solo R·c5 «siete días de uso real» | **Degradó** |
| Investigación (apps, papers, ranking, licencias) | [N4, decisiones.md] | Ausente | **Se perdió** (vive solo en Notion/DS) |
| Direcciones y raros (Neón, Ciruela, Organismo, Memphis, Ácido) | [DIR, RAR, N5] | Ausente | Se perdió (descartadas, documentadas en DS decisiones.md) |
| Stack frontend (shadcn, Motion, React Flow, tauri-nspanel, pnpm monorepo) | [N2, N4] | «Tauri 2 · React · Tailwind», «Next.js · PWA» (L620-621) | Degradó |
| Jerarquía de fuentes | DS = tokens, Biblia = leyes, Notion = espejo solo lectura [MEM] | Hero L316-322: DS, Biblia, Obsidian, Notion, Repo | Cambió (Obsidian entra, Notion «ida y vuelta» en hero pero «solo de ida» en L645 — **inconsistencia interna**) |

---

## C. Perdido o degradado, por importancia para «terminar y cobrar»

1. **Metas y plata: meta → número mensual → brecha → acción** (Vivir solo $2.400/mes, faltan $900, «2 propuestas Fiverr las cubren») [PAN, N1]. Es el único mecanismo que traducía «cobrar» a un número diario; sin él el panel no dice cuánta plata falta.
2. **Número de la semana en Hoy** ($1.500 de $2.400) [PAN]. La presión sana: dinero visible sin regañar, en la pantalla principal.
3. **Orden fijo de prioridad del líder** (entregas con dinero > bugs > propuestas > mejoras > ideas) [N1 §5]. Sin esto «Reglas del líder» es una caja vacía; es la regla que decide UpVisuals antes que Malik.
4. **Seis problemas que resuelve + filtro «o va a la Bandeja»** [N1 §0]. Era el criterio para no construir de más; su ausencia explica que la v3.5 haya crecido en oficios y motores.
5. **«Listo cuando» de uso real por fase** (5 días seguidos, 7 mañanas, una semana sin apagar) [N1 §8]. La v3.5 mide «criterios técnicos»; el objetivo del producto es que se use.
6. **Lista de cierre** (commit · estado.md · avisar al cliente) [N1]. Ataca directamente «desconectarse antes de cerrar»; cobrar exige avisar.
7. **Revisión semanal de 20 min** (metas, plata por línea, cerrado, aplazado) [N1 §3.2]. Único punto donde se mira la plata del mes.
8. **Presupuesto de silencio completo** (nunca por reloj, dos «ahora no» callan el tipo, sin sonido) [VEN]. Son las reglas que evitan que Remi se vuelva ruido y se apague.
9. **Privacidad y seguridad operativa** (mic solo en escuchando, lo leído es dato no instrucción, secretos en llavero, cero acciones destructivas) [N1 §7]. Menos «producto», pero la Biblia dice «gana la Biblia» y ya no lo dice.
10. **Fundamentos de robustez v1**: timeouts concretos, idempotencia, cola con reintentos, tope de gasto/interruptor [N1 §7b]. El plan v3.5 los reemplaza por doctor.sh y respaldos; el tope de gasto importa porque Max es lo que paga.
11. **Refinamiento de la ventanita** (punto anclado 28 px, píldora 120×44, ⌘↵/esc) [VEN]. Está solo en un tablero; Claude Code no lo lee desde la Biblia.
12. **Tipografía con tamaños, radios, movimiento, iconos** [DS]. Delegado al DS: aceptable si el repo genera desde `tokens.json`, pero la Biblia dice «950 ms» y el DS «900 ms».
13. **Nudge: 8 s, entra por el borde, uno a la vez** [DS Nudge]. Detalle que define si un nudge bloquea.
14. **«Mira esto» / captura a pedido** [N1 §1]. Fase 3 v1 (una venta real sin escribir nada) desapareció como función.
15. **Investigación** [N4]. No hace falta en la Biblia, pero la Biblia ya no enlaza a Notion 4 ni a `decisiones.md`.

---

## D. Nuevo en v3.5 (no estaba en v1/v2)

- El **norte** en el hero: «terminar lo que empieza y cobrar»; «no es otro Claude de escritorio» (L309) [MEM 29-sep].
- **Lectura clara y biónica** con reglas de ancla/peso/intensidad (L425-436) [MEM].
- **Gestos reales** 1/2/3 clicks, ⌃⌥R, Whisper large-v3-turbo, Kokoro 4 voces, X cancela, flecha de modo (L553) [EF].
- **Parte IV·B El cerebro**: niveles 0–3, asociar, conversar, consolidar, hilos, actuar; tres modos (L757-778) [AC].
- **Contratos Memoria y Turno** (L720-737).
- **Parte VI Oficios**: Claude Code, prompting, stack, SOP, clientes, producción, mantenimiento, vibe coding, mi voz; banco de configuraciones; límite «lo que Remi no rehace» (L781-803).
- **Indestructible**: GitHub, copia cifrada, restaurar, LaunchAgents, vigía, Cloudflare Tunnel, doctor.sh, reporte nocturno, cerebro con respaldo (L652-664) [RB].
- **Plan de robustez** y fase **R** (L665, L877-882); motores por proveedor en `config/motores.json`; Notion solo de ida.
- **Fases vivas con persistencia** (db del artefacto, L1042-1106); fases C y S; maquetas del panel A/B/C con recomendación «B permanente + C foco» (L574); nudge tipo **rumbo** (L702); trabajo en paralelo con worktrees y orden de merge (L813).
- Decisión de que finanzas y salud **sí** van a Claude (L614, L749).

---

## E. Juicio

**Debe volver a la Biblia** (corto, en la Parte III/IV, no como anexo):
1. Un bloque «Plata» con el mecanismo de Metas (meta → $/mes → brecha → acción) y el número de la semana en Hoy. Es lo único que conecta el producto con «cobrar».
2. El orden fijo de prioridad del líder, como regla escrita bajo «Reglas del líder».
3. Los seis problemas, con el filtro «si no responde a uno, Bandeja». Sirve para frenar la propia Biblia.
4. «Listo cuando» de uso real en cada fase (días seguidos usándola), además de los criterios técnicos.
5. La lista de cierre y el presupuesto de silencio completo (dos líneas cada uno).
6. Cinco líneas de privacidad/seguridad (mic, dato-no-instrucción, sin borrar, secretos) y el tope de gasto de Max.
7. Corregir las dos inconsistencias: 950 vs 900 ms; Notion «ida y vuelta» (hero) vs «solo de ida» (arquitectura y fase 4).

**Lo que en v3.5 parece tiempo mal gastado frente al objetivo**: los nueve oficios y el banco de configuraciones (Parte VI) son infraestructura para un Remi que todavía no se usa siete días seguidos; cinco proveedores de IA con chips y `motores.json` cuando la decisión ya fue «Claude al frente»; fases C, S y R sumadas antes de cerrar la Fase 2 (panel Hoy) que sí toca la plata. La Biblia v1 tenía 6 problemas y 7 fases; la v3.5 tiene 10 fases y ninguna pantalla de plata. La regla de robustez «siete días sin funciones nuevas» es la más valiosa del documento: aplicarla también a la Biblia.

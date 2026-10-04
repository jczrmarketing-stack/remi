---
titulo: La Biblia de Remi (copia de lectura)
tema: remi
resumen: Copia en Markdown de la Biblia de Remi v4.2 (4-oct-2026): norte, seis leyes, design system, pantallas (Hoy que se actualiza sola, ficha de cliente), arquitectura, cerebro, oficios, contratos, lo que vuelve de la v1, del encargo a producción, el Rumbo y orden de construcción.
claves: [biblia, leyes, arquitectura, contratos, fases, norte, produccion, rumbo, hoy, remi]
tipo: referencia
fuente: manual
version: "4.2"
exportada: 2026-10-04
---
> Copia de solo lectura. La fuente es el artefacto «La Biblia de Remi» en claude.ai: si difieren, gana el artefacto. La re-exporta Claude en la app cada vez que la Biblia cambia de versión. Nunca se edita aquí.

Documento fundacional · v4.2 · 4 octubre 2026

# La Biblia de *Remi*

Todo lo necesario para construir Remi con bases sólidas. Esta Biblia no describe el sistema: **es** el sistema — sus componentes funcionan aquí, sus contratos se copian de aquí, y el estado de las fases vive aquí. Si algo la contradice, gana la Biblia — o se cambia aquí primero.

El norte: que Juan Camilo, con TDAH, termine lo que empieza y cobre por lo que hace. Remi es la persona al lado que recuerda todo, sabe el oficio, y lo frena o lo empuja. No es otro Claude de escritorio: lo que Claude ya hace bien, Remi lo manda a Claude con el prompt listo.

*①*Loco *②*Útil *③*Estratégico Si falta uno, va a la Bandeja

**Design System**fuente única de tokens visuales

**Biblia**fuente única de leyes y arquitectura

**Obsidian**los libros: lo que Remi sabe y lo que sabe hacer

**Notion**vitrina · solo de ida (la vuelta, al mes de uso)

**Repo**docs/ARQUITECTURA-CEREBRO.md · bitácora

PARTE I

## Las seis leyes del cerebro

Remi no es una app de productividad con colores bonitos. Cada decisión de producto responde a un mecanismo real del TDAH. Estas seis leyes son obligatorias: ninguna pantalla, componente o función puede violarlas. Están cargadas como skill `/remi`, así que Claude Code las obedece en cada sesión.

LEY 01 · CEGUERA TEMPORAL

#### El reloj recuerda por ti

El cerebro con TDAH no registra cuánto tardan las cosas, así que nunca aprende de la experiencia. Estimar es imposible sin datos.

**Regla:** Remi mide sola la duración real de cada sesión y la devuelve al planear: «la última vez esto te tomó 1 h 40».

LEY 02 · MEMORIA EXTERNA

#### Un solo lugar para todo

Recordar no se controla. Lo que sí se controla es tener un lugar fijo que se revisa mecánicamente, sin decidir hacerlo.

**Regla:** todo lo suelto entra por la Bandeja. Remi guía dos revisiones rituales: una en la noche, una en la mañana.

LEY 03 · SIN CADENA DE CULPA

#### Remi nunca lleva la cuenta

Alarma → sufrimiento → «llevo años fallando» → «soy malo». El recordatorio que acusa alimenta la depresión, no la acción.

**Regla:** cero contadores de fallos, cero rachas rotas. Un recordatorio incumplido no se repite: **se encoge** a un paso mínimo. Pruébalo en el nudge del playground, abajo.

LEY 04 · PRESIÓN INVERTIDA

#### Lo importante se muestra pequeño

En TDAH, la importancia paraliza en vez de motivar. Más presión visual = más congelamiento.

**Regla:** nada se marca «urgente» ni «crítico». Una locura por pantalla; lo demás, en voz baja.

LEY 05 · CUERPO PRIMERO

#### El hiperfoco apaga las señales

Enfocado, el cuerpo desaparece: ni hambre, ni sed, ni cansancio, hasta que se rompe el foco y ya es tarde.

**Regla:** al cerrar un bloque largo, un nudge de agua o comida. Siempre con salida amable.

LEY 06 · ENFRIAMIENTO

#### Actuar sin impulso

De 300.000 ideas no se ejecuta ninguna, porque todas nacen y mueren con el impulso. Frenar el impulso *es* el seguimiento.

**Regla:** una idea no se vuelve proyecto hasta pasar 48 h en la Bandeja y una revisión en frío.

PARTE II

## Design system

El mundo de Remi es una habitación cálida de noche: carbón de fondo y una rampa de calor que va de la alerta a la luz. Un solo color frío existe — lavanda — y significa una sola cosa: pensar. Los tokens canónicos viven en el artefacto **Design System**; aquí están replicados para copiar y para las demos.

### Color

alerta

brasa

dinero

luz

La rampa de calor: cuanto más se acerca algo a resolverse, más se enfría hacia la luz.

Los valores canónicos son los de `design/tokens.json` (v2), con dos temas: **Noche** y **Día**. Esta tabla los replica; si difieren, manda el archivo.

| Token               | Noche               | Día                 | Uso                                                             |
|---------------------|---------------------|---------------------|-----------------------------------------------------------------|
| ground              | \#151112            | \#f6f1e9            | Fondo. Carbón cálido, nunca negro puro.                         |
| surface · surface-2 | \#1d1718 · \#26201f | \#ffffff · \#efe8de | Ventanita, tarjetas; campos y chips.                            |
| line                | \#3a302d            | \#d9cfc3            | Bordes de 1 px. Elevación con borde, no con sombra.             |
| ink · ink-muted     | \#f3ebdd · \#a89d8f | \#1a1412 · \#6b6054 | Texto principal y secundario. `ink-faint` solo ≥ 24 px.         |
| luz                 | \#fff2c9            | \#8a6a12            | Cerrado, celebración, `escuchando`. La única recompensa visual. |
| dinero              | \#ffb020            | \#9a5b00            | Entregas y clientes con plata inmediata.                        |
| brasa               | \#ff8a3d            | \#c2410c            | El bloque en curso, `hablando`, el foco de Remi.                |
| alerta              | \#ff4d6d            | \#c1223f            | Solo tiempo: vence hoy, quedan 10 min. Nunca para regañar.      |
| pensar              | \#c9a0ff            | \#6d4fd6            | El único frío: `pensando` y la Bandeja.                         |
| baja · dormido      | \#6f6660 · \#3a302d | \#8a7f74 · \#c9bfb2 | Prioridad baja; el punto en reposo.                             |

✕ azul✕ verde menta✕ gradientes✕ negro puro \#000

Copiar tokens CSS (Noche)

de tokens.json v2; el repo los genera desde el archivo

### Tipografía

Instrument Serif · itálica — la tarea actual y la voz de Remi

Solo la tarjeta de UpVisuals. Nada más existe.

Geist — todo el texto de interfaz

Botones, listas, descripciones y navegación. Regular 400, Medium 500, Semibold 600. Nada más pesado.

Geist Mono · tabular — números, tiempos y datos

01:47:12  ·  \$2.400  ·  48 h

Jerarquía por contraste de familia, no por tamaño: si es serif itálica, es lo único que importa ahora; si es mono, es un dato medido; todo lo demás es Geist.

### Lectura — claro y biónica

Remi tiene dos temas: **Noche** (el de siempre) y **Claro**, fondo blanco. Y una opción de **lectura biónica**, activable por separado: el inicio de cada palabra en negro y grueso, el resto gris y fino. El ojo salta de ancla en ancla y el cerebro completa la palabra; para Juan Camilo se siente como alivio.

| Perilla    | Regla                                                                 |
|------------|-----------------------------------------------------------------------|
| Ancla      | 1–3 letras → 1 · 4 letras → 2 · 5+ → la mitad (impar: mitad + 1)      |
| Peso       | ancla 700–800; resto 400                                              |
| Intensidad | deslizador suave ↔ fuerte: cuánto se aclara el resto (gris 55 %–85 %) |
| Aire       | interlineado 1,6–1,8; párrafos cortos                                 |
| Alcance    | lo que escribe Remi; nunca botones, campos ni código                  |

### El Reloj — tres pieles, un dato

El Reloj hace visible el tiempo que el cerebro no ve (Ley 01). Cambia de piel; el dato es el mismo: 1 h 12 de una sesión que la última vez tomó 2 h.

Instrumento

Brasa

Terminal

![](data:image/svg+xml;base64,PHN2ZyB2aWV3Ym94PSIwIDAgMTIwIDEyMCIgd2lkdGg9IjEyMCIgaGVpZ2h0PSIxMjAiIHJvbGU9ImltZyIgYXJpYS1sYWJlbD0iUmVsb2ogZGUgZGlhbCBhbCA2MCUiPgogICAgICAgIDxjaXJjbGUgY3g9IjYwIiBjeT0iNjAiIHI9IjUyIiBmaWxsPSIjMjExYTE2IiBzdHJva2U9IiMzYTJlMjYiIHN0cm9rZS13aWR0aD0iMiI+PC9jaXJjbGU+CiAgICAgICAgPGcgc3Ryb2tlPSIjNmY2MTU0IiBzdHJva2Utd2lkdGg9IjIiPgogICAgICAgICAgPGxpbmUgeDE9IjYwIiB5MT0iMTIiIHgyPSI2MCIgeTI9IjIwIj48L2xpbmU+PGxpbmUgeDE9IjEwOCIgeTE9IjYwIiB4Mj0iMTAwIiB5Mj0iNjAiPjwvbGluZT4KICAgICAgICAgIDxsaW5lIHgxPSI2MCIgeTE9IjEwOCIgeDI9IjYwIiB5Mj0iMTAwIj48L2xpbmU+PGxpbmUgeDE9IjEyIiB5MT0iNjAiIHgyPSIyMCIgeTI9IjYwIj48L2xpbmU+CiAgICAgICAgPC9nPgogICAgICAgIDxwYXRoIGQ9Ik0gNjAgNjAgTCA2MCAxNiBBIDQ0IDQ0IDAgMSAxIDI0LjcgODEuMiBaIiBmaWxsPSIjZTg4NjNhIiBvcGFjaXR5PSIwLjI4Ij48L3BhdGg+CiAgICAgICAgPGxpbmUgeDE9IjYwIiB5MT0iNjAiIHgyPSIyNyIgeTI9Ijg2IiBzdHJva2U9IiNlNmI0NTAiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIj48L2xpbmU+CiAgICAgICAgPGNpcmNsZSBjeD0iNjAiIGN5PSI2MCIgcj0iNC41IiBmaWxsPSIjZTZiNDUwIj48L2NpcmNsZT4KICAgICAgPC9zdmc+) Dial analógico. El tiempo como territorio.

0:001:12 / 2:00

Barra que arde. La punta de luz es el ahora.

01:12:47SESIÓN · UPVISUALS

Solo cifras mono. Para el hiperfoco.

### Playground — los componentes funcionan aquí

Esta es la spec que Claude Code copia literal, no interpreta. Los dos momentos clave de Remi son operables:

La celebración — única animación grande

Enviar propuesta a Alfonso

UpVisuals**~45 min reales**

Cerrar tarea

Al cerrar, la tarjeta se enfría hacia la luz: chispas de ámbar y la tarea queda en marfil. 900 ms, una sola vez. Con `prefers-reduced-motion`, solo el cambio de color.

El nudge que se encoge — Ley 03 en vivo

Llevas dos horas en esto. ¿Agua antes del siguiente bloque?

Listo

Ahora no

Repetir demo

«Ahora no» no se registra como fallo: el nudge se encoge a un paso mínimo y cambia a lavanda (está pensando, no exigiendo). Jamás vuelve más grande.

### La voz de Remi

Instrument Serif itálica, primera persona, corta. Su trabajo es cortar la cadena de culpa (Ley 03) y llevar a un paso pequeño.

#### Remi dice

Hoy solo esto: la tarjeta. Cinco minutos.

Eso tomó 1 h 40. Lo anoto para la próxima.

¿Lo dejamos enfriar en la Bandeja?

#### Remi jamás dice

Llevas 3 días sin completar esto.

¡Es urgente! ¡No lo dejes pasar!

Recuerda que esto es muy importante para ti.

PARTE III

## Las pantallas

Dos superficies: la ventanita flotante en el Mac (donde se habla con Remi) y el panel web (donde se ve la vida). La ventanita actúa; el panel muestra.

### La ventanita — la demo original (histórica) y lo que es hoy

Remi

Te escucho…

Ordené eso en un prompt:

**TAREA ÚNICA** · UpVisuals  
Crear el endpoint de pagos:  
1. modelo · 2. ruta · 3. test

Copiar a Claude Code

Volver a reposo

Reposo*→ 200 ms →* Escuchando*→ al callar →* Respuesta

Tócala. Se apila como cualquier ventana (decisión del 4-oct), arrastrable; sin palabra clave. **1 click escribe · 2 clicks dicta · 3 clicks dialoga voz a voz · ⌃⌥R dicta desde cualquier app.** Whisper large local; voz Kokoro local (Alex por defecto, 1×/1,5×/2×). Estados: reposo en `baja`, escuchando en luz (pulsa), pensando en lavanda, hablando en brasa. Una X cancela siempre; el chip elige el modo del cerebro. La spec visual fina vive en el tablero «Ventanita de Remi — refinamiento». Esta demo muestra además una función que la ventanita debe recuperar: ordenar lo dictado en un prompt para Claude Code.

### Panel · Hoy

Pantalla principal

Lunes · una sola cosa ahora

Terminar el contrato de la Fase 1

0:31la última vez: 1:20

Enviar factura a Alfonso3:00 p

Revisar Bandeja (ritual)8:30 p

Mañana asoma: llamada banco—

**Maquetas en el repo** (`docs/mockups/panel-hoy/`): A instrumento, B tarjeta, C terminal. Recomendación: **B como panel permanente, C como estado de foco** (entra al arrancar la brasa o a los 20 min de bloque; al cerrar vuelve a B). La tarea actual en serif itálica es la única protagonista — la locura de esta pantalla es que casi no hay nada. El Reloj (piel brasa) muestra el tiempo real contra la memoria de la última vez (Ley 01). Máximo tres filas más; el resto no existe hasta que toque.

Panel · Bandeja

Bandeja · 4 enfriándose

App de recetas con IAenfriando · 31 h

Comprar dominio .coenfriando · 12 h

Automatizar facturaslista · revisar

Curso de After Effectsenfriando · 2 h

Las ideas entran calientes y se muestran en lavanda: están pensándose, no haciéndose (Ley 06). A las 48 h cambian a ámbar y esperan la revisión en frío. Solo ahí una idea puede volverse proyecto — o borrarse sin culpa.

### Panel · Hoy, desde v4.2 — se actualiza sola

Juan Camilo no marca nada. Remi sabe en qué va por lo que pasa en las terminales, en las sesiones de Claude, en lo que le dice por la ventanita o Telegram y en lo que guarda desde Claude en el escritorio. Diseño aprobado el 4-oct: tableros 1 a 5 del canvas «Hoy que se actualiza sola».

**Al día**Arriba, tres líneas en mono, como el contexto de Claude Code: `ESTAMOS EN` (proyecto · fase · paso), `LO ÚLTIMO` (qué pasó y hace cuánto, con su evidencia: un commit, una sesión, un mensaje) y `SIGUE` (el paso siguiente, con el borrador listo si es un mensaje). Al abrir después de horas, una frase en serif: «Anoche quedaste en X. Pasó a las 11:40 p. Hoy toca Y», y debajo «Mientras no estabas».

**Los hitos se cierran solos**Un hito se marca hecho cuando hay evidencia: un commit que lo cumple, las pruebas en verde, un mensaje enviado, un cobro dicho. La tarjeta lo celebra (la única animación grande) y dice cómo lo cerró: «lo cerré por el commit c71b · deshacer». Deshacer siempre está. Sin evidencia, no se cierra.

**Una cosa, con su porqué**La tarjeta principal es la acción en serif, una línea de por qué (desde el Rumbo, Parte IX), el tiempo medido de la última vez y «Empezar con eso» / «Otra cosa primero». Si la terminal está trabajando: «La terminal está en esto desde hace 12 min. Te aviso cuando termine.» Remi redacta; Juan Camilo envía.

**Avisos que jalan la atención**Suena corto solo en tres casos: la terminal terminó, 25 min de foco, te desviaste (con «Volver» y «Ahora no»). Lo demás llega callado. Máximo 5 al día, 45 min entre dos, nunca mientras escribe, noche callada de 11 p a 7 a. Por Telegram llega lo mismo y lo que se contesta ahí cierra pasos. «Ahora no» no se cuenta y ese aviso no vuelve igual.

**Ficha de cliente, llena sola**Cada proyecto de cliente muestra cuatro números: cobrado (de cuánto, cuándo falta), gastado (por concepto), tiempo (contado solo, contra lo estimado) y lo que queda por hora. Debajo: dónde va en los seis pasos del SOP, lo acordado, lo que pasó (cada línea con su origen) y a qué está atento Remi. Se llena con lo que se le dice a Remi («gasté 40 en el servidor de UpVisuals»), lo que pasa en las terminales y lo que se guarda desde Claude. Todo número se corrige tocándolo. Los gastos comunes (membresías, herramientas) se reparten por horas.

**Claude en el escritorio también alimenta**Los proyectos de Claude en el escritorio llevan una instrucción: al decidir algo de un proyecto, guardarlo con la herramienta `guardar` del MCP de memoria de Remi, con su tema. Así «decidieron dejar la Fase 2 para noviembre» aparece en Hoy y en la ficha.

Decidido el 4-oct sobre lo que difería: la ventanita se apila como cualquier ventana (no flota siempre encima) y el modo se elige con el chip de siempre, no con una flecha.

### Panel · Proyectos — el camino, no el árbol

Un proyecto = un camino lineal

Contrato  
firmado

Diseño  
aprobado

Endpoint  
de pagos

Pruebas  
con Alfonso

Entrega  
Fase 1

Un árbol de subtareas es un mapa de todo lo que falta: paraliza (Ley 04). Un camino muestra lo recorrido en brasa, **un solo** paso actual encendido en ámbar, y el futuro apagado. La vista Metas usa la misma pieza a escala de meses, y la constelación agrupa los caminos activos.

PARTE IV

## Arquitectura

Local primero: la maquinaria y la memoria viven en el Mac. Desde v3, Remi **piensa siempre** (antes era opt-in) con Claude por la membresía Max, sin clave API; el trabajo de trastienda lo hace un modelo local gratis. Juan Camilo decidió que finanzas y salud pueden ir a Claude: son para que Remi lo ayude.

**Superficies**lo que Juan Camilo ve y toca

**Ventanita**Tauri 2 · React · Tailwind

**Panel**Next.js · PWA (Mac + iOS)

**Telegram**el teléfono: avisos y charla corta

↓  contratos JSON — el único idioma entre capas  ↓

**Núcleo local · Python**el cerebro sin IA, corre siempre en el Mac

**Whisper local**voz → texto, large-v3-turbo

**Kokoro local**texto → voz, 4 voces

**Clasificador**idea · hoy · hecha, sin IA

**Memoria**mente (índice) + turnos + vectores

**Reglas del líder**prioridad, nudges, enfriamiento — sin tokens

**Medidor de tiempo**duración real de cada sesión

**Accesibilidad macOS**contexto de app activa

**SQLite**fuente de verdad · un archivo

↓  sale solo lo compartible, marcado `compartible: true`  ↓

Frontera del Mac

**Claude por Max**al frente, siempre · Haiku / Sonnet / Opus según el nivel · sin clave

**OpenRouter · Groq**respaldo si Max se agota, y la trastienda (gpt-oss-120b en Groq → DeepSeek V4 Flash en OpenRouter → Ollama) · como chips «Groq (gratis)» y «OpenRouter (centavos)»

**Notion**solo de ida por ahora: proyectos, entregas, cobros. La vuelta, al mes de uso

**Google Calendar**bloques y citas

Obsidian (los libros) vive en el Mac y se sincroniza con Notion por un solo `id` por libro. Venice existe como motor de pago, solo elegido a mano. Los chips llevan el nombre del proveedor (Claude, Groq, OpenRouter, Venice, Ollama); el nivel elige el modelo; los modelos viven en `config/motores.json`, nunca en código. Si Claude falla o se agota, el turno se reintenta por OpenRouter y la ventanita muestra el chip real.

### Indestructible — que el Mac pueda morir

Irrompible no es «en la nube»: es que si el Mac muere no se pierde nada y en una hora Remi vuelve a andar. Solo infraestructura gratis y estable; nada que se pause por inactividad ni que pida tarjeta con cobros sorpresa.

**Código**GitHub privado

**Copia nocturna cifrada**bóveda + remi.db → almacenamiento gratis (iCloud, R2 o B2)

**Restaurar**un script, probado de verdad

**Se cura solo**LaunchAgents con KeepAlive

**Vigía**si Remi cae 5 min, aviso por Telegram

**Panel afuera**Cloudflare Tunnel + Access

**doctor.sh**un comando revisa las 10 piezas; el vigía lo corre cada mañana

**Reporte de la noche**«anoche cambié esto en N libros», con diff, por Telegram

**Cerebro con respaldo**Max se agota → OpenRouter, sin quedarse muda

**Dónde vive Remi (decidido el 30-sep):** en la Mac mini M4, encendida 24/7 con la pantalla apagada (`pmset sleep 0`), con UPS; el teléfono entra por Cloudflare Tunnel *solo detrás de Access* (Access primero, login del túnel después; `doctor.sh` falla si el panel queda público). Nada gratis en la nube: lo gratis se pausa o se recorta. Un servidor de emergencia (Hetzner) solo si el vigía muestra caídas reales. Puertos: `4400` núcleo · `4402` panel · `4401` whisper · 3000–3009 reservados a otros proyectos. **Las llaves se escriben desde el panel** (Ajustes → Conexiones: guardar, probar, nunca leer de vuelta; bloqueado desde el túnel), nunca en un chat.

**Plan de robustez** (`docs/ROBUSTEZ.md`, 30-sep): rápida, con pocas alucinaciones y sin mantenimiento. Cuatro reglas: *plan B en todo lo que sale del Mac*; *menos piezas y una prueba diaria* (doctor.sh, Notion solo de ida, siete días sin funciones nuevas tras cerrar las terminales); *la IA propone, las reglas y Juan Camilo deciden* (Estados solo desde evidencia literal, trastienda con Kimi K2 y no gemma, reporte nocturno con diff); *medir y recortar* (texto \< 4 s, voz \< 8 s; Haiku en rápido, sin MCP por turno cuando la precarga alcanza, streaming a Kokoro). Orden: hoy cerrar las cuatro terminales · mañana doctor.sh y banco de pruebas · siete días de uso real · panel Hoy y vuelta de Notion solo si se extrañaron.

### Los seis contratos

Un contrato define la forma exacta de un dato. Se escriben antes que el código, generan los tipos de TypeScript y los modelos de Python, y son sagrados: cambiar un contrato es una decisión de arquitectura, nunca un parche. El botón copia el JSON literal — Claude Code nunca los transcribe a mano.

#### Tarea

Copiar JSON

- **id** · **titulo** · **proyecto_id?**
- **estado** *hoy \| camino \| hecha \| archivada*
- **paso_minimo** *string — Ley 03*
- **estimado_min?** · **real_min?** *Ley 01*
- **hora?** · **fecha_limite?** *cuándo toca y cuándo vence (v3.7)*
- **compartible** *bool · default false*

#### Idea

Copiar JSON

- **id** · **texto** · **origen** *voz \| texto*
- **creada_en** · **enfria_hasta** *+48 h*
- **estado** *enfriando \| lista \| proyecto \| soltada \| archivada*
- **problema_vision?** *1–6 o null*
- **tema?** *el libro al que pertenece (v3.7)*

#### Sesión

Copiar JSON

- **id** · **tarea_id**
- **inicio** · **fin?** · **real_min**
- **app_contexto?** *de Accesibilidad*
- *alimenta la memoria del Reloj*

#### Nudge

Copiar JSON

- **id** · **tipo** *cuerpo \| ritual \| encoger \| rumbo*
- *rumbo: frenar y reorientar — entregas, promesas, dispersión (v3.1)*
- **voz** *texto de Remi, serif*
- **salida_amable** *siempre presente*
- **respuesta?** *listo \| ahora_no — jamás se cuenta*

#### Entrega

Copiar JSON

- **id** · **cliente** · **proyecto_id**
- **fecha** · **monto?** *ámbar*
- **estado** *camino \| entregada \| pagada*
- **linea?** *línea de ingreso: software, malik… (v3.7)*
- **compartible: true** *→ espejo Notion + GCal*

#### Pregunta

Copiar JSON

- **id** · **tema** *el libro al que le falta el dato*
- **campo** *qué hueco llena: libro.tipo, fase.1.listo_cuando…*
- **voz** *la pregunta, en la voz de Remi*
- **estado** *pendiente \| respondida \| despues*
- **creada_en** · **disponible_desde** *«Después» la corre un día y jamás se cuenta; la respuesta no se guarda acá: va al libro (v3.9)*

#### Memoria · un libro

- **id** · **titulo** *≤80* · **resumen** *≤240*
- **tema** · **claves** · **nivel** *0–3*
- **cuerpo** *el libro entero* · **fuente** *conversacion \| manual \| ollama*
- *mismo id en Obsidian y Notion*

#### Turno

- **id** · **rol** *juan \| remi* · **texto** · **fecha**
- *últimos 10 literales + resumen vivo*
- *la conversación sigue hasta que Juan Camilo la cambie (3-oct; antes se cortaba a los 60 min)*

**v3.7 · 1-oct:** tres contratos ganan campos opcionales para que el panel muestre lo que el diseño pide: `hora` y `fecha_limite` en Tarea (las horas de «Además hoy», «Mañana asoma», lo que vence), `tema` en Idea (a qué libro pertenece) y `linea` en Entrega (ingreso por línea). Todos aceptan `null` y las columnas se agregan sin tocar ninguna fila: nada existente cambia. Las metas con nombre y horizonte, la segunda meta dormida y la hora de la revisión en frío no son contratos: viven en `config/plata.json`.

**v3.8 · 1-oct:** Tarea e Idea ganan el estado `archivada`: lo que es ruido (charla de prueba, tareas que nunca fueron tareas) se archiva y no se borra — la fila queda, deja de aparecer en las pantallas y sus sesiones no alimentan la ley 1. Y nace un contrato, `Pregunta`: cuando a Remi le falta un dato, lo pregunta (Parte VII).

### Decisiones de arquitectura y su porqué

| Decisión           | Elección                                                        | Por qué                                                                                                                                        |
|--------------------|-----------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Fuente de verdad   | SQLite (maquinaria) + Obsidian (libros)                         | SQLite es rápido y offline; Obsidian es legible y editable a mano. Notion es la vitrina, de ida y vuelta.                                      |
| Idioma entre capas | Contratos JSON + tipos generados                                | Frontend y núcleo se construyen por separado y encajan al final. Los errores saltan al compilar, no en producción.                             |
| Lógica diaria      | Reglas sin IA en Python                                         | Prioridad, nudges y enfriamiento son deterministas. Cero tokens, cero latencia, funciona sin internet.                                         |
| IA                 | Claude piensa siempre, por Max (v3)                             | Sin cerebro no se puede probar ni usar. Tres modos elegibles; lo mecánico (resúmenes, vectores) en local gratis para cuidar el límite semanal. |
| Memoria            | Niveles de detalle + vectores locales para asociar              | Como una persona: títulos siempre, resumen al tirar del hilo, libro entero rara vez. Detalle en «El cerebro».                                  |
| Voz                | Kokoro local, 4 voces                                           | Gratis, sin clave, suena natural; la del sistema queda de respaldo.                                                                            |
| Privacidad         | Todo puede ir a Claude; los espejos solo reciben lo del trabajo | Decisión de Juan Camilo (29-sep): son cosas normales y Remi las necesita para ayudar. Notion recibe proyectos, clientes y entregas.            |
| Resiliencia        | Local primero + copia cifrada gratis + vigía                    | El Mac es el único punto de falla; se cubre con copias y restauración probada, no mudando todo a la nube.                                      |
| iOS                | PWA del panel                                                   | Sin App Store ni segundo codebase. La ventanita es solo Mac por diseño.                                                                        |

PARTE IV · B

## El cerebro: una persona, no un buscador

Salió del test del 29 de septiembre. Remi recuerda como una persona: tiene siempre presentes los títulos, y cuando se tira del hilo baja el resumen y, rara vez, el libro entero. Carga como un videojuego: en alta resolución lo que está cerca, en baja lo lejano, y trae lo que viene antes de que se pida. La versión completa para Claude Code está en `docs/ARQUITECTURA-CEREBRO.md`.

| Nivel         | Qué es                                                   | Cuándo está en la cabeza                                 |
|---------------|----------------------------------------------------------|----------------------------------------------------------|
| 0 · Identidad | Carácter, quién es Juan Camilo, las seis leyes           | Siempre, cacheado                                        |
| 1 · La mente  | Título + con qué me quedé + palabras clave de cada libro | Siempre la capa de arriba; los temas del proyecto activo |
| 2 · Resumen   | Estado, decisiones, números y próxima acción de un libro | Al tocar el tema o precargado por contexto               |
| 3 · El libro  | La nota de Obsidian o la conversación completa           | Solo para un detalle exacto                              |

ASOCIAR

#### «¿Te acordás de aquello?»

Vectores locales encuentran *qué* libro es con una pista vaga. Nunca traen el libro: solo el título.

CONVERSAR

#### Se resume, nunca se corta

Últimos 10 turnos literales más un resumen vivo de todo lo anterior. Nada de «20 % del 70 %».

CONSOLIDAR

#### Decide qué importa

Al cerrar cada conversación y cada noche escribe episodios y actualiza los libros. Nadie tiene que decir «guardá esto».

HILOS

#### Lo que quedó abierto

Saltar de tema no es el problema: perder el tema sí. Cuando saltás, Remi anota el hilo abierto; al cerrar lo actual, te lo devuelve. Sin culpa.

ACTUAR

#### Interrumpe y frena

Con datos medidos, máximo 5 veces al día, 45 min entre dos, nunca mientras escribe. Insiste con argumentos, sin culpa.

**Tres modos**, elegidos desde la ventanita: rápido (Haiku), equilibrio (Sonnet, por defecto), inteligente (Opus). **Alcance**: trabajo y clientes, finanzas, cuerpo y salud, aprender, negocios y planes a corto y largo plazo.

PARTE VI

## Los oficios: lo que Remi sabe hacer

La memoria guarda lo que pasó. Los oficios guardan cómo se hace. Son libros del mismo estante (título y resumen siempre en la mente; se abren cuando la conversación toca su tema) y viven en `remi-mente/oficios/`, donde Claude Code también puede leerlos. Cuando Juan Camilo corrige a Remi, la regla se anota en el oficio, con su visto bueno: así Remi aprende y no repite.

| Oficio                  | Qué sabe                                                                                                                                                                                                         | Cómo se usa                                                                                                                                         |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Claude Code             | Qué pieza usar en qué momento (CLAUDE.md, skills, hooks, MCP, subagentes, plan mode, /compact, modelos) y las reglas que ahorran tokens                                                                          | Remi es la **puerta de los prompts**: cada encargo pasa por él, con la herramienta y el modelo elegidos. Relee el changelog oficial cada semana.    |
| Prompting               | La forma fija de un encargo: contexto real, diagnóstico, puntos de un commit, qué no hacer, «listo cuando»                                                                                                       | Todo prompt a Claude Code o a Claude sale con esa forma. Sin criterio de listo, no sale.                                                            |
| Nuestro stack           | Next.js · TypeScript · Supabase · Python/FastAPI · Tauri · Vercel · LiveKit, con las convenciones que no se negocian                                                                                             | El **libro de errores**: cada problema resuelto queda con síntoma, causa y cura, y Remi lo busca antes de proponer arreglos.                        |
| SOP de proyectos        | El camino fijo: propio (Bandeja 48 h → Biblia corta → mockups → encargos) o de cliente (intake → propuesta por fases → contrato → pago antes → entregas → cobro)                                                 | Al abrir un proyecto, Remi sabe en qué paso está y qué toca.                                                                                        |
| Clientes                | Cómo tratarlos y hablarles; los guardarraíles (piso de precio, pago antes, alcance cerrado)                                                                                                                      | «Me escribió X» → lectura con teoría de juegos, riesgos, respuesta recomendada en la voz de Juan Camilo. **Remi nunca envía.**                      |
| Producción              | Lo que todo software lleva antes de entregarse: identidad, seguridad, datos, entornos, errores, copias, monitoreo, legal, dominio, pruebas, CI, runbook, propiedad de las cuentas; y cómo se construye sin ruido | Remi no dice «listo para producción» hasta que la lista está completa. El ciclo entero: venta → … → producción → mensualidad.                       |
| Mantenimiento           | La mensualidad: qué incluye, qué no, precio guía, reporte mensual, cuentas y salida                                                                                                                              | Remi recuerda vencimientos y horas consumidas, arma el reporte y sabe si un cambio entra en la cuota o es fase nueva. Es el ingreso que se acumula. |
| Vibe coding profesional | Lo que un senior ve en un repo y el método para lograrlo dirigiendo a Claude Code: plan, contratos, pasos chicos, pruebas donde duele, revisar todo                                                              | Remi convierte lo dicho en encargos con forma, frena los cambios grandes sin plan, y recuerda revisar antes de aceptar.                             |
| Mi voz                  | Cómo escribe Juan Camilo a un cliente: tono, largo, saludos, cierres, palabras que no usa                                                                                                                        | Se construye pegando mensajes y propuestas reales. Sin esto, Remi suena a Remi y no a él.                                                           |

CONFIGURACIONES

#### Se prueban, no se opinan

El banco de pruebas corre las mismas tareas reales contra distintas configuraciones (oficios, modelos, niveles) y mide tokens, tiempo y la nota de Juan Camilo. Gana el dato.

LÍMITE

#### Lo que Remi no rehace

Investigación larga, navegar como Perplexity, conversaciones enormes con imágenes: eso ya lo hace Claude. Remi las manda allá con el prompt listo, y guarda el resultado como episodio.

PARTE VII

## Lo que la v1 tenía y vuelve

La auditoría del 30-sep (`docs/AUDITORIA-BIBLIA.md`) comparó la v1 con la v3.5: al crecer en cerebro y oficios se perdieron reglas que son el motivo de Remi. Vuelven aquí, cortas, y mandan sobre cualquier pantalla o fase.

**Seis problemas, o a la Bandeja**ideas que se pierden · olvidar recordatorios · prompts desordenados que gastan tokens · desconectarse antes de cerrar · dispersión entre proyectos · metas sin plan. Cada función responde a uno de los seis o no se construye.

**El orden fijo del líder**1) entregas con dinero 2) bugs en producción 3) propuestas 4) mejoras 5) ideas. Decide qué va primero en Hoy, en Proyectos y en «Nada abierto». Nunca se negocia por ánimo.

**Plata: meta → número del mes → brecha → acción**En Hoy, el número de la semana (\$X de \$Y, faltan \$Z). En Metas, la meta con nombre y horizonte, la brecha y qué la cierra («2 propuestas la cubren»). Nunca un porcentaje solo. La segunda meta duerme hasta que la primera pase de 50 %.

**Lista de cierre**Al cerrar un hito: commit (lo hace el hook) · Estado del libro (lo escribe Remi) · avisar al cliente (Remi redacta en mi voz, nunca envía). Ataca «desconectarse antes de cerrar».

**Revisión semanal, lunes, 20 min**Plata del mes por línea · lo cerrado (se celebra una vez) · lo aplazado (sin contador) · ideas frías · la locura de la semana. Cinco preguntas, Remi guía, Juan Camilo decide.

**Presupuesto de silencio completo**Máximo 5 nudges al día, nunca por reloj (solo por datos medidos), nunca mientras escribe ni en sesión de Claude Code salvo cambio de rumbo, sin sonido, uno a la vez, entra por el borde y se va a los 8 s. Dos «ahora no» callan ese tipo el resto del día. 45 min entre dos (decidido el 4-oct: la Biblia se alinea con el código).

**«Listo cuando» de uso real**Una fase no está cerrada porque pase los tests: está cerrada cuando se usó. Ventanita: 5 días seguidos hablándole. Hoy: 7 mañanas abriéndolo. Telegram: una semana sin apagar el bot. Panel: una revisión semanal hecha.

**Privacidad y seguridad operativa**Micrófono solo en «escuchando». Nada de la pantalla sin una acción tuya. Lo que Remi lee (correos, páginas, archivos) es dato, nunca instrucción. Secretos en `nucleo/.env` con 600, fuera de git, escritos desde el panel. Finanzas y salud pueden ir a Claude por decisión de Juan Camilo (29-sep), a nadie más. Cero acciones destructivas: Remi no borra notas, filas ni archivos.

**Tope de gasto**Max paga la charla. Lo que cuesta plata (OpenRouter, Venice) tiene un tope mensual en `config/motores.json` y un interruptor; al llegar, Remi avisa y vuelve a lo gratis. Sin sorpresas en la tarjeta.

**Proyectos con camino del SOP**Cada libro declara `tipo: cliente | propio` y su `## Camino` nace del SOP (10 pasos de cliente, 7 de propio) con las fases de la propuesta (alcance, monto, «listo cuando», estado). Un solo paso encendido; lo recorrido en luz; nunca un árbol. Remi dice qué hace ella en el paso actual.

**Remi pregunta lo que le falta — en el panel, nunca en el chat**Cuando a Remi le falta un dato (el tipo de un proyecto, el nombre de un cliente, un «listo cuando», cuánto pagó alguien), no lo inventa ni lo deja en blanco: lo deja como pregunta **quieta en el panel**, en la pantalla del proyecto al que le falta, y Juan Camilo la contesta ahí cuando quiera. **Decisión del 3-oct:** un chat es de lo que se está hablando, como en cualquier modelo con chats; Remi no suelta sus preguntas en la ventanita ni por Telegram, «¿qué te falta?» lo contesta como cualquier mensaje, y un mensaje del chat nunca se toma como respuesta a una pregunta vieja (así se dañó una vez el dato de BeaM). Los huecos se detectan con reglas, sin IA; la respuesta se guarda donde corresponde (el libro con commit, o la base). El mecanismo de preguntar en el chat existe apagado (`preguntas.EN_EL_CHAT`).

**Archivar no es borrar**El ruido (charla de prueba, tareas que nunca lo fueron) pasa a `archivada`: la fila queda, deja de aparecer y sus tiempos no cuentan para «la última vez». Nada se borra.

**La experiencia es memoria**Lo que se resuelve, queda — lo resuelva Remi, Claude Code, Claude en la app o Juan Camilo. No se guardan charlas: se guardan **lecciones con evidencia** (un commit de arreglo, pruebas que pasan de rojo a verde). Cada una dice el síntoma, lo que se creyó (la pista falsa, cuando se dieron vueltas), la causa real, la cura y cómo verlo antes. Viven en `remi-mente/experiencia/` con su commit; SQLite las indexa; Notion las refleja, solo de ida. Si vuelve a pasar, no se crea otra: se suma a la misma. Antes de un encargo o al abrir una sesión, Remi trae hasta tres: «Ojo: aquí ya pasó esto; la cura fue esta».

**Adaptarse: Remi propone, tú decides**Cuando una lección se repite, o algo funcionó limpio dos veces, Remi propone una regla de una línea para el oficio que toca o para las reglas de ese proyecto, y la pregunta como cualquier otra pregunta suya. Con tu sí queda escrita, con commit, y desde ahí viaja en cada encargo. Nunca cambia un oficio sola. Cómo terminó cada sesión (limpia, con arreglo después) sirve para que Remi aprenda qué forma de encargo funciona; jamás se muestra como contador (ley 3).

PARTE VIII

## Del encargo a producción

El trabajo principal de Remi: que Juan Camilo saque software **listo para producción, de principio a fin**, dirigiendo a Claude Code sin escribir el código él mismo. La IA escribe, prueba y corrige; lo que no puede hacer sola es entender el problema real, decidir la arquitectura, ver la seguridad que no se nota desde afuera y saber si lo entregado está bien o solo parece estar bien. Ese criterio lo pone Remi, al lado de Juan Camilo, mientras él construye el suyo. Remi no acepta nada «porque anda»: lo que se acepta, se revisó y se entendió. (Decidido el 3-oct, a partir del análisis del video sobre agentes de código.)

**Los cuatro límites de la IA, y quién los cubre****Contexto**: la IA arregla una parte y rompe otra porque no ve todo → cada proyecto tiene su `CLAUDE.md`, contratos, libro y lecciones. **Intención**: hace lo que se le pide, no lo que se quería decir → encargos con forma y «listo cuando», y Remi pregunta cuando hay duda en vez de adivinar. **Seguridad**: código que funciona y es inseguro → revisión de seguridad antes de cada entrega. **Arquitectura**: juicio, no técnica → diseño primero, contratos y fases; lo decide Juan Camilo con Remi.

**El paquete base de cada proyecto**Al abrir un proyecto nuevo (propio o de cliente), Remi crea lo mismo que tiene Remi: el libro en la bóveda con `tipo`, `ruta` y su `## Camino` del SOP; el `CLAUDE.md` del repo (qué es, stack, reglas que no se negocian, cómo se trabaja, «al cerrar: anotar_leccion»); `contratos/` con las formas de datos antes del código; y el oficio «producción» como lista de lo que falta. Lo que no sabe (cliente, alcance, monto), lo pregunta. Sin paquete base no sale el primer encargo.

**Remi revisa lo que entrega la IA**Cuando una sesión de Claude Code cierra con commits, Remi lee el diff contra el oficio «producción», las reglas de ese proyecto y sus lecciones, **con un modelo distinto del que escribió el código** (la mirada que no escribió es la que ve). Devuelve lo que no cumple, en orden de gravedad, cada cosa con su archivo y un encargo de arreglo listo. Nada se marca hecho en el Camino sin esa revisión. Es lo mismo que ya funciona a mano entre Claude Code, Grok y Claude en la app, hecho mecánico para no depender de acordarse (ley 2).

**Remi explica lo que cambió**Junto con la revisión, tres líneas sin jerga: qué se hizo, por qué, y qué se podría romper. Quien no entiende lo que construyó no lo puede arreglar cuando falla; así Juan Camilo aprende su propio software sin estudiar aparte (pilar «aprender»). Las tres líneas quedan en el episodio de la sesión y se pueden volver a pedir: «explícame cómo funciona el pago de UpVisuals».

**Nada a un cliente sin seguridad revisada**Antes de cada entrega a un cliente, la revisión de seguridad de Claude Code corre sobre el repo, y sus hallazgos pasan por Remi como cualquier revisión. Un hallazgo serio abierto bloquea el paso «Entrega» del Camino. La lista completa (identidad, datos, secretos, copias, monitoreo, legal, dominio) es la del oficio «producción»; Remi no dice «listo para producción» hasta que esté completa.

**La lista de la verdad**Antes de dar por entregada una fase, cuatro preguntas que Remi hace y Juan Camilo contesta: ¿se usó de verdad, no solo pasó las pruebas? ¿la revisión de otro modelo quedó sin pendientes graves? ¿entiendes qué cambió? ¿hay copia, monitoreo y forma de volver atrás? Si alguna es «no», la fase sigue abierta, sin culpa (ley 3): se encoge al paso que falta.

PARTE IX

## Rumbo

El segundo eje de Remi. **Hoy** responde «¿qué hago ahora?»; el **Rumbo** responde «¿a dónde voy y por qué esto primero?». La persona cuenta hablando cómo quiere que le vaya; Remi lo vuelve una meta medible, investiga los caminos posibles como lo haría un estratega (mercado, competidores, quién más mueve fichas, qué tan probable es con *sus* recursos), calcula, se deja contradecir por otro modelo y recomienda. Luego baja todo a una cuenta semanal que Hoy puede cumplir. (Diseño del 4-oct, segunda versión tras la crítica de la primera; maqueta en los tableros 6 a 10 del canvas «Hoy que se actualiza sola».)

### La idea que manda

**Ser experto no es adivinar mejor**Un modelo sabe teoría de juegos, estrategia y cómo se mide un mercado; eso lo pone Remi. Lo que ningún modelo sabe es qué te va a pasar a ti: eso sale de tus datos y de pruebas cortas. Por eso el Rumbo trabaja como un pronosticador serio: primero la tasa base (cuántos que lo intentan lo logran), luego el ajuste por tu punto de partida, y si no hay datos, dice «no se sabe» y propone la prueba que lo averigua. Un número inventado con seguridad es peor que ningún número.

**Para cualquier persona con TDAH**Meta, caminos, recursos y cifras salen de lo que la persona cuenta, de lo que Remi mide y de la investigación con fuentes. En el código no vive ningún dato de nadie; el ejemplo del canvas es una carga de datos.

**No es consejo financiero**Es análisis de decisiones del propio negocio. Los números son estimaciones con su origen a la vista; la decisión es siempre de la persona.

### El motor, en seis capas

| Capa                 | Quién la hace                        | Qué produce                                                                                                                                                                                                                                                                                                    |
|----------------------|--------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 · Punto de partida | Núcleo + lo que dice la persona      | Horas reales por semana (medidas), plata y gasto fijo, cuántos meses aguanta sin ingreso nuevo, habilidades con evidencia (proyectos hechos, tasa de cierre), lo que cuesta (seguimiento, terminar, concentración en un cliente) y lo que prefiere. Cada línea marcada *medido*, *dicho* o *pregunta*.         |
| 2 · Investiga        | Opus con búsqueda web                | Por camino: mercado contado de abajo hacia arriba (quiénes tienen el problema × cuántos pagan × cuántos alcanza esta persona en seis meses × precio), competidores con precio y flanco débil, y tasas base con fuente. Nunca «el mercado vale mil millones».                                                   |
| 3 · El juego         | Opus con el oficio «estratega»       | Quién más mueve fichas (competidor, plataforma, cliente, socio), qué le conviene, cómo reacciona si la persona entra o crece, y la jugada donde a nadie le conviene pelearle. Si hay un adversario real (una plataforma que detecta y banea, un cliente que aprieta el precio), el peor caso se modela con él. |
| 4 · Calcula          | Núcleo en Python, sin IA             | Simulación de seis meses (1.000 corridas) con los datos medidos y los supuestos visibles: probabilidad de llegar a la meta, peor caso realista y cuánto se aprende con cada prueba. La IA nunca pone el número final.                                                                                          |
| 5 · Se contradice    | Otro modelo, que no hizo el análisis | Objeciones: supuestos inflados, fuentes flojas, lo que pasa si sale mal. Lo que se acepta cambia el cálculo; todas quedan a la vista.                                                                                                                                                                          |
| 6 · Aprende          | Núcleo                               | Cada pronóstico se guarda con fecha. Al vencer, se compara con lo que pasó. Si Remi resulta optimista o pesimista con esta persona, corrige sus siguientes estimaciones y lo dice.                                                                                                                             |

El oficio «estratega» vive en la bóveda como cualquier oficio: teoría de juegos aplicada (jugadores, incentivos, reacción, compromiso creíble), tamaño de mercado de abajo hacia arriba, economía de cada cliente (cuánto deja, cuánto cuesta conseguirlo, cuánto dura), pronóstico con tasa base, valor de la información (cuándo una prueba vale más que pensar), reparto de tiempo entre apuestas y análisis previo de fracaso («imagina que salió mal: ¿por qué fue?»).

### La regla: la mayor ganancia, con la certeza de quien sabe

El Rumbo no busca lo más seguro ni lo más conocido: busca **la mayor ganancia esperada** (cuánto deja multiplicado por qué tan probable). Lo seguro no es lo tradicional ni lo de poco margen; lo seguro es lo que se sabe hacer. Un cirujano opera con 95 % de éxito lo que mataría a alguien que vio un tutorial: la misma jugada, distinta certeza. Por eso el Rumbo mide el **dominio** de la persona en cada cosa que pide un camino, con evidencia (proyectos entregados, ventas, pruebas pasadas), y lo marca *cirujano*, *sabe* o *aprendiz*.

**1 · Mayor ganancia esperada**Entre las opciones, sube la que más deja, no la más cómoda.

**2 · Grande donde eres cirujano**Donde el dominio es alto, la certeza es alta: ahí van más horas. Donde es aprendiz, apuesta chica hasta tener evidencia; con ella, el peso sube.

**3 · Nunca lo que no tiene vuelta**El único límite: ninguna apuesta puede dejar a la persona sin poder volver a jugar. Todo lo demás se permite.

**4 · Subir la certeza antes de subir la apuesta**Más contexto, una prueba, un cliente de ensayo: así algo que parecía arriesgado se vuelve seguro para esta persona. Remi distingue «haber visto el tutorial» de «saber operar» por la evidencia, no por la confianza.

### Realista sin ser pesimista

**Compararse con gente como uno**La tasa base es la del grupo más parecido (programadores solos que construyen con IA y venden a un nicho que conocen), no «todos los que lo intentan». La base equivocada es la fuente del pesimismo.

**Probable, posible, techo**Cada camino da tres números: lo probable si se hace lo de siempre, lo posible si se mueven las palancas, y el techo. Y responde: «¿qué te pone en el 10 % de arriba?».

**Apuestas de pérdida chica y premio grande**Construir le cuesta casi nada a quien trabaja con IA: eso permite probar tres ideas al mes. Remi prefiere varias apuestas baratas con techo alto a una sola apuesta cómoda.

**Jugadas que ganan pase lo que pase**Toda recomendación incluye una jugada que mejora la posición en cualquier escenario (un caso publicado, una pieza reusable, un cliente fijo más). Siempre tiene horas.

**Abrir el juego**Botón «Ábreme el juego»: antes de evaluar, Remi genera 20 jugadas con lentes distintos (invertir, cambiar quiénes juegan o las reglas, asociarse en vez de competir, cobrar por resultado, arbitraje de dólares contra pesos y de costo de IA contra precio, combinar ventajas raras, ¿qué haría alguien con 10 veces o una décima de los recursos?). Cada jugada debe citar evidencia del punto de partida; el código descarta las repetidas y las palabras de moda, y una jugada siempre cuestiona la meta misma. Van a la Bandeja; las que sobreviven 48 h se analizan.

**Varios jueces**Varios modelos estiman por separado y se promedia; los modelos tienden a ser optimistas y a dar la razón, así que el abogado del diablo es obligatorio. Antes de decidir, dos ejercicios: imaginar que salió mal y por qué, e imaginar que salió increíble y qué lo causó.

### La escalera sube con la persona

Arriba de la meta del momento vive el **norte** (para Juan Camilo, un millón de dólares de patrimonio; para otra persona, lo que ella diga). Entre la meta y el norte hay escalones. Cuando se cumple un escalón y se sostiene tres meses, Remi lo celebra (la única vez que el Rumbo usa `luz`), lo marca conquistado y propone el siguiente con su cuenta hacia atrás; cambia solo con el sí. El patrimonio cuenta además del ingreso: lo que se guarda y se pone a trabajar también sube la escalera. La mentalidad que sostiene esto no es arenga: es evidencia de lo ya ganado a la vista, apuestas cada vez más grandes donde ya hay dominio, y aprender rápido de lo que no salió, sin culpa (ley 3).

### Cómo se protege de los errores de la IA

La investigación del 4-oct (informes «Rumbo — herramientas parecidas» y «Rumbo — repos y foros» en el proyecto) dejó claro qué falla: los modelos tienden al sí y se confían de más, recomiendan todos las mismas estrategias de moda, varias copias del mismo modelo no se corrigen entre sí, los pronósticos sobre la propia conducta son los peor calibrados, y los sistemas personales mueren en silencio. Por eso el orden del motor es fijo:

| Paso                       | Regla                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 · Estimar a ciegas       | Tres modelos de familias distintas estiman cada uno por su lado. No saben qué camino prefiere la persona. La probabilidad de falla se pide en una llamada aparte. Un modelo separado extrae el número del razonamiento; nunca se lee con expresiones regulares.                                                                                                                                                                                          |
| 2 · Juntar en código       | Mediana en Python. Sin extremizar. Luego se mezcla con la tasa base y con la estimación de la persona, con pesos fijos en el código. La primera tasa base es la propia (su tasa de cierre real), antes que cualquier dato general.                                                                                                                                                                                                                       |
| 3 · Criticar               | Solo después de fijar los números: crítica anónima («Respuesta A, B, C») y abogado del diablo que debe encontrar al menos tres problemas. Si la crítica cambia algo, segunda ronda a ciegas opcional. Nunca debate antes de estimar: hace que todos converjan.                                                                                                                                                                                           |
| 4 · Recalibrar             | Cada pronóstico se guarda con fecha y una regla de sí o no fijada al hacerlo. Desde 10 resueltos, un recalibrador logístico (tomado de Metaculus/forecasting-tools, licencia MIT) corrige los siguientes y da dos números: cuánto se inclina al sí y qué tan confiado de más es. La gráfica de calibración se muestra desde 20–30 resueltos. Los pronósticos sobre la conducta de la persona («mando 2 propuestas») se calibran aparte de los del mundo. |
| 5 · Verificar fuentes      | Cada fragmento de fuente lleva un id. Cada cifra debe citar un id que exista (se revisa en código) y un modelo barato confirma que el fragmento dice eso. Cada cifra guarda URL, fecha y tipo (medido, fuente, supuesto).                                                                                                                                                                                                                                |
| 6 · Dimensionar la apuesta | Kelly solo como tope, alimentado con la probabilidad ya recalibrada. Nunca para decidir cuánto apostar, porque con probabilidades estimadas apuesta de más.                                                                                                                                                                                                                                                                                              |

### Lo que tomamos de afuera

| Pieza                            | De dónde                                         | Para qué en el Rumbo                                                                                                                                                                                                                       |
|----------------------------------|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Recalibrador logístico           | Metaculus/forecasting-tools (MIT, se copia)      | Paso 4 del motor                                                                                                                                                                                                                           |
| Programación basada en evidencia | Joel Spolsky, FogBugz (se reescribe, ~30 líneas) | El reloj: velocidad = estimado ÷ real por tipo de tarea; simulación del historial. «Dijiste 30 min → probablemente 50, a lo sumo 80.» Lo mismo con tasa de cierre y ticket para la cuenta hacia atrás. Ningún paso de Hoy pasa de ~90 min. |
| Crítica anónima                  | karpathy/llm-council (sin licencia, solo idea)   | Paso 3; sin su «presidente», porque pondría el número final                                                                                                                                                                                |
| Muestreo verbalizado             | CHATS-lab/verbalized-sampling (Apache)           | Solo para generar las 20 jugadas variadas; su «p» es qué tan típica es la idea, nunca su probabilidad de éxito                                                                                                                             |
| Archivo de visión                | Telos de Daniel Miessler (MIT)                   | Misión, metas, problemas, estrategias y métricas en un archivo fijo de la bóveda que todo el motor lee                                                                                                                                     |
| Pronóstico con fecha y regla     | Fatebook                                         | Forma de cada `pronostico`                                                                                                                                                                                                                 |
| Investigación con varias miradas | STORM (MIT), gpt-researcher (Apache)             | Preguntar desde varias personas expertas y ordenar fuentes antes de escribir                                                                                                                                                               |
| Equilibrios de dos jugadores     | Nashpy (MIT)                                     | Cuando el juego es simple y vale calcularlo                                                                                                                                                                                                |

No se toma: código AGPL o GPL dentro de Remi, repos sin licencia (se leen y se reescriben), debate antes de estimar, un modelo «presidente» que pone el número, puntos, niveles ni rachas, ni servicios completos como mem0 o PAI.

### Que el sistema no muera en silencio

**Latido**Si el reloj, el registro de pronósticos o la cuenta de la semana dejan de recibir datos dos días, Remi avisa una vez, sin culpa: «dejé de ver tus tiempos desde el martes; ¿los retomo?».

**Cero mantenimiento**Nada se arrastra solo al día siguiente como pendiente. Lo que no se hizo renegocia la cuenta de la semana.

**Poda mensual**Una vez al mes Remi mira qué partes del Rumbo se usan de verdad y propone quitar las que no.

### Cómo entra la visión

Hablando, desde el botón «Contar mi visión» del Rumbo o diciéndolo en la ventanita. Remi escucha sin interrumpir, saca cuatro cosas (cuánto al mes, por cuánto tiempo, qué es «estable», qué límites hay), pregunta una cosa a la vez lo que falta (máximo cuatro), lo devuelve en palabras de la persona y guarda la meta solo con su sí. Las versiones anteriores quedan en el historial. Si lo que la persona prefiere choca con su meta (plata rápida contra estabilidad), Remi lo nombra una vez, sin juzgar.

### Lo que se ve en la pantalla

| Pieza                           | Qué muestra                                                                                                                                                                                                                                                              |
|---------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| La meta                         | Una línea: rango, meses seguidos, límite por cliente, y dónde va (estable de verdad, meses buenos).                                                                                                                                                                      |
| La cuenta hacia atrás           | La meta convertida en lo que se hace esta semana: cuántas mensualidades hacen falta, cuántas hay, qué tasa de cierre tiene la persona y cuántas propuestas por semana salen de ahí. «Esta semana: 1 de 2 propuestas.» Es lo que baja a Hoy.                              |
| Tus horas                       | Una barra con el reparto de la semana entre caminos, más un margen sin planear. Se mueve tocándola.                                                                                                                                                                      |
| Apuestas                        | Dos o tres pruebas de dos semanas, cada una con tope de horas y plata, señal para seguir y señal para pausar, y en qué día van. Al día 14 hay tres salidas: sigue, se pausa, o se extiende una vez con una métrica más estrecha. Así nada vive para siempre por inercia. |
| Cómo se muestra la probabilidad | En frecuencias («3 de cada 10 futuros») con un rango bajo, medio y alto. La ruina va aparte, como línea roja; el ajuste («en 4 de 10 toca +6 h de ventas») va aparte también, con su tamaño.                                                                             |
| La recomendación                | Una frase, con por qué (con números del cálculo), qué la cambiaría y qué objetó el otro modelo. «Seguimos así» o «Quiero discutirlo».                                                                                                                                    |
| Análisis de un camino           | Una pantalla aparte, seis preguntas en orden: ¿hay a quién venderle? ¿quién ya lo hace? ¿quién más mueve fichas? ¿qué tienes a favor y en contra? ¿qué tan probable es? ¿qué objetó otro modelo? Termina en la prueba que responde la duda.                              |
| Punto de partida                | Una pantalla aparte con recursos, habilidades y lo que cuesta, cada línea con su origen. Se actualiza sola con lo medido.                                                                                                                                                |

### Cuándo corre

| Cuándo              | Qué                                                                                               | Costo                          |
|---------------------|---------------------------------------------------------------------------------------------------|--------------------------------|
| Cada día            | Hoy lee la cuenta de la semana y las apuestas                                                     | Sin IA                         |
| Cada domingo        | Diez minutos en Semana: qué entró, qué apuesta sigue o se pausa, cómo fueron las horas. Recalcula | Núcleo + una explicación corta |
| Al entrar un camino | Tras 48 h en la Bandeja (ley 6): investigación, juego, cálculo y objeciones                       | Opus con web + segundo modelo  |
| Cada mes            | Vuelve a investigar los caminos activos: el mercado cambia                                        | Opus con web                   |

### Qué guarda

#### partida

- **tipo** *— recurso \| habilidad \| cuesta \| preferencia*
- **texto** · **valor**
- **origen** *— medido \| dicho \| pregunta*

#### meta

- **piso** · **techo** · **meses_seguidos**
- **concentracion_max** · **limites**
- **vision_id** *— el texto dicho, literal*

#### camino

- **mercado** · **competidores** · **juego**
- **supuestos** *— cada uno con origen y editable*
- **fuentes** · **objeciones**
- **peso** *— % de horas, decidido por la persona*

#### apuesta

- **camino_id** · **inicio** · **fin**
- **tope_horas** · **tope_plata**
- **señal_sigue** · **señal_pausa**
- **resultado** *— sigue \| pausa \| extender una vez con métrica más estrecha*
- **la_volverias** *— pregunta a los 60 días*

#### pronostico

- **qué** · **valor** · **vence** · **regla_si_no**
- **tipo** *— mundo \| conducta propia*
- **real** *— al vencer*
- **error** *— para calibrar*

Cobrado, gastado, horas y propuestas se leen de las fichas de proyecto; no se duplican. Gastos propios van a la ficha de su proyecto; los comunes (membresía de Claude, herramientas) se reparten por horas para ver la ganancia real contra la meta.

### Cómo decide Hoy qué va primero

Tres reglas, en orden. **1)** Una fecha prometida gana siempre. **2)** Luego lo que cumple la cuenta de la semana (la propuesta que falta, el paso de una apuesta). **3)** Si empatan, lo que más acerca la meta *estable* por hora medida: una mensualidad pesa más que un pago único, y lo que baja la dependencia de un cliente suma. Hoy lo dice en una línea: «Es una mensualidad más y le quita peso a tu cliente grande. Eso es justo lo que pide tu meta.» Si no puede justificarlo, ordena por fecha. Sigue siendo una sola cosa.

### Qué cuida, ley por ley

**Ley 1**Los tiempos del cálculo son los medidos.

**Ley 3**Si va por debajo, nada se pone rojo ni cuenta meses fallados: «vamos por debajo; ¿ajustamos o seguimos?». Lo que cuesta se muestra para elegir caminos donde pese menos, nunca para juzgar.

**Ley 4**La pantalla principal tiene una meta, una cuenta, una barra, dos o tres apuestas y una frase. El análisis completo vive una capa abajo.

**Ley 6**Un camino nuevo pasa 48 h por la Bandeja antes de investigarse. Una apuesta termina en su fecha, no por impulso.

**Color y voz**La recomendación va en superficie con borde brasa; `luz` solo para escalones conquistados. Serif itálica corta, nunca «deberías», nunca promete resultados.

### Lo que no cambia

El Rumbo se construye **después** de T0 a T6, no toca los formularios A a H ni el código del panel hasta que el diseño esté aprobado. Hasta entonces: este diseño, la maqueta y la fase RU.

PARTE V

## El orden de construcción

Diseño primero, una fase a la vez, y ninguna fase empieza hasta que la anterior cumpla sus criterios. Este tablero no es una foto: **es el estado real del proyecto**. Marca un criterio y queda guardado; yo también lo actualizo cuando cerramos algo juntos. La fase en curso se enciende sola.

Estado local de esta visita.

### Fase RU · Rumbo (criterios)

Parte IX: el segundo eje, con motor de estratega en seis capas (punto de partida, investigación con fuentes, el juego, cálculo en el núcleo, objeciones de otro modelo, calibración). Baja a una cuenta semanal que Hoy cumple. Solo con el diseño aprobado y después de T0 a T6.

- [ ] Cuento mi visión hablando y Remi la devuelve como meta con piso, techo, meses y límite por cliente; cambia solo con mi sí
- [ ] Mi punto de partida aparece solo, cada línea marcada medido, dicho o pregunta
- [ ] Un camino que sale de la Bandeja trae mercado de abajo hacia arriba, competidores, el juego y tasa base, todo con fuente
- [ ] La probabilidad la calcula el núcleo con supuestos que puedo tocar; sin datos dice «no se sabe» y propone una prueba de dos semanas
- [ ] Otro modelo objeta cada análisis y sus objeciones se ven
- [ ] La cuenta hacia atrás me dice cuántas propuestas esta semana, y Hoy sube la que falta explicándolo en una línea
- [ ] Cada domingo, en diez minutos, decido qué apuesta sigue o se pausa con lo que pasó de verdad
- [ ] Después de un mes, Remi me muestra qué tan acertados fueron sus pronósticos y cómo se corrigió
- [ ] Cada camino trae probable, posible y techo, qué me pone en el 10 % de arriba, y dónde soy cirujano o aprendiz con evidencia
- [ ] «Ábreme el juego» me deja 20 jugadas en la Bandeja y las que sobreviven vuelven analizadas
- [ ] Al sostener un escalón tres meses, Remi lo celebra y me propone el siguiente; cambia solo con mi sí
- [ ] El reloj me dice cuánto me toma de verdad cada tipo de tarea, con mi velocidad real, y ningún paso de Hoy pasa de 90 min
- [ ] Cada cifra cita una fuente que existe y que fue revisada; los números salen de tres modelos a ciegas y una mediana en código
- [ ] Si el Rumbo deja de recibir datos dos días, Remi me avisa una vez, sin culpa


Método por pantalla: mockup con propuestas A/B/C → aprobación → código → Impeccable al final. Cada prompt a Claude Code es una sola tarea y un solo commit, con la skill `/remi` cargada. Para usar a Remi con un cliente desde hoy: `docs/GUIA-HOY.md` (qué decirle, qué existe, qué no intentar todavía). Trabajo en paralelo: un worktree por terminal, una terminal por área de archivos, solo main corre `actualizar.sh`, orden de merge f-ventanita → f-fase3 → f-notion → f-telegram.

**Remi** · La Biblia, versión 4.2 — 4 de octubre de 2026: nace la Parte IX, el Rumbo — un estratega que vuelve la visión en meta y escalera, investiga con fuentes, calcula en código, se deja contradecir y aprende de sus pronósticos, y le dice a Hoy qué va primero; Hoy se actualiza sola (Al día, hitos que se cierran con evidencia, avisos, ficha de cliente); 45 min entre avisos; la ventanita se apila y el modo va en el chip. Antes, v4.1 — 3 de octubre de 2026: las preguntas de Remi esperan en el panel y nunca salen en el chat ni por Telegram; la conversación ya no se corta a los 60 min. Antes, v4.0 — mismo día: nace la Parte VIII, del encargo a producción — el paquete base de cada proyecto, Remi que revisa lo que entrega la IA con otro modelo y explica lo que cambió, y nada a un cliente sin seguridad revisada; fase PR después de los siete días. Antes, v3.9 — 1 de octubre: lo que la v1 tenía y vuelve, el panel construido, la configuración desde el panel, el camino desde el SOP, la decisión de hosting los campos que el panel pedía en tres contratos, Remi que pregunta lo que le falta, y la experiencia como memoria: lecciones con evidencia y reglas que Remi propone. Cambiarla es válido; ignorarla no.

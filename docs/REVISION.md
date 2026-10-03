# Revisión contra la Biblia — resultados

Plan: `docs/PLAN-REVISION.md`. Banco: `python3 scripts/banco.py arrancar | frases | parar`
(núcleo aislado en :4499, copias de base y bóveda en `$TMPDIR/remi-banco`).

Estados: **pasa** · **falla** (con evidencia) · **difiere** (cambio decidido después de la
Biblia: Juan Camilo dice cuál manda) · **no existe** · **por ver en la app** (el código está;
falta probarlo contigo) · *pendiente*.

## R1 · La ventanita

| # | Promesa | Código / banco (3-oct) | En la app | Estado |
|---|---|---|---|---|
| 1 | Flota siempre encima, arrastrable | Se arrastra (`startDragging`). **Siempre encima no**: `e802988` (1-oct) lo quitó a propósito, «que se apile como cualquier ventana» | — | **difiere** |
| 2 | 1 click escribe · 2 dicta · 3 dialoga | `gestos.ts`, con pruebas; el log registra cada gesto | probar | por ver en la app |
| 3 | ⌃⌥R dicta desde cualquier app | `Control+Alt+R` registrado en `lib.rs` | probar | por ver en la app |
| 4 | Colores por estado; solo «escuchando» pulsa | `status-dot[data-estado]` en `App.css` | mirar | por ver en la app |
| 5 | Una X cancela siempre | `cancelar_escucha` borra el audio sin transcribir | probar | por ver en la app |
| 6 | Flecha al acercar el mouse elige el modo | La bitácora registra que se quitó la flechita; el modo va en el chip | — | **difiere** |
| 7 | Micrófono solo en «escuchando» | ffmpeg arranca al escuchar y se cierra al parar; el micrófono caliente (V2 b) no se hizo | mirar el punto naranja | por ver en la app |
| 8 | Whisper large local | `large-v3-turbo` residente en :4401; dictado de 57 s → 991 ms al parar (V1) | dictar 10 s y 50 s | por ver en la app |
| 9 | Kokoro, 4 voces, Alex por defecto, 1×/1,5×/2× | 4 voces (Alex, Dora, Santa, Bella); velocidades `[1, 1.5, 2]` | escuchar | por ver en la app |
| 10 | El diálogo corta solo al callar | 1,4 s de silencio, umbral adaptativo | 5 turnos | por ver en la app |
| 11 | Voz < 8 s (robustez); ≤ 4,5 s al primer sonido (V3) | La línea `latencia` está en el log | 5 turnos | por ver en la app |
| 12 | Muletilla mientras piensa | `decirMuletilla` antes del primer audio | escuchar | por ver en la app |
| 13 | Clasificador sin IA: idea · hoy · hecha | idea ✓, hoy ✓, «Gracias.» no crea nada ✓, «anota esto:» guarda solo el contenido ✓. **«listo, ya terminé» → idea**: no cierra el bloque y queda en la Bandeja (solo cierra si la frase es *exactamente* «listo», «ya terminé»…) | — | **falla** |
| 14 | Tres modos: Haiku, Sonnet, Opus | El chip manda el modo; el log dice el modelo | elegir cada uno | por ver en la app |
| 15 | Chips por proveedor | Claude ✓ en el banco; Groq dio 429 el 2-oct | probar los cinco | por ver en la app |
| 16 | Claude agotado → OpenRouter, chip real | Con pruebas (`test_limite_alcanzado…`) | — | pasa (pruebas) |
| 17 | Ley 1: «la última vez te tomó…» al planear | Volver a abrir la misma tarea en el banco: la voz no lo dice; `/ultima-vez` lo da al Reloj | mirar el Reloj | por ver en la app |
| 18 | Ley 6: una idea enfría 48 h | `enfria_hasta` = +48 h ✓ | — | pasa |
| 19 | Ordenar lo dictado en un prompt | Modo prompt: «arreglar el login…» **pregunta qué repo en vez de armar el encargo con el hueco marcado** (F2.2b) | — | **falla** |
| 20 | «Me escribió X» → lectura, riesgos, respuesta; nunca envía | Sale con LECTURA…; **16,6 s** | — | pasa (lento) |
| 21 | Pregunta lo que le falta, de a una | Con pruebas; 8 preguntas reales en el núcleo | ver una | por ver en la app |
| 22 | Sabe en qué estado está | **«¿estás funcionando bien? ¿qué te falta?» → «Tengo 3 preguntas pendientes. Mira Proyectos.»**: la regla de «¿qué falta?» se come la pregunta. Y el 3-oct dijo que el núcleo no arranca y que Notion falla: las dos falsas | — | **falla** |
| 23 | Ley 5: nudge de cuerpo al cerrar un bloque largo | Bloque largo = más de 90 min | cerrar uno largo | por ver en la app |
| 24 | Ley 3: «Ahora no» encoge, nunca crece, no se cuenta | Con pruebas en `test_nudges.py` | responder «Ahora no» | por ver en la app |
| 25 | Presupuesto de silencio | 5 al día ✓; **45 min entre dos** (la Biblia dice 90 en «Actuar» y 45 en la Parte VII) | — | **difiere** (la Biblia misma) |

Otras cosas que salieron del guion:
- La charla coló voseo («querés») con Haiku: sigue la duda de F2.
- «¿qué tengo pendiente hoy?» contestó con algo del Estado del libro de Remi escrito por la
  máquina («correr test_tema_dudoso»): a revisar en R2.

## R2 · Cerebro y memoria — *pendiente*

## R3 · Núcleo e indestructible — *pendiente*

## R4 · Panel — *pendiente*

## R5 · Telegram y espejos — *pendiente*

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
| 3 | ⌃⌥R dicta desde cualquier app | `Control+Alt+R` registrado en `lib.rs` | Juan Camilo, 3-oct: funciona (había probado con ⌘) | **pasa** |
| 4 | Colores por estado; solo «escuchando» pulsa | `status-dot[data-estado]` en `App.css` | mirar | por ver en la app |
| 5 | Una X cancela siempre | `cancelar_escucha` borra el audio sin transcribir | probar | por ver en la app |
| 6 | Flecha al acercar el mouse elige el modo | La bitácora registra que se quitó la flechita; el modo va en el chip | — | **difiere** |
| 7 | Micrófono solo en «escuchando» | ffmpeg arranca al escuchar y se cierra al parar; el micrófono caliente (V2 b) no se hizo | mirar el punto naranja | por ver en la app |
| 8 | Whisper large local | `large-v3-turbo` residente en :4401; dictado de 57 s → 991 ms al parar (V1) | dictar 10 s y 50 s | por ver en la app |
| 9 | Kokoro, 4 voces, Alex por defecto, 1×/1,5×/2× | 4 voces (Alex, Dora, Santa, Bella); velocidades `[1, 1.5, 2]` | escuchar | por ver en la app |
| 10 | El diálogo corta solo al callar | 1,4 s de silencio, umbral adaptativo | 5 turnos | por ver en la app |
| 11 | Voz < 8 s (robustez); ≤ 4,5 s al primer sonido (V3) | La línea `latencia` está en el log | 3-oct, 5 turnos reales: `→primer_sonido` 3448, 3625, 4566, 5327, 5929 ms (mediana 4,6 s) | **pasa** < 8 s; al borde de 4,5 |
| 12 | Muletilla mientras piensa | `decirMuletilla` antes del primer audio | escuchar | por ver en la app |
| 13 | Clasificador sin IA: idea · hoy · hecha | «listo, ya terminé» caía como idea. **Arreglado** en `d433f10`: dos cierres seguidos también cierran | decir «listo, ya terminé» con un bloque abierto | arreglado, por ver en la app |
| 14 | Tres modos: Haiku, Sonnet, Opus | El chip manda el modo; el log dice el modelo | elegir cada uno | por ver en la app |
| 15 | Chips por proveedor | Claude ✓ en el banco; Groq dio 429 el 2-oct | probar los cinco | por ver en la app |
| 16 | Claude agotado → OpenRouter, chip real | Con pruebas (`test_limite_alcanzado…`) | — | pasa (pruebas) |
| 17 | Ley 1: «la última vez te tomó…» al planear | Volver a abrir la misma tarea en el banco: la voz no lo dice; `/ultima-vez` lo da al Reloj | mirar el Reloj | por ver en la app |
| 18 | Ley 6: una idea enfría 48 h | `enfria_hasta` = +48 h ✓ | — | pasa |
| 19 | Ordenar lo dictado en un prompt | Preguntaba en vez de armar el encargo. **Arreglado** en `b42c350`: seis secciones en 6 de 6 en el banco (antes 0 de 3 y 1 de 3) | dictar un encargo | arreglado, por ver en la app |
| 20 | «Me escribió X» → lectura, riesgos, respuesta; nunca envía | Sale con LECTURA…; **16,6 s** | — | pasa (lento) |
| 21 | Pregunta lo que le falta, de a una | Con pruebas; 8 preguntas reales en el núcleo | ver una | por ver en la app |
| 22 | Sabe en qué estado está | Inventaba fallas. **Arreglado** en `b638761`: contesta con `doctor.sh` medido; 3 de 3 en el banco | preguntarle «¿estás funcionando bien?» | arreglado, por ver en la app |
| 23 | Ley 5: nudge de cuerpo al cerrar un bloque largo | Bloque largo = más de 90 min | cerrar uno largo | por ver en la app |
| 24 | Ley 3: «Ahora no» encoge, nunca crece, no se cuenta | Con pruebas en `test_nudges.py` | responder «Ahora no» | por ver en la app |
| 25 | Presupuesto de silencio | 5 al día ✓; **45 min entre dos** (la Biblia dice 90 en «Actuar» y 45 en la Parte VII) | — | **difiere** (la Biblia misma) |

Lo que salió de la prueba en la app del 3-oct (Juan Camilo):

| # | Lo que pasó | Arreglo | Estado |
|---|---|---|---|
| 26 | Al minimizar, cerrar con la X o reabrir, parecía que Remi se olvidaba de la charla (volvían 3 mensajes en gris) | `fb43d87`: vuelve la conversación entera | arreglado, por ver en la app |
| 27 | La conversación se cortaba sola a los 60 min | `990f579`: sigue hasta que él la cambie (decisión suya; cambia la Biblia) | arreglado, por ver en la app |
| 28 | En la conversación por voz no había cómo parar el micrófono (más de 20 clicks ignorados) | `e04fef4`: botón «Parar» al lado del chip del modelo | arreglado, por ver en la app |
| 29 | «no pude reproducir el audio del núcleo» en el log | No es falla: el audio sonó entero; el aviso sale de más al pasar a la frase siguiente | pendiente menor (solo el log) |

Otras cosas que salieron del guion:
- La charla coló voseo («querés», «vos», «necesitás») con Haiku: sigue la duda de F2.
- «¿qué tengo pendiente hoy?» contestó con algo del Estado del libro de Remi escrito por la
  máquina («correr test_tema_dudoso»): a revisar en R2.

## R2 · Cerebro y memoria — *pendiente*

## R3 · Núcleo e indestructible — *pendiente*

## R4 · Panel — *pendiente*

## R5 · Telegram y espejos — *pendiente*

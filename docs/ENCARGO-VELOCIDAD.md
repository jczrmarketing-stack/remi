# Encargo · velocidad de Remi (2-oct, 21:30)

Quién lo pide: Juan Camilo. «Lo más importante es que sea lo más rápido posible en todo.»
Quién lo escribe: Claude en la app, leyendo `~/Library/Logs/Remi/ventanita.log` y `nucleo.log` del 2-oct 21:00–21:25.
Quién lo construye: la terminal, en este orden. **Un punto = un commit.** Cada punto trae su «listo cuando» medido en el log; si no mejora el número, no se cierra.

## Lo ya hecho (no repetir) — commits en main
- `e901045`, `490f337`: conversación por voz — texto difuminado antes de bajar la bolita, flecha ◂ para volver al texto, corte por silencio 2000 → 1400 ms (`SILENCIO_PARA_CORTAR` en `voz.rs`).
- `fce2f68`: `hablar()` en frases (la primera suena cuando está lista, las demás se generan mientras tanto). `dividirEnFrases` en `voz.ts`.
- `cbeb3e8`: muletilla instantánea («Mmm, a ver…») al terminar de hablarle por voz (`decirMuletilla`, `precalentarMuletillas`).
- `71927b1`: la velocidad 1,5× la genera Kokoro (`speed` en `POST /tts`); el reproductor solo completa el 2×.
- `04af875`: al parar un dictado, lo ya transcrito queda a la vista y la versión final lo completa (`dictado:adelantado` en el log).
- `7962cc9`: Groq es una opción del chip de cerebro (`{motor:"groq"}`).
- Ojo: vitest de estos commits **no se ha corrido** (`tsc` pasa). Correrlo antes de empezar: `bash scripts/recargar.sh --vigilar` y pedir `vitest`.

## Dónde se va el tiempo hoy (medido)
Conversación por voz, 2.º intercambio del log de las 21:09, desde que Juan Camilo deja de hablar:

| Tramo | Hoy | Dónde |
|---|---|---|
| esperar silencio | 2000 ms (ahora 1400) | `voz.rs` `SILENCIO_PARA_CORTAR` |
| Whisper | ~1000 ms (4,5 s de audio) | `transcribir_con_servidor` |
| Haiku por la CLI | 3300–5500 ms para 15–60 tokens de salida; 10350 ms para 315 | `pensar._una_llamada_claude` |
| TTS | primera frase ~1 s | `nucleo/tts.py` |

Dictado: 55 s de audio → Whisper tardó **5887 ms** al parar (21:22:43). El costo crece con el largo.
Arranque del micrófono: «el wav apareció a los 250 ms» casi siempre, pero **1750 ms** una vez (21:53); en ese hueco se pierden las primeras palabras.

## V1 · El dictado no espera por lo ya dicho (Rust, `voz.rs`)
Hoy `transcribir_parcial` vuelve a pasar **todo** el wav por Whisper cada 1,5 s y al parar se pasa todo otra vez.
1. Guardar en el estado de la grabación: `bytes_confirmados` (hasta dónde ya es texto definitivo) y `texto_confirmado`.
2. Confirmar un trozo cuando hay una pausa (reusar la detección de silencio de la vigilancia: nivel bajo el umbral ≥ 400 ms) o cuando el pendiente pasa de ~12 s. Se corta **en la pausa**, nunca a mitad de palabra; el trozo siguiente arranca con ~300 ms de solape para no perder la primera sílaba.
3. `transcribir_parcial` y `detener_escucha_y_transcribir` transcriben **solo desde `bytes_confirmados`** y devuelven `texto_confirmado + nuevo`.
4. Prueba Rust de la función que decide el corte (pausa → corte; sin pausa a los 12 s → corte; nunca dentro de voz).
**Listo cuando:** un dictado de ≥ 40 s deja el texto final < 1500 ms después de parar (`[voz] whisper residente: N ms` del último trozo), y el texto final es igual o mejor que el de hoy en un clip de prueba de 55 s (comparar a ojo las dos transcripciones).

## V2 · Micrófono sin hueco al empezar (Rust)
Medir primero: tiempo entre `grabando: …ffmpeg` y `el wav apareció` en 20 arranques.
- Opciones: (a) ffmpeg con `-fflags nobuffer -flags low_delay` y `-audio_buffer_size` pequeño; (b) calentar el dispositivo al abrir el chat (ffmpeg corriendo, audio descartado hasta el click) y soltarlo a los 30 s de inactividad.
- **(b) prende el indicador naranja del micrófono de macOS mientras el chat esté abierto y toca privacidad (pacientes, finanzas). No se hace sin que Juan Camilo lo diga en el chat.** Empezar por (a) y reportar el número.
**Listo cuando:** `el wav apareció` ≤ 400 ms en 19 de 20 arranques.

## V3 · Streaming: hablar con la primera frase (núcleo + ventanita)
Hoy `POST /mensaje` devuelve todo junto; la voz espera a la respuesta completa (10 s en la de 315 tokens).
1. Núcleo: `POST /mensaje/stream` (NDJSON o SSE) que emite `{"frase": "..."}` por cada oración completa y al final `{"fin": {…lo mismo que devuelve /mensaje hoy…}}`.
   - Groq / OpenRouter / Venice / Ollama: `"stream": true` del cliente OpenAI-compatible (`_llamar_openai_compatible`).
   - Claude: `--output-format stream-json --include-partial-messages` en `_comando`.
   - Mismo guardado de turnos, mismas reglas (anti-invento, límites, respaldo). Si el stream falla a la mitad, el cliente cae a `/mensaje` normal sin decir nada.
2. Ventanita (`servidor.ts`, `App.tsx`): consumir el stream; el chat muestra el texto creciendo; `hablar()` recibe cada frase en cuanto llega y las encadena (la muletilla sigue sonando primero).
3. Instrumentar en el log una línea por turno de voz: `latencia fin_habla→transcrito=… →primera_frase=… →primer_sonido=…`.
**Listo cuando:** con Groq, `fin_habla→primer_sonido` ≤ 2000 ms (sin contar el silencio de 1400); con Haiku, ≤ 4500 ms. Sin regresión en los tests de núcleo (pytest) ni de ventanita (vitest).

## V4 · Por qué Haiku manda 10.000 tokens y no usa la caché (núcleo)
`nucleo.log`: 10 de las últimas 12 llamadas con `cache_leida=0 cache_escrita≈10 000`. Dos de 12 con `cache_leida≈9 200`.
1. Averiguar qué cambia entre llamadas en el prefijo (¿el índice de memoria, `ENCABEZADO_ASOCIADOS`, la precarga, el orden del system prompt, la config MCP con ruta temporal distinta cada vez?) y estabilizarlo. Las partes variables, al final.
2. Medir cuánto de esos 10 000 son las herramientas y el MCP del estante. Para un turno de voz que no pide leer memoria ni buscar: probar `--tools ""` y sin MCP, y comparar `ms`.
3. No quitar el estante a las conversaciones que lo necesitan: decidir con regla simple (sin IA) cuándo se carga.
**Listo cuando:** `cache_leida > 0` en ≥ 8 de 10 llamadas seguidas y la mediana de `ms` de Haiku baja de ~4400 a ≤ 3000, sin que cambie lo que Remi contesta en 5 frases de prueba.

## Después, solo si lo anterior no alcanza
«Pensar en voz alta»: un modelo rápido (Groq) suelta 3–5 reacciones cortas mientras el bueno piensa. Reglas: solo reacciona y duda, **nunca afirma datos** (Haiku ya pisó libros tres veces); no se contradice con la respuesta final; una locura por pantalla. No empezar sin ver las cifras de V3.

## Reglas
Leyes de Remi y Design System intactos. Nada de voseo. Sin hex a mano. Cada punto, con prueba o con captura del log.

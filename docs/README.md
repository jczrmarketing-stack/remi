# docs/

Pon aquí `vision.md` (los 6 problemas y el detalle de fases). La Biblia y el Design System viven como artefactos en claude.ai; aquí solo notas de trabajo.

## Estado (espejo de solo lectura de la Biblia — la Biblia manda)

- **Fase 0.3 (esqueleto que camina) — cerrada.** Núcleo con uv: contratos → modelos (`extra="forbid"`), SQLite (`remi.db`) con las 5 tablas del contrato, `POST /mensaje` crea Tarea+Sesion y responde en voz de Remi, `GET /hoy` devuelve tareas + historial de sesiones. `uv run pytest` y `uv run mypy .` limpios.
- **Fase 2a (núcleo sostiene las leyes) — cerrada.** Sesiones se cierran de verdad (`real_min` calculado), `POST /tarea/{id}/estado`, `GET /tarea/{id}/historial`, `/hoy` con `ultima_vez_min`, `paso_minimo` universal + `POST /tarea/{id}/paso-minimo`, FK+índice en sesiones.
- **Fase 2b (ventanita terminada) — en curso.** Reposo pasa a píldora 120×44 (antes 320×180, medida de antes de elegir la variante C — **pendiente que Milo actualice esta medida en la Biblia real**, este archivo es solo el espejo).
- **Hallazgo para el Design System (pendiente que Milo lo lleve al artefacto real):** el punto en reposo usaba `dormido`, que es el mismo valor que `line` (#3a302d) — sobre `surface` da 1.5:1 de contraste y no se ve. Se cambió en código a `baja` (2.6:1) mientras tanto.
- **Fase 2d (la ventanita completa) — construida el 29 sep 2026, pendiente la prueba a mano de Milo.** Voz por calidad real (voiceURI) con aviso por consola; velocidad 1×/1.5×/2× persistida junto al mute; «pensar con Claude» opt-in por mensaje (`think` en `POST /mensaje`, clave en `nucleo/.env`, tokens solo a consola); leer en voz alta y copiar en la respuesta; «hace N min» en reposo (ley 1); atajos con «·· hablar» y «··· dialogar»; «transcribiendo» visible en `pensar`; detector de silencio con wav sin atraso, hilo cancelable y tope de 10 s sin voz.
- **Hallazgos para la Biblia / el Design System (pendiente que Milo los lleve):** (a) en esta Mac no hay ninguna voz Premium/Enhanced en español descargada — la ventanita cae a Paulina/Mónica compactas hasta que se descargue una en Ajustes → Accesibilidad → Contenido hablado; (b) el reposo con «hace N min» mide 120×64 (sin historia sigue en 120×44); (c) **cerrado** — `ink-faint` estaba usado a 11-12 px (atajos, «hace N min», toggle y controles de voz), y el DS lo reserva para ≥24 px: todo eso pasó a `ink-muted`, y el estado activo a `ink`. En la ventanita ya no queda ningún uso de `ink-faint`.
- Actualizar la Biblia en claude.ai con estos cierres queda pendiente — este archivo es el espejo local, no la fuente.

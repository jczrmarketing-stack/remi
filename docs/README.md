# docs/

Pon aquí `vision.md` (los 6 problemas y el detalle de fases). La Biblia y el Design System viven como artefactos en claude.ai; aquí solo notas de trabajo.

## Estado (espejo de solo lectura de la Biblia — la Biblia manda)

- **Fase 0.3 (esqueleto que camina) — cerrada.** Núcleo con uv: contratos → modelos (`extra="forbid"`), SQLite (`remi.db`) con las 5 tablas del contrato, `POST /mensaje` crea Tarea+Sesion y responde en voz de Remi, `GET /hoy` devuelve tareas + historial de sesiones. `uv run pytest` y `uv run mypy .` limpios.
- **Fase 2a (núcleo sostiene las leyes) — cerrada.** Sesiones se cierran de verdad (`real_min` calculado), `POST /tarea/{id}/estado`, `GET /tarea/{id}/historial`, `/hoy` con `ultima_vez_min`, `paso_minimo` universal + `POST /tarea/{id}/paso-minimo`, FK+índice en sesiones.
- **Fase 2b (ventanita terminada) — en curso.** Reposo pasa a píldora 120×44 (antes 320×180, medida de antes de elegir la variante C — **pendiente que Milo actualice esta medida en la Biblia real**, este archivo es solo el espejo).
- **Hallazgo para el Design System (pendiente que Milo lo lleve al artefacto real):** el punto en reposo usaba `dormido`, que es el mismo valor que `line` (#3a302d) — sobre `surface` da 1.5:1 de contraste y no se ve. Se cambió en código a `baja` (2.6:1) mientras tanto.
- Actualizar la Biblia en claude.ai con estos cierres queda pendiente — este archivo es el espejo local, no la fuente.

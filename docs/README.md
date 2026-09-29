# docs/

Pon aquí `vision.md` (los 6 problemas y el detalle de fases). La Biblia y el Design System viven como artefactos en claude.ai; aquí solo notas de trabajo.

## Estado (espejo de solo lectura de la Biblia — la Biblia manda)

- **Fase 0.3 (esqueleto que camina) — cerrada.** Núcleo con uv: contratos → modelos (`extra="forbid"`), SQLite (`remi.db`) con las 5 tablas del contrato, `POST /mensaje` crea Tarea+Sesion y responde en voz de Remi, `GET /hoy` devuelve tareas + historial de sesiones. `uv run pytest` y `uv run mypy .` limpios.
- **Siguiente: Fase 1 (ventanita).** `apps/ventanita` sigue sin código, solo README.
- Actualizar la Biblia en claude.ai con este cierre queda pendiente — este archivo es el espejo local, no la fuente.

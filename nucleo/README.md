# Núcleo (Fase 0.3 en adelante)

Python. Corre siempre en el Mac:
- `whisper/` — voz → texto, offline
- `reglas/` — prioridad, nudges, enfriamiento (determinista, sin IA, con pruebas)
- `tiempo/` — duración real de cada Sesión (Ley 01)
- `db/` — SQLite `remi.db`, fuente de verdad (jamás en git)
- `espejos/` — Notion / GCal / Telegram; solo leen objetos `compartible: true`

Los modelos se generan de `contratos/contratos.json`.

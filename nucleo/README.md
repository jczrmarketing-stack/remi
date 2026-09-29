# Núcleo (Fase 0.3 en adelante)

Python. Corre siempre en el Mac:
- `whisper/` — voz → texto, offline
- `reglas/` — prioridad, nudges, enfriamiento (determinista, sin IA, con pruebas)
- `tiempo/` — duración real de cada Sesión (Ley 01)
- `db/` — SQLite `remi.db`, fuente de verdad (jamás en git)
- `espejos/` — Notion / GCal / Telegram; solo leen objetos `compartible: true`

Los modelos se generan de `contratos/contratos.json`.

## Pensar con Claude (opt-in, `pensar.py`)

Solo corre si la ventanita manda `think: true` en `POST /mensaje`; por defecto no llama a nadie.

Va por la **CLI de Claude Code** (`claude -p`), con la sesión con la que Milo ya está logueado —
**no** por la API con clave, que se factura aparte del plan. No hay `.env` ni `ANTHROPIC_API_KEY`:
el módulo las **borra** del entorno del subproceso, para que ni existiendo en el shell se termine
facturando por fuera.

- Modelo por defecto: `haiku`. Se cambia con `REMI_CLAUDE_MODELO` (cualquier alias que acepte la CLI).
- Techo de salida: 200 tokens, con el razonamiento apagado (`MAX_THINKING_TOKENS=0`). El techo
  cuenta toda la salida y el razonamiento entra ahí: sin apagarlo, 200 no alcanzan ni para una frase.
- La frase entra por stdin, nunca como argumento: no aparece en la lista de procesos.
- Corre sin herramientas, sin MCP, sin settings del usuario y en un directorio vacío, para que no
  cargue el `CLAUDE.md` del repo.

La cuenta sale por la consola del núcleo (`[claude] modelo=… tokens entrada=… salida=…`) y por la
del webview; nunca en pantalla. Si `claude` no está en el PATH, tarda más de 6 s o falla, la
respuesta sigue por el camino sin IA, en silencio.

# Núcleo (Fase 0.3 en adelante)

Python. Corre siempre en el Mac:
- `whisper/` — voz → texto, offline
- `reglas/` — prioridad, nudges, enfriamiento (determinista, sin IA, con pruebas)
- `tiempo/` — duración real de cada Sesión (Ley 01)
- `db/` — SQLite `remi.db`, fuente de verdad (jamás en git)
- `espejos/` — Notion / GCal / Telegram; solo leen objetos `compartible: true`

Los modelos se generan de `contratos/contratos.json`.

## Pensar con Claude (opt-in, `pensar.py`)

Solo corre si la ventanita manda `think: true` en `POST /mensaje`; por defecto cero tokens.
La clave va en **`nucleo/.env`** (ya excluido por el `.gitignore` de la raíz), jamás en el repo:

```
ANTHROPIC_API_KEY=sk-ant-…
# opcional; por defecto claude-opus-5
REMI_CLAUDE_MODELO=claude-opus-5
```

La cuenta de tokens sale por la consola del núcleo (`[claude] … tokens entrada=… salida=…`) y por
la del webview; nunca en pantalla. Sin clave o sin red, la respuesta sigue por el camino sin IA.

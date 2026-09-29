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

## La voz de Remi (`tts.py`)

Kokoro-82M local, en CPU, sin clave y sin red después de la primera vez. Hace falta
`brew install espeak-ng` (sin eso el español se rompe; el inglés anda igual).

Cuatro voces, ni una más. El prefijo del id marca el idioma: `e…` español, `a…` inglés.

| id | idioma | etiqueta |
|---|---|---|
| `em_alex` | es | Alex (ES) — la de todos los días |
| `ef_dora` | es | Dora (ES) |
| `em_santa` | es | Santa (ES) |
| `af_bella` | en | Bella (EN) |

- `POST /tts` `{"text": "…", "voice": "em_alex"|null, "speed": 1.0}` → `audio/wav` 24 kHz mono.
  Sin `voice` (o `"auto"`) la elige el texto: español salvo que sea claramente inglés.
- `GET /tts/voices` → las cuatro, con `id`, `lang` y `label`.
- Texto vacío → 204. Voz que no existe → 400. Motor caído → 503 sin cuerpo, y la ventanita cae
  a la voz del sistema **en silencio**: Remi nunca dice un error en voz alta (ley 3).

La velocidad (1× / 1.5× / 2×) la hace el reproductor de la ventanita, que conserva el tono;
pedírsela al modelo le cambiaría la prosodia. Por eso se genera siempre a 1.0.

El modelo se carga en un hilo al arrancar (`python servidor.py`): la primera carga tarda ~18 s y
después cada frase sale en ~1 s. Importar el módulo no carga nada, así que las pruebas no pagan
esos 300 MB.

Prueba de humo (genera los cuatro wav en `vendor/kokoro/salida/`, fuera de git):

```bash
cd nucleo && uv run python ../vendor/kokoro/tts_kokoro.py
```

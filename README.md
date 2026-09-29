# Remi

Asistente personal para TDAH de Juan Camilo. Una persona, un Mac, cero culpa.

- **Ley del repo:** `CLAUDE.md` (léelo primero; Claude Code lo carga siempre).
- **Contratos:** `contratos/contratos.json` — el idioma entre capas.
- **Tokens:** `design/tokens.json` — export del Design System; no se edita a mano.
- **Fuentes de verdad:** Design System (tokens) → Biblia (leyes y arquitectura) → este repo (ejecución). Notion es espejo.

## Estructura

| Carpeta | Qué es | Fase |
|---|---|---|
| `nucleo/` | Python: Whisper local, reglas sin IA, medidor de tiempo, SQLite | 0.3 |
| `apps/ventanita/` | Tauri 2 + React + Tailwind — la ventanita flotante | 1 |
| `apps/panel/` | Next.js PWA — Hoy, Proyectos, Metas, Bandeja | 2–3 |
| `contratos/` | Contratos JSON congelados | 0.1 |
| `docs/` | vision.md y notas | — |

El estado de fases vive en la **Biblia de Remi** (artefacto), no aquí.

## Instalar en el Mac

```bash
# 1. El núcleo, como servicio que arranca con el Mac
./scripts/instalar.sh

# 2. La app
cd apps/ventanita && npm run tauri -- build --bundles app
cp -R src-tauri/target/release/bundle/macos/Remi.app /Applications/
```

Después, Remi se abre desde Launchpad o Spotlight y la terminal puede estar cerrada.
Abrirla estando abierta no crea otra ventana: trae la que hay.

**El repo no se puede mover.** Las rutas de `config/` se resuelven con `CARGO_MANIFEST_DIR`,
que queda escrito dentro del binario al compilar: hoy,
`/Users/juancamilo/proyectos/remi`. Si el repo cambia de lugar, la app deja de encontrar
`config/ventanita.json` (el micrófono y whisper) y hay que recompilarla. Es una app para una
persona y un Mac, así que está bien; conviene saberlo antes de mover carpetas.

El núcleo escribe en `~/Library/Logs/Remi/nucleo.log`. Ahí se ve si Remi pudo pensar
(`[claude] modelo=…`) y si la voz quedó lista (`[tts] cargando…`).

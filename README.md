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

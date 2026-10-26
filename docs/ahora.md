# Ahora — 26 oct 2026

## Qué se hizo
- `git init` en `~/proyectos/remi` (main, sin remoto). Commits: `b08962d` base · `f79bc11` núcleo coding · `7d81e99` pantalla Coding.
- `nucleo/coding.py`: tarea → bóveda (máx 6 lecciones + «Úsalas, no las re-investigues») → spec (sonnet) → builder (opus, propone diff, no escribe) → revisor (sonnet). Todo por `claude -p` (Max); si Max llega al límite, para — sin OpenRouter.
- Lección nueva del revisor entra por `experiencia.crear_leccion` (= `POST /experiencia`). Rutas: `/coding/estado`, `/coding/lecciones`, `/coding/corrida`.
- Panel `apps/panel/src/app/coding/page.tsx` + enlace en `Header.tsx`.
- Pruebas: `nucleo/pruebas/test_coding.py` 6/6. Suite: 1048 ok, 6 fallos previos ajenos (oficios, Notion, Ollama).
- Claude Code pasó a nativo 2.1.310 en `~/.local/bin`; `.zshrc` la pone primero (respaldo `~/.zshrc.bak-2026-10-26`).

## Pendiente de Milo
- Probar `/coding` con el núcleo y el panel prendidos, con una tarea pequeña real.
- Decidir si se borran las copias viejas de claude en `/opt/homebrew` y `/usr/local`.

## Pendiente de Claude
- Corrida completa real (builder + revisor) sin probar todavía.
- La bóveda tiene 0 lecciones: el ahorro empieza cuando se llenen.
- El FTS de experiencia no se reindexa solo (`noche.py` solo hace vectores); coding.py lo cubre con búsqueda por palabras.
- Los 6 fallos previos de la suite.

## Siguiente paso
Prender núcleo (4400) y panel (4402) y correr en `/coding` una tarea chica de Remi.

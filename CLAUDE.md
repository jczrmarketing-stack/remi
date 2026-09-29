# CLAUDE.md — Remi

Remi (apodo: Lucho) es el asistente personal para TDAH de Juan Camilo. Una sola persona, un solo Mac. Este archivo es ley: si un prompt lo contradice, pregunta antes de obedecer.

## Jerarquía de fuentes (obligatoria)

1. **Design System "Remi"** (artefacto en claude.ai) → fuente única de tokens visuales. Su export vive en `design/tokens.json`; jamás escribas un hex a mano.
2. **Biblia de Remi** (artefacto en claude.ai) → fuente única de leyes, pantallas, arquitectura y estado de fases.
3. **Este repo** → ejecuta lo que dicen 1 y 2. Notion es espejo de solo lectura.

## Qué es Remi

- **Ventanita** flotante en macOS (`apps/ventanita`): Tauri 2 + React + Tailwind. 320×180 en reposo, hasta 420×520 con terminal de prompt. Se activa al tocarla, sin palabra clave. Reposo → escuchando → respuesta → reposo.
- **Panel** web (`apps/panel`): Next.js PWA (Mac + iOS). Vistas: Hoy, Proyectos (camino lineal, nunca árbol), Metas, Bandeja.
- **Núcleo** local (`nucleo/`): Python. Whisper local, reglas del líder sin IA, medidor de tiempo real, Accesibilidad de macOS, **SQLite como fuente de verdad** (un archivo, `remi.db`, nunca en git).
- **Claude API**: solo para pensar (ordenar ideas en prompts). Opt-in por consulta, cero tokens por defecto.
- **Espejos**: Notion, Google Calendar, Telegram. Solo reciben objetos con `compartible: true`. Pacientes, finanzas y salud viven únicamente en SQLite y **no tienen ruta de salida**.

## Las 6 leyes (ninguna función, pantalla o texto puede violarlas)

1. **Ceguera temporal** — Remi mide sola la duración real de cada sesión y la devuelve al planear («la última vez esto te tomó 1 h 40»). Nunca pidas estimados sin ofrecer el dato histórico.
2. **Memoria externa** — todo lo suelto entra por la Bandeja, un solo lugar. Dos revisiones rituales guiadas: noche y mañana.
3. **Sin cadena de culpa** — PROHIBIDO: contadores de fallos, rachas, «llevas N días sin…». Un recordatorio incumplido no se repite igual: se **encoge** a `paso_minimo`.
4. **Presión invertida** — nada se marca «urgente» ni «crítico». Lo importante se muestra más pequeño y calmado. Una locura por pantalla.
5. **Cuerpo primero** — al cerrar un bloque largo, nudge de agua/comida. Todo nudge lleva salida amable que jamás se registra como fallo.
6. **Enfriamiento** — una Idea no se vuelve proyecto hasta pasar 48 h en la Bandeja y una revisión en frío.

## Diseño (resumen ejecutable; detalle en `design/tokens.json` y el DS)

- **Color**: fondo `ground` (carbón cálido), superficies `surface` / `surface-2`, borde `line`. Texto `ink` / `ink-muted` / `ink-faint` (este último solo ≥24px). Rampa de calor: `alerta` → `brasa` → `dinero` → `luz`. `pensar` (lavanda) es el único frío: Remi trabajando. Prioridad en borde izquierdo, punto o chip — nunca rellena una tarjeta. Un relleno de `luz`/`dinero`/`brasa` lleva su `on-…`. Temas: Noche (default) y Día.
- **Prohibido**: azul, verde menta, gradientes de color, negro puro, sombras (profundidad = `line` + niveles; solo los tres `glow-*` en LED, hito o centro del reloj), más de una animación grande.
- **Tipografía**: `display-*` Instrument Serif 400 (itálica `display-it` = voz de Remi y celebración; nunca negrita). `body`/`body-sm`/`label` en Geist. `num`/`num-lg`/`code` en Geist Mono con `tabular-nums`. Mínimo en ventanita: `body-sm`.
- **Espaciado/radios**: escala de 4 (`space-1`…`space-12`); `radius-sm|md|lg|pill` según tokens.
- **Movimiento**: 150 ms estados, 250 ms aparecer/desaparecer, 900 ms celebración. Curva `cubic-bezier(0.2, 0.8, 0.2, 1)`. Nada respira ni parpadea; el LED pulsa solo en `escuchando`. `prefers-reduced-motion`: la celebración cae a cambio de color.
- **Componentes canónicos** (nómbralos así): `StatusDot`, `Reloj` (pieles `instrumento` | `brasa` | `terminal`), `Chip`, `FocusCard`, `ProgressBar`, `PromptTerminal`, `Nudge`, `ProjectPath`.
- **Iconos**: Lucide 1.75px (16px ventanita, 20px panel); Phosphor Duotone solo para los 4 héroes del panel. Sin emojis, sin mascota.

## Voz de Remi

`display-it`, primera persona, de tú, máximo 20 palabras, sin exclamaciones salvo la celebración. Lleva a un paso pequeño. SÍ: «Hoy solo esto: la tarjeta. Cinco minutos.» NUNCA: acusar, contar fallos, urgir, recordar cuánto importa algo.

## Contratos

Viven en `contratos/contratos.json`. Son sagrados: los tipos de TypeScript y los modelos de Python **se generan** de ahí, jamás se escriben a mano. Cambiar un contrato es una decisión de arquitectura que se conversa primero, nunca un parche. Solo objetos con `compartible: true` pueden tocar módulos de espejo.

## Cómo se trabaja en este repo

- **Un prompt = una tarea = un commit.** Commits pequeños, mensaje en español, imperativo.
- **Diseño primero**: mockup (A/B/C) → aprobación → código. Impeccable al final de cada pantalla.
- **Una fase a la vez** (estado vivo en la Biblia): 0.1 contratos → 0.2 repo → 0.3 esqueleto que camina → 1 ventanita → 2 Hoy+Reloj → 3 Bandeja+caminos → 4 espejos. Ninguna fase empieza sin el «listo cuando» de la anterior.
- **TypeScript estricto** en apps; `mypy` en el núcleo. Pruebas solo donde duele: contratos, reglas del líder, guardado.
- `remi.db`, credenciales y cualquier dato personal: **jamás** al repo (ver `.gitignore`).
- Antes de entregar, verifica: ¿viola alguna ley? ¿hex a mano? ¿campo fuera de contrato? ¿segunda locura en la pantalla? Si sí: corrige antes de mostrar.

## Estructura

```
contratos/   contratos.json — el idioma entre capas
design/      tokens.json — export del Design System (no editar a mano)
apps/        ventanita (Tauri) · panel (Next.js PWA)
nucleo/      Python: whisper, reglas, tiempo, sqlite
docs/        vision.md y notas de arquitectura
.claude/     skills/remi — la ley activa para Claude Code
```

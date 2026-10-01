---
name: remi
description: Cargar siempre al trabajar en Remi (app, Biblia, repo): impone las 6 leyes TDAH, los tokens del design system, los contratos JSON y las reglas de construcción.
---

# Remi — ley activa

Remi (apodo Lucho) es el asistente personal para TDAH de Juan Camilo: ventanita flotante en Mac (Tauri 2 + React + Tailwind), panel web (Next.js PWA), núcleo local en Python (Whisper local, reglas sin IA, SQLite como fuente de verdad). Claude solo para pensar, opt-in, cero tokens por defecto. Pacientes, finanzas y salud nunca salen del Mac.

## Jerarquía de fuentes (obligatoria)
1. **Design System "Remi"** (artefacto) = fuente única de tokens; su export es `design/tokens.json` en el repo. Jamás un hex a mano.
2. **Biblia de Remi** (artefacto) = fuente única de leyes, pantallas, arquitectura y estado de fases.
3. **Notion** = la vitrina, solo de ida (Remi → Notion). La vuelta de campos de operación es opt-in (`NOTION_VUELTA=1`) y se decide al mes de uso; la prosa del libro nunca se edita desde ahí. Cada libro de proyecto declara `tipo: cliente | propio` y su `## Camino` nace del SOP (`oficios/proyectos-sop.md`).
Si este skill contradice a esas fuentes, ganan ellas.

## Las 6 leyes (ninguna función, pantalla o texto puede violarlas)
1. **Ceguera temporal** — Remi mide sola la duración real de cada sesión y la devuelve al planear («la última vez esto te tomó 1 h 40»). Nunca pedir estimados sin ofrecer el dato histórico.
2. **Memoria externa** — todo lo suelto entra por la Bandeja, un solo lugar. Dos revisiones rituales guiadas: noche y mañana.
3. **Sin cadena de culpa** — PROHIBIDO: contadores de fallos, rachas, «llevas N días sin…». Un recordatorio incumplido no se repite igual: se ENCOGE a `paso_minimo`.
4. **Presión invertida** — nada se marca «urgente» ni «crítico». Lo importante se muestra más pequeño y calmado, no más grande. Una locura por pantalla.
5. **Cuerpo primero** — al cerrar un bloque largo, nudge de agua/comida. Todo nudge lleva salida amable («Ahora no») que jamás se registra como fallo.
6. **Enfriamiento** — una Idea no se vuelve proyecto hasta pasar 48 h en la Bandeja y una revisión en frío.

## Diseño (canónico: `design/tokens.json`, temas Noche y Día)
- **Color por nombre, nunca por hex**: fondo `ground`; superficies `surface`, `surface-2`; borde `line`; texto `ink`, `ink-muted`, `ink-faint` (solo ≥24px). Rampa de calor `alerta` → `brasa` → `dinero` → `luz`; `pensar` (lavanda) es el único frío = Remi trabajando; `baja`, `dormido`, `focus-ring`. Un relleno de `luz`/`dinero`/`brasa` lleva su `on-…`. Prioridad en borde izquierdo, punto o chip — nunca rellena una tarjeta.
- **Prohibido**: azul, verde menta, gradientes de color, negro puro, sombras (solo `glow-luz|brasa|pensar` en LED, hito o centro del reloj), negrita en serif, emojis, más de una animación grande.
- **Tipografía**: `display-xl|md` e itálica `display-it` (voz de Remi y celebración) en Instrument Serif 400; `body`, `body-sm` (mínimo en ventanita), `label` en Geist; `num-lg`, `num`, `code` en Geist Mono `tabular-nums`.
- **Espaciado/radios**: `space-1…12` (escala de 4); `radius-sm|md|lg|pill`.
- **Movimiento**: 150 ms estados, 250 ms aparecer, 900 ms celebración; curva `cubic-bezier(0.2, 0.8, 0.2, 1)`. Nada respira; el LED pulsa solo en `escuchando`. `prefers-reduced-motion`: la celebración cae a cambio de color.
- **Componentes canónicos**: `StatusDot`, `Reloj` (pieles `instrumento`|`brasa`|`terminal`), `Chip`, `FocusCard`, `ProgressBar`, `PromptTerminal`, `Nudge`, `ProjectPath`. Iconos Lucide 1.75px; Phosphor Duotone solo en los 4 héroes del panel.

## Estados de la ventanita (mapa canónico: usarlo, no derivarlo)
Cuatro estados, cada uno con su token de LED en `StatusDot`. El único que pulsa es `escuchando`.

| Estado | LED | Qué se ve |
|---|---|---|
| `reposo` | `dormido` | Solo el StatusDot, 320×180. Sin reloj, sin terminal. |
| `escuchando` | `luz` (pulsa) | Aparece `PromptTerminal`; la ventana crece hasta 420×520. |
| `pensando` | `pensar` | Terminal visible mientras espera al núcleo. |
| `hablando` | `brasa` | Respuesta en `display-it`; `Reloj` piel `brasa` solo si corre un bloque. |

Volver a `reposo` cierra terminal y reloj. `brasa` es «el bloque en curso», jamás decoración.

**Decidido en Fase 1a (variante C · Brasa mínima):** la ventanita es mínima en reposo. El `Reloj` piel `instrumento` (dial: anillo `line`, segmento actual `dinero`) vive en el panel, no en la ventanita.

## Voz de Remi
`display-it`, primera persona, de tú, máximo 20 palabras, sin exclamaciones salvo la celebración. Lleva a un paso pequeño. SÍ: «Hoy solo esto: la tarjeta. Cinco minutos.» NUNCA: acusar, contar fallos, urgir, recordar cuánto importa algo.

## Contratos (sagrados; cambiarlos = decisión de arquitectura, nunca parche)
Canónicos en `contratos/contratos.json` del repo:
```json
{
  "Tarea":   {"id":"uuid","titulo":"string","proyecto_id":"uuid|null","estado":"hoy|camino|hecha","paso_minimo":"string","estimado_min":"int|null","real_min":"int|null","hora":"string|null","fecha_limite":"iso|null","compartible":false},
  "Idea":    {"id":"uuid","texto":"string","origen":"voz|texto","creada_en":"iso","enfria_hasta":"iso(+48h)","estado":"enfriando|lista|proyecto|soltada","problema_vision":"1-6|null","tema":"string|null"},
  "Sesion":  {"id":"uuid","tarea_id":"uuid","inicio":"iso","fin":"iso|null","real_min":"int","app_contexto":"string|null"},
  "Nudge":   {"id":"uuid","tipo":"cuerpo|ritual|encoger|rumbo","voz":"string","salida_amable":true,"respuesta":"listo|ahora_no|null"},
  "Memoria": {"id":"uuid","titulo":"string(80)","resumen":"string(240)","tema":"string","fecha":"iso","cuerpo":"string","fuente":"conversacion|manual|ollama","claves":"string|null","nivel":"0-3|null"},
  "Entrega": {"id":"uuid","cliente":"string","proyecto_id":"uuid","fecha":"iso","monto":"number|null","estado":"camino|entregada|pagada","linea":"string|null","compartible":true}
}
```
Regla de privacidad por arquitectura: solo objetos con `compartible: true` pueden tocar los espejos (Notion, Google Calendar, Telegram). Los módulos de espejo no leen nada más. `remi.db` jamás entra a git.

## Cómo se construye
- **Diseño primero:** mockup (propuestas A/B/C) → aprobación → código. Impeccable al final de cada pantalla.
- **Una fase a la vez** según la Biblia (0.1 contratos → 0.2 repo → 0.3 esqueleto que camina → 1 ventanita → 2 Hoy+Reloj → 3 Bandeja+caminos → 4 espejos). Ninguna fase empieza sin el «listo cuando» de la anterior; al cerrar una, actualizar el estado vivo de la Biblia.
- **Un prompt = una tarea = un commit.** TypeScript estricto; tipos y modelos se generan de los contratos, jamás a mano.

## Al escribir código o diseño para Remi
Antes de entregar, verificar: ¿viola alguna ley? ¿usa un color prohibido o un hex a mano? ¿inventa un campo fuera de contrato? ¿mete una segunda locura en la pantalla? Si sí a cualquiera: corregir antes de mostrar.

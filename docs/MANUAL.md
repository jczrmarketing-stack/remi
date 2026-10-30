# Remi · Manual de uso (30-oct-2026)

Versión para el repo y Obsidian del documento «Remi · Plan y manual de uso». El plan vive en `docs/PLAN-FINAL.md`; aquí está solo el manual.

## Qué es Remi hoy

| Parte | Qué hace | Estado |
|---|---|---|
| Remi (núcleo, ventanita, panel, bot) | Contexto vivo inyectado en Claude Code y Claude escritorio por MCP y hooks | Funciona. Foco y notificaciones: F3b |
| Bóveda (`/Volumes/ORGANIC/boveda`) | Cualquier link por Telegram → transcribe o ve, titula, resume, clasifica, detecta «comenta X» | Funciona. Visión lista, falta `OPENROUTER_API_KEY`. Hallazgos automáticos: F1.6 |
| Rumbo (`/rumbo`) | Una decisión concreta, de a una pregunta, termina en experimento | Texto. Sin pantalla: F2 |
| La mente (`~/proyectos/mente`) | La única memoria: `yo/ negocio/ mundo/ aprendido/ bandeja/` + índice | Funciona. Notas de la bóveda se unifican en F1.4 |

## Telegram (`@lucho777_bot`)

| Quieres | Haces | Pasa |
|---|---|---|
| Guardar un video, blog o repo | Compartes el link solo | Entra a los 45 s; llega resumen al terminar |
| Muchos a la vez | Un mensaje con todos los links, uno por línea (~40 máx.) | Un lote; otro mensaje queda en cola |
| De a poco | `/info` … links … `/listo` (o `/enviar`) | Se juntan y arrancan con `/listo` |
| Cómo va | `/estado` | Van / faltan / fallaron |
| Cancelar | `/cancelar` | Cierra sin procesar |
| Hablarle | Texto normal | Responde con el estado vivo y la mente |

No lee: X, LinkedIn, posts privados de Instagram. Archivos (PDF, DOCX): F1.4. Fallidos en `00_inbox/_fallidos.txt`; reintento: `python3 lote.py --inbox`.

## Bóveda (`cd /Volumes/ORGANIC/boveda`)

Con cada link: metadatos y caption → transcripción en cascada (subtítulos, API, Whisper; sin voz → visión por OpenRouter gratis, un pedido por video) → puntaje y carpeta → enriquecido en segundo plano (título, resumen con citas, frentes, cifras, interés del autor, pedido). GitHub → ficha de repo.

| Para | Comando |
|---|---|
| Reintentar fallidos | `python3 lote.py --inbox` |
| Qué videos esconden la herramienta y qué comentar | `python3 pedidos.py` |
| Modelos gratis con visión hoy | `python3 vision.py --modelos` |
| Probar visión con un reel | `python3 vision.py <url>` |
| Medir un tema en el mercado | `python3 campo.py --tema "ai receptionist"` |
| Fichar un repo | `python3 repos.py <url>` |
| Tablero | `dashboards/dashboard.md` |

Límite: OpenRouter gratis ≈ 50 pedidos/día (1.000 si la cuenta compró 10 USD alguna vez).

## Claude Code y Claude escritorio

MCP `remi`: `estado_vivo`, `preguntar(q)` (fichas), `leer(id)` (cuerpo), `anotar(texto, tipo)`, `supuestos`. Hooks: al abrir sesión entra el estado vivo y los mapas; en cada mensaje, lo que la bóveda sabe del tema.

`/rumbo <decisión en una frase>`: lee la mente, reformula (incluye «no hacer nada»), pregunta de a una (máx. 5), separa evidencia de hipótesis, termina en ficha con experimento; se guarda en `mente/aprendido/decisiones/`.

Reglas en `CLAUDE.md`: `docs/MAPA.md` antes de grep; `preguntar` antes de la web; nunca arrastrar PDFs (convertir a Markdown); cinco líneas a la mente al cerrar.

Claude escritorio: agregar el MCP `remi` (bloque `mcpServers` del README) y reiniciar.

## Obsidian y la mente (`~/proyectos/mente`)

| Carpeta | Qué hay | Quién escribe |
|---|---|---|
| `yo/` | Perfil, metas, recursos, valores, restricciones | Tú; Claude con confirmación |
| `negocio/` | Frentes, CRM, ofertas, cifras propias | Remi (noche), Claude |
| `mundo/fuentes/` `repos/` `campo/` | Videos y blogs, fichas de repos, mediciones | Bóveda y sensores |
| `mundo/hallazgos/` | Cruces por frente | A mano hoy; la noche desde F1.6 |
| `mundo/fabrica/` | Material de Software Factory | Tú |
| `aprendido/lecciones/` `decisiones/` `procedimientos/` `supuestos.md` | Lecciones, fichas de Rumbo, listas de revisión, supuestos | Claude Code, Rumbo, hallazgos, Remi |
| `bandeja/` | Lo suelto | Telegram, hooks |
| `MAPA.md` | Una línea por nota | `scripts/mapa.py` |

Regla: lo que dices no pisa un hecho verificado; se marca el choque. Lo que Claude concluye es hipótesis o decisión con fecha, nunca hecho.

## Servicios (`launchd`, puertos 4400 núcleo · 4402 panel · 4401 whisper)

`com.remi.nucleo`, `.ventanita`, `.panel`, `.whisper`, `.noche`, `.copia` (3:00), `.vigia` (doctor cada mañana), `com.boveda.campo` (semanal). Reiniciar uno: `launchctl kickstart -k gui/$(id -u)/<nombre>`. Scripts: `./scripts/doctor.sh` (11 chequeos), `./scripts/recargar.sh`, `./scripts/instalar.sh`. Logs: `~/Library/Logs/Remi/`.

## Rutinas

- **Mañana (5 min):** lee el estado; elige una tarea y ponle tiempo (BeFocus hasta F3b; después el parte de las 7:00 con «Empezar 25 min»).
- **Día (0 min):** todo lo que veas, al bot. No clasifiques.
- **Noche (automática):** bandeja, estado, índice, CRM, mapas, `uso.md`. Si quieres, dos líneas por Telegram. Nunca cuenta fallos.
- **Domingo (15 min):** `python3 pedidos.py`, comenta lo que valga, pásame los repos; lee `mundo/hallazgos/`.
- **Cada decisión grande:** `/rumbo`.

## Cuando algo falla

| Síntoma | Arreglo |
|---|---|
| Bot no contesta | `launchctl kickstart -k gui/$(id -u)/com.remi.nucleo`; 40 s; luego `./scripts/doctor.sh` |
| Links sin efecto | Solo links, uno por línea, o `/info` … `/listo` |
| «whisper no devolvió texto» | Pasa a visión solo; si falla, falta `OPENROUTER_API_KEY` en `_sistema/.env` |
| «empty media response» | Post privado; descartar |
| «There is no video in this post» | Carrusel: `pip install gallery-dl` en el entorno de la bóveda |
| Claude Code sin contexto | `python3 scripts/instalar_hook_claude.py --aplicar`; `claude mcp list` debe mostrar `remi`; reabrir sesión |
| Título «Video by …» | `python3 enriquecer.py` en la bóveda |
| `git` con `.lock` | `mv .git/index.lock .git/stale-index-lock` |
| ORGANIC desmontado | Conectarlo; en F1.4 deja de importar |

## Lo que todavía no existe

Hallazgos automáticos y teoría de juegos (F1.6, F2) · pantalla de Rumbo (F2; Sala en F5) · ventanita de foco y notificaciones (F3b) · archivos por Telegram (F1.4) · medición del ahorro (`uso.md`, F1.3) · copia fuera del Mac (F1.7) · fábrica (F4) · repo privado y token rotado (F3).

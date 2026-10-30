# Plan final · terminar Remi (30-oct-2026)

Estado vivo. Una fase a la vez; ninguna empieza sin el «listo cuando» de la anterior. El plan del 4-oct está en `docs/archivo/`. Diseños de referencia: `docs/diseno/boveda-v2-mente.md`, `docs/diseno/filtro-de-la-verdad.md`, `docs/revision/2026-10-30-sintesis.md`, `docs/prompts/no-inventar-la-rueda.md`.

## Qué es «terminado»
1. Cualquier Claude (Code, escritorio, Telegram) arranca sabiendo quién es Juan Camilo, su negocio, sus metas, recursos y restricciones, sin que se lo cuente, y le devuelve a la mente lo que aprende.
2. La bóveda es una sola mente (`mente/`), con Obsidian como ventana y un índice regenerable; ahorra tokens de forma medida.
3. Rumbo responde `/rumbo` con una ficha honesta que termina en un experimento dimensionado, y aprende de lo que pasa.
4. Todo corre solo en el Mac (servicios, noche, copias, campo) siete días sin tocarlo, y se puede restaurar.
5. La fábrica produce una cotización real y una entrega real con revisión y portero.
6. Nada de esto viola las 6 leyes ni mete datos personales en git.

## Decisiones tomadas el 30-oct (cambian si Juan Camilo lo dice)
- `mente/` vive en el disco interno (`~/proyectos/mente`, git privado, restic); en ORGANIC solo audio y caché.
- Claude escribe directo en `aprendido/`; lo que diga de él (`yo/`) espera su «sí» por Telegram; lo del mundo exige URL o entra como hipótesis.
- Obsidian con tablas vivas (Dataview o Bases).
- Rumbo v2 según la revisión: contador de tiros, experimentos con potencia mínima, diario de micro-predicciones, tasas base propias, sensibilidad simple; sin ranking de 60 nichos ni Kelly ni futuros a 12 meses. El espacio de configuraciones (yo fijo × modelo, nicho, geografía, canal, precio) se construye, pero solo con datos T1/T2.
- La fábrica arranca por cotizar y proponer, no por código.
- Nada entra como hecho sin fuente; lo que Claude concluye es hipótesis o decisión con fecha.

## Reglas
Un prompt = una tarea = un commit. Pruebas donde duele. `conocimiento/` y `mente/` nunca al repo público. Diseño antes que pantalla. Cada fase cierra con un «listo cuando» verificado por Juan Camilo o por Claude en la app, no por la terminal que lo hizo.

## Quién hace qué
- **Terminal (Claude Code en el Mac):** el código, las pruebas, las migraciones, las mediciones locales.
- **Claude en la app (esta conversación):** diseño, revisión de lo que entrega la terminal, prompts de cada paso, verificación cruzada.
- **Juan Camilo:** decisiones, comandos que tocan `~/.claude` y launchd, pruebas desde el teléfono, exportar su historial de Fiverr, el token de Telegram, el repo privado.

---

## F0 · Cerrar lo abierto (hoy, ~1 h)
- [ ] `/etiquetar` probado desde el teléfono (él, 1 min).
- [ ] Hook de prompt instalado: `python3 ~/proyectos/remi/scripts/instalar_hook_claude.py --aplicar` (él).
- [ ] MCP `remi` en Claude Desktop (él, pegar el JSON del README).
- [ ] Servicio semanal de campo cargado (él, comando del README de la bóveda).
- [ ] `python3 campo.py --tema "ai receptionist"` corre con RemoteOK, Remotive y HN respondiendo (él pega la salida).
**Listo cuando:** Telegram responde a `/etiquetar`; una pregunta en Claude Code trae contexto de la bóveda; el campo deja una nota con al menos dos fuentes.

## F1 · La mente (terminal, ~3,5 días) — detalle en `docs/diseno/boveda-v2-mente.md` §7
1. **Estructura y mudanza (M).** Crear `~/proyectos/mente/{yo,negocio,mundo,aprendido,bandeja}`; mover `conocimiento/vida` y `experiencia`; sembrar `yo/` (perfil, metas, recursos, valores y reglas, restricciones) desde `estado.md` y sus frases, con fecha por línea; `vida.py`, hooks y MCP apuntan a `mente/`; vault de Obsidian con `.obsidian`, propiedades uniformes y plantillas. *Listo cuando:* `estado_vivo` sale de `yo/` + `negocio/`; Obsidian abre `mente/`.
2. **Un índice (M).** `indexar.py` (FTS5 + sqlite-vec, por hash) sobre `mente/`; `preguntar` devuelve resumen + fecha + estatus + confianza; `leer(id)`; `vectores.py` migrado; las 6 pruebas rotas pasan. *Listo cuando:* una consulta cruza lección, campo, decisión y fuente.
3. **Salida con compuerta (L).** `anotar` con tipos; confirmación por Telegram para `yo/`; regla de cierre de sesión en `CLAUDE.md` + hook; la noche consolida bandeja, actualiza `estado.md`, re-indexa y escribe `uso.md` con las 5 métricas. *Listo cuando:* una sesión de Claude Code deja una investigación con fuentes en `mundo/investigaciones/` y la siguiente sesión la usa sin buscar en la web.
4. **Ingesta unificada (L).** La bóveda pasa a `nucleo/ingesta/` con un solo entorno; notas de videos a `mundo/fuentes/` con `estatus`; `campo.py` y `repos.py` como sensores; archivar ejemplos; apagar `boveda/memoria/`, `inteligencia/memoria.py`, `contexto.yaml`, el MCP `memoria` (absorbido por `remi`). *Listo cuando:* compartir un reel por Telegram termina en una nota enriquecida en `mente/mundo/fuentes/` y `preguntar` la encuentra.
5. **Ventana viva (S).** Dataview/Bases: repos por veredicto, fuentes por estatus, supuestos vencidos, decisiones por frente. `/estado`, `/repos`, `/campo <tema>` por Telegram sin modelo. *Listo cuando:* las tablas se llenan solas.

## F2 · Rumbo v2 (terminal, ~2 días) — detalle en `docs/revision/2026-10-30-sintesis.md`
1. **Cifras propias (S).** Él exporta Fiverr (y Upwork/Malik si se puede); la terminal calcula mediana, p90, $/día, concentración, tiempos entre órdenes → `mente/negocio/cifras-propias.md`. *Listo cuando:* `estado_vivo` cita su propia distribución, no «$500 al mes».
2. **Contador de tiros y diario (M).** Una línea por contacto (canal, fecha, respuesta, cotización, pago) por Telegram; micro-predicción diaria con probabilidad y vencimiento; resultado al vencer; Brier a las 30. *Listo cuando:* 7 días de registro sin fricción.
3. **Experimentos (M).** Hipótesis, métrica, umbral de éxito, umbral de abandono, plazo, tope de horas; n ≥ 3/tasa esperada; aviso al vencer; resultado como evidencia T1. *Listo cuando:* un experimento real cerrado y registrado.
4. **`/rumbo` (L).** Marco (unidades propias y techo de capacidad), espacio de configuraciones con clases de referencia T1/T2, sensibilidad simple (qué parámetro cambia al líder), ficha de una tarjeta que termina en experimento; por Telegram y ventanita. *Listo cuando:* `/rumbo ¿qué nicho?` devuelve una ficha con lo que más pesa que no sabe y un experimento dimensionado.

## F3 · Producción (terminal + él, ~2 días)
- Repo privado antes de cualquier push; token de Telegram rotado; llaves solo en Ajustes.
- Los 10 servicios cargados y el vigía como proceso aparte; logs rotados; restic con restauración de prueba hecha y documentada.
- Medición de tokens por sesión (`uso.md`) y semana de uso real con bitácora de fallos.
**Listo cuando:** 7 días sin intervención manual; una restauración probada; `git log -p` sin un solo secreto.

## F4 · La fábrica (terminal, ~3 días) — según el video y `nucleo/coding.py`
1. **Cotizar y proponer (L).** Entrada por Telegram (brief del cliente) → spec que consulta `mente/` → propuesta con precio ancla y contrato Omniway → revisor con contexto limpio → portero (reglas, no agente) → PDF listo para enviar. *Listo cuando:* una cotización real sale en menos de 30 min de su tiempo.
2. **Entregar software (L).** Spec → builder con TDD → revisores (seguridad, UX, código) → aprobador → portero con hooks → PR; trazas en SQLite. *Listo cuando:* una entrega real pasa por la fábrica y se cobra.

## F5 · Después (no antes)
La Sala (mapa vectorial) cuando `mente/` tenga datos de campo y decisiones; el investigador semanal que llena `mundo/`; marketing y ventas; la vara contra Grok Bot medida como oportunidades por semana que el sistema encontró y él no.

## Registro
- 30-oct: plan reescrito tras la revisión externa y el diagnóstico de la bóveda. F0 abierta.

## Cómo se arranca cada paso en la terminal
«Lee `docs/PLAN-FINAL.md` y el diseño que cita. Haz solo el paso F<n>.<m>. Antes de tocar código, di en 5 líneas qué vas a cambiar y qué prueba lo demuestra. Un commit por tarea. Al final: qué quedó, qué no, cómo lo verifico desde mi teléfono o desde Obsidian, y qué anotaste con `anotar_leccion`.»

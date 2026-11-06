# Plan: fábrica, línea y Gerente de cuenta (4-nov-2026)

Copia para la terminal del documento «Plan: fábrica, línea y Gerente de cuenta» (claude.ai). Diseño completo: «SOP de la Fábrica de Software — INV3RZA».

## Reglas del plan
1. La Fase 1 de UpVisuals va primero. Esta semana solo lo que no arriesga la entrega ni el cobro.
2. Un bloque a la vez: el siguiente no empieza hasta cumplir el «listo cuando» del anterior.
3. Cada bloque se prueba con un caso real, no con una demo.
4. Adoptar antes que construir: Superpowers como motor de la fábrica; skills de ventas existentes.
5. Nada sale sin el sí de Juan Camilo (mensajes, facturas, propuestas, PRs).
6. Medir el consumo de Max desde el día uno.
7. Antes de construir algo que Juan Camilo va a ver, mostrarle un ejemplo y esperar su aprobación.

## Bloque 0 · La base (4–9 nov)
Juan Camilo: instalar CLAUDE.md global, /revisar y /cerrar-fase; `brew install gitleaks semgrep osv-scanner`; instalar Superpowers; revisar en Settings → Usage de qué bolsa sale `claude -p`; decidir si se une la rama del verificador.
Terminal: ajustar la línea base del verificador con la corrida del Mac; unir `fabrica/verificador` (hecho el 6-nov, en main); el verificador corre en el hook `pre-push` local y el CI de GitHub queda apagado a propósito para no gastar (se reactiva con `gh workflow enable verificar`); registro de consumo por agente de cada `claude -p` en SQLite.
Listo cuando: el verificador corre solo en cada push, en el Mac, y se sabe de qué bolsa sale el uso automático.

## Bloque 1 · Fábrica v1 (10–16 nov)
Expediente `fabrica/pedidos/<id>/expediente.md` con secciones por agente. Planificador (spec de 5 líneas con escenarios «cuando… entonces…», máx. 3 preguntas) → Tester (tests que fallan antes de construir) → Constructor (worktree aparte, método Superpowers) → verificador (si falla vuelve al Constructor, máx. 2 vueltas) → Revisor (`/revisar` en sesión nueva, solo spec + diff) → Portero (hooks: nada en main, sin push --force, sin borrar, sin desplegar) → aviso en el mensaje de las 11 o al bot de alertas. Base: `nucleo/coding.py`.
Prueba real: los 6 tests rotos de agentes (Clasificador y Editor) y el test inestable de `test_estado_propio`.
Listo cuando: 3 pedidos reales terminan en PR que pasa verificador y /revisar, y Juan Camilo aprueba al menos uno sin cambios. Se mide: % de PRs aprobados sin cambios y tokens por PR.
Mejoras del 6-nov (investigación «mejor software factory», bóveda: Risco 4hzSdtikHNs y p6nnqerea7w, indydevdan haUfb1ievTE, Cole Medin eecUhBpTz_g; informe en `.workflow/scratch/investigacion-software-factory-2026-11-06.md`). Lección central: pasar los tests no basta; 4.500 tests en verde dieron un Frankenstein.
1. Compuertas tipadas: cada estación deja su sección del expediente como JSON validado (`--json-schema`) y una función en código decide si pasa. Un control que no corrió queda visible, nunca se da por bueno.
2. La spec dice «cómo se demuestra»: qué podrá hacer el usuario, condiciones de partida, resultado esperado y qué evidencia queda. El Tester escribe además 2–3 escenarios ocultos que el Constructor no lee; el verificador los corre al final.
3. `fabrica/REGLAS.md` + `fabrica/mission.md` con alcance y fuera de alcance. El Planificador puede responder «no puedo / fuera de alcance / partir en dos» en vez de inventar.
4. Cola con estados en SQLite (la misma base que `consumo.py`): pedido → spec → construyendo → revisar → listo/parado. Disparo de noche por launchd, un pedido a la vez.
5. Revisor con otro modelo cuando el cambio toque auth, dinero o migraciones; el resto, mismo modelo en sesión limpia. Los hallazgos se contrastan con el código real y se ordenan por gravedad antes de volver al Constructor.

Estado (6-nov): TERMINADO. Unido a `main` el 6-nov; PR #4 aprobado sin cambios por Juan Camilo. Construido en `fabrica/bloque-1` con las 5 mejoras (a5bdce4, 7ecea94, 228def6, 256e5b5, fdda36c). Tres pedidos reales en PR en borrador: #2 (test_notion_sync), #3 (cuatro tests de oficios) y #4 (Telegram no bajaba documentos: `descargar_archivo` vivía en el Protocol; 366.044 tokens, 0 vueltas, 1 oculto que pasa). La noche (`com.remi.fabrica`, 2:30) quedó instalada el 6-nov.

## Bloque 2 · Gerente de cuenta y Administrador (17–23 nov)
Expediente del cliente en `mente/negocio/clientes/<cliente>.md` (etapa, alcance, cobros, documentos, últimos mensajes).
Gerente de cuenta: entrada por Evolution API (solo conversaciones existentes, número aparte; correo y Fiverr pegados a mano en Telegram); redacta con el filtro (reconozco, hecho, propuesta); fuera de alcance → propone cotizar; borrador a la cola por Telegram; nunca envía; avance de los viernes.
Administrador: cobros del expediente; factura lista en Malik Gestión y mensaje de cobro en borrador; atraso de más de 5 días → propone pausa; marca pagado solo lo que Juan Camilo confirma (Zelle no avisa).
Antes de construir: 3 borradores de ejemplo con mensajes reales de Alfonso, aprobados.
Listo cuando: una semana de mensajes reales con borrador a tiempo, enviados con cambios mínimos.

## Bloque 3 · Pantalla de la línea (24–30 nov)
Núcleo: `GET /linea`, `GET /linea/<cliente>`, `POST /linea/aprobar` (aprobar copia y abre WhatsApp; no envía). Panel: `/linea` y `/linea/[cliente]` con el estilo de la Suite. Estado en vivo de cada agente.
Antes de construir: Juan Camilo aprueba el diseño del lienzo «INV3RZA Suite · Línea de clientes».
Sin CRM externo todavía: Twenty entra con más de 3 clientes activos.
Listo cuando: UpVisuals aparece donde está de verdad y se aprueba un borrador real desde la pantalla.

## Después
Crecimiento → Reactivador → Cronista, Guionista y Adaptador → Cotizador y Cerrador → revisores especializados → célula fría.

## Decisiones pendientes de Juan Camilo
- Unir y subir la rama del verificador (frena Bloque 0).
- Constructor que escribe en worktree en vez de solo proponer diff (frena Bloque 1).
- Qué segundo modelo revisa auth, dinero y migraciones: Sonnet por Max, o Codex/API (frena la mejora 5 del Bloque 1).
- Número de WhatsApp para Evolution API (frena Bloque 2).
- Aprobar el diseño de la línea (frena Bloque 3).

# SOP de la fábrica: de un proyecto a producción

Todo proyecto que entra a la fábrica pasa por estas puertas, en orden. Cada puerta se cierra con **evidencia** (un archivo, un test en verde, un informe) y con el **sí de Juan Camilo**. Nada se salta y nada avanza sin la anterior.

| # | Puerta | Sale | Quién la cierra |
|---|---|---|---|
| 0 | **Diagnóstico**: heredar o construir | `docs/DIAGNOSTICO.md` en el repo del proyecto | Agente lee; Juan Camilo aprueba |
| 1 | **Biblia corta** | `docs/BIBLIA.md`: problema, qué NO es, stack, fases con «listo cuando» | Juan Camilo aprueba |
| 2 | **Diseño** | Mockups A/B/C de las pantallas de la fase | Juan Camilo aprueba |
| 3 | **Esqueleto** | Arquitectura, contratos, verificador y CI corriendo | Verificador en verde |
| 4 | **Pedidos** | Un PR en borrador por tarea (`python3 -m fabrica pedir`) | Verificador + Revisor; Juan Camilo fusiona |
| 5 | **Seguridad base** | Secretos fuera del repo, escáneres en verde, accesos con MFA | Checklist del oficio «producción» |
| 6 | **Producción** | Respaldo previo, despliegue, prueba de 5 minutos | Juan Camilo despliega |
| 7 | **Entrega** | Documento, video, accesos a nombre del cliente, garantía | Cliente recibe; se cobra |

## Puerta 0 · Diagnóstico: heredar o construir

INV3RZA hace ingeniería inversa: se parte de lo que el producto necesita, no del stack que nos gusta. Esta puerta se corre **siempre**, también en proyectos propios.

**1. Qué necesita el producto.** Una línea por capacidad, sin nombrar tecnología: trabajos largos en segundo plano, archivos pesados, OAuth con terceros, tiempo real, pagos, IA, multi-cliente.

**2. Qué hay hoy.** Inventario de lo existente: repos, servicios, base de datos, infraestructura y **de quién es** (nuestra o del cliente), apps de OAuth ya aprobadas, dominios.

**3. Qué sobra.** Servicios que duplican trabajo, piezas que se pueden quitar. Quitar es la primera mejora.

**4. Cuánto cuesta cambiar.** Reescritura, migración de datos, nuevas verificaciones con terceros (OAuth, auditorías) y riesgo sobre lo que está por cobrarse.

**5. Decisión**, con esta regla:
- **Proyecto nuevo** → stack INV3RZA: Next.js + TypeScript + Tailwind + Supabase + Vercel. Python solo puertas adentro.
- **Proyecto heredado** → **se queda con su stack**. Se estandarizan los bordes sin reescribir: TypeScript estricto, contrato de la API con tipos generados, verificador, monitoreo de errores, runbook. Y se quita lo que sobra.
- **Migrar** solo si el cliente gana algo que puede pagar, y entonces es una **fase cotizada aparte**, nunca dentro de una entrega en curso.

**6. Paquete de oficio.** El diagnóstico elige el paquete de instrucciones que reciben los agentes de la línea según el stack (por ejemplo «Node + Express + Prisma» o «Next.js + Supabase»). Los agentes siguen siendo los 4 roles de la línea; lo que cambia es lo que saben del stack.

**`docs/DIAGNOSTICO.md` (una página):** capacidades · inventario · lo que sobra · costo de cambiar · decisión y por qué · paquete de oficio · riesgos. La firma Juan Camilo antes de la Puerta 1.

### Ejemplo: UpVisuals (Alfonso), 4-nov-2026
- Necesita: publicar en 6 redes con OAuth, subir videos y programar con reintentos (trabajos largos), archivos pesados, créditos con Stripe, IA.
- Hay: panel Next.js en Vercel (ya es nuestro stack); backend Node + Express + Prisma + MySQL en EC2, RDS y S3 del cliente; un servicio Flask para la IA.
- Sobra: probablemente el Flask, si solo llama a la IA (verificarlo).
- Cambiar costaría: reescribir el backend, migrar MySQL, volver a verificar OAuth y TikTok, y arriesgar la entrega de la Fase 1.
- Decisión: **heredar**. La Fase 2 se construye dentro del backend actual. Supabase o Postgres se reevalúan solo para la Fase 3 (multi-cliente).

## Puerta 4 · Cuatro pasos de la línea tomados de Archon (9-nov-2026)

Origen: lectura de los flujos `split`, `triage`, `deliver` y `review` del pack SDLC de Archon (MIT; bóveda, `mundo/investigaciones/2026-11-09-*`). No se migra: Archon no trae escenarios ocultos, «cómo se demuestra» ni Portero, que son lo que mejor funciona aquí. Se toman cuatro ideas. Cada paso dice entradas, regla, qué sale y quién aprueba. **Estado: método aprobado el 9-nov; ninguno construido todavía.**

**A. Partir un PRD en pedidos.**
- Entra: una fase de la Biblia o un PRD/épica.
- Regla: un pedido = una cosa, con su propio «listo cuando»; máximo 12 por tanda; solo se parte la fase actual y las siguientes quedan anotadas con la señal que las activa; no se duplica un pedido ya abierto.
- Sale: lista de pedidos para `encolar`.
- Aprueba: Juan Camilo aprueba la lista antes de encolar nada.
- Ejemplo: la Fase 2 de UpVisuals sale como 6 a 10 pedidos, no como uno gigante.

**B. Triage con rutas.**
- Entra: un pedido nuevo.
- Regla: el Planificador elige una ruta: `investigar` (solo lectura, devuelve un informe y ningún código), `planificar`, `entregar`, `partir` o `fuera_de_alcance`. Hoy ya existen las dos últimas; falta `investigar`.
- Sale: la ruta en el expediente, con una línea de por qué.
- Aprueba: Juan Camilo, siempre que la ruta no sea `entregar`.

**C. Revisión con lentes y votación de bloqueantes.**
- Entra: spec y diff.
- Regla: el Revisor mira por lentes según el riesgo (código, tests, errores, contratos); riesgo alto sigue pidiendo otro modelo. Cada hallazgo **alto** lo juzgan 3 verificadores aparte, en contexto limpio, con la evidencia del código; con 2 votos en contra baja a `nota` (defecto previo) o `refutado` (no es real).
- Sale: la sección Revisión del expediente con los hallazgos que sobreviven y los degradados con su razón.
- Aprueba: Juan Camilo lee el PR, como hoy.
- Ejemplo: pendiente, el primer pedido real que lo use. (El falso «alto» del 8-nov en el pedido `-14` no se habría salvado con votos: el diff sí borraba lo que decía; se curó fijando la base, `base_sha`.)
- Costo: 3 llamadas pequeñas solo cuando hay hallazgos altos.

**D. Revisor de solo lectura impuesto.** Ya está cumplido: el Revisor y el Planificador corren con `--tools Read,Grep,Glob` (`comando()` en `nucleo/fabrica/agentes.py`), así que el CLI les niega escribir; no depende del prompt. Los verificadores de C heredan lo mismo. Falta un test que fije el conjunto de herramientas del Revisor (hoy solo se prueba el del Planificador).

**Qué se mide** al construir A a C: % de PRs aprobados sin cambios, tokens por PR y cuántos hallazgos altos terminan degradados.

## Estado
La Puerta 0 hoy se corre en una sesión de Claude Code con esta guía. Cuando la fábrica soporte otros repos, pasa a ser una orden propia (agente de solo lectura más tu aprobación). La lista de puertas sigue el SOP de proyectos de la bóveda (`oficios/proyectos-sop.md`) y el plan de la fábrica (`docs/fabrica/PLAN.md`).

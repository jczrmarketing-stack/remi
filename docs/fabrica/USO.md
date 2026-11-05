# Cómo se usa la fábrica (una página)

## Sesión o fábrica
- **Sesión de Claude Code** (el chat, o una sesión lanzada desde él): trabajo artesanal. Conversas y decides sobre la marcha. Para lo nuevo, el diseño o lo que pide decisiones.
- **Fábrica** (`nucleo/fabrica/`): línea de montaje. Das un pedido de una frase y los agentes se pasan el trabajo solos, con `claude -p` (gasta Max). Para lo acotado y con test claro: tests rotos, bugs, funciones pequeñas.

## La línea
1. **Planificador**: spec corta con escenarios «cuando… entonces…» y máximo 3 preguntas.
2. **Tú apruebas la spec.** Es el único momento en que tienes que pensar.
3. **Tester**: escribe tests que fallan.
4. **Constructor**: programa en un worktree aparte hasta que pasan.
5. **Verificador**: si falla, vuelve al Constructor (máximo 2 vueltas).
6. **Revisor**: revisa solo la spec y el diff, en limpio.
7. **Portero**: impide tocar `main`, hacer `push --force`, borrar o desplegar.
8. Sale un **PR en borrador** y te llega el aviso al bot de alertas. Nada se fusiona sin ti.

## Los 4 comandos
Desde `nucleo/`, con el venv del núcleo (`.venv/bin/python`):

```bash
python3 -m fabrica pedir "arreglar el test inestable de test_estado_propio"
python3 -m fabrica responder <id> "tu respuesta"   # si el Planificador preguntó
python3 -m fabrica aprobar <id>                     # aprueba la spec y corre hasta el PR
python3 -m fabrica ver [<id>]                       # lista los pedidos o muestra uno
```

`pedir` acepta `--base <rama>` si no se parte de `main`. Si algo para a medias, `aprobar` retoma donde quedó.

## Un buen pedido
- **Una cosa.** «Arreglar los 6 tests rotos del Clasificador», no «mejorar los agentes».
- **Dónde.** El archivo o el test, si lo sabes.
- **Listo cuando.** Qué tiene que pasar para darlo por hecho: «pasa `test_x`», «el panel muestra Y».

## Usarla bien
1. **Lo acotado a la fábrica, lo nuevo a una sesión.**
2. **La spec es donde se gana o se pierde.** Léela con calma: si la spec está mal, sale un PR perfecto de lo equivocado.
3. **Mide el gasto.** Una spec cuesta hoy unos 90.000 a 100.000 tokens de Max; el total de cada pedido sale en su PR. Lo que se mide: % de PRs aprobados sin cambios y tokens por PR.

## Estado
Bloque 1, en la rama `fabrica/bloque-1`. Se une a `main` cuando 3 pedidos reales terminen en un PR que pase el verificador y la revisión, y Juan Camilo apruebe al menos uno sin cambios. Plan completo: `docs/fabrica/PLAN.md`.

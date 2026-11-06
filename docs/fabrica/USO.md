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

## Dónde vive
La fábrica corre desde su casa, `~/proyectos/remi/.worktrees/fabrica` (rama `fabrica/casa`, igual a `main`). El checkout principal puede estar en otra rama sin afectarla. Para ponerla al día:
```bash
git -C ~/proyectos/remi/.worktrees/fabrica pull --ff-only origin main
```

## Los 4 comandos
Desde `~/proyectos/remi/.worktrees/fabrica/nucleo`, con el venv del núcleo (`~/proyectos/remi/nucleo/.venv/bin/python`):

```bash
python3 -m fabrica pedir "arreglar el test inestable de test_estado_propio"
python3 -m fabrica responder <id> "tu respuesta"   # si el Planificador preguntó
python3 -m fabrica aprobar <id>                     # aprueba la spec y corre hasta el PR
python3 -m fabrica ver [<id>]                       # lista los pedidos o muestra uno
```

`pedir` acepta `--base <rama>` si no se parte de `main`. Si algo para a medias, `aprobar` retoma donde quedó.

## De noche (sin gastar tu día)
```bash
python3 -m fabrica encolar "arreglar el test de X"    # la noche corre el Planificador
python3 -m fabrica aprobar <id> --de-noche            # apruebas la spec; la noche la lleva al PR
python3 -m fabrica cola                               # qué hay y en qué estado
```
La noche (`python3 -m fabrica noche`, launchd a las 2:30 con `scripts/launchd/com.remi.fabrica.plist`) toma **un** pedido por corrida: primero lo aprobado, después planear lo encolado. Lo que no marcaste para la noche no lo toca.

## Qué garantiza cada PR (mejoras del 6-nov)
- **Reglas y misión** (`fabrica/REGLAS.md`, `fabrica/mission.md`): el Planificador puede decir `fuera_de_alcance` o `partir` en vez de inventar.
- **Cómo se demuestra**: toda spec dice qué evidencia prueba que está hecho.
- **Escenarios ocultos**: el Tester escribe tests aparte que el Constructor nunca ve; si fallan, solo recibe sus nombres.
- **Controles**: el PR lista cada control y su resultado; el que no corrió lo dice.
- **Revisión contrastada**: un hallazgo que cita código que no existe se descarta; con riesgo alto revisa un modelo distinto al que construyó.

## Un buen pedido
- **Una cosa.** «Arreglar los 6 tests rotos del Clasificador», no «mejorar los agentes».
- **Dónde.** El archivo o el test, si lo sabes.
- **Listo cuando.** Qué tiene que pasar para darlo por hecho: «pasa `test_x`», «el panel muestra Y».

## Usarla bien
1. **Lo acotado a la fábrica, lo nuevo a una sesión.**
2. **La spec es donde se gana o se pierde.** Léela con calma: si la spec está mal, sale un PR perfecto de lo equivocado.
3. **Mide el gasto.** Una spec cuesta hoy unos 90.000 a 100.000 tokens de Max; el total de cada pedido sale en su PR. Lo que se mide: % de PRs aprobados sin cambios y tokens por PR.

## Proyectos enteros
Un proyecto completo (nuevo o heredado de un cliente) sigue las puertas del SOP: `docs/fabrica/SOP.md`. Siempre empieza por la Puerta 0, el diagnóstico de heredar o construir. La fábrica entra en la Puerta 4, con los pedidos.

## Estado
Bloque 1 terminado el 6-nov: unido a `main` con las mejoras, y el PR #4 aprobado sin cambios. Quedan en borrador #2 y #3. Se une a `main` cuando 3 pedidos reales terminen en un PR que pase el verificador y la revisión, y Juan Camilo apruebe al menos uno sin cambios. Plan completo: `docs/fabrica/PLAN.md`.

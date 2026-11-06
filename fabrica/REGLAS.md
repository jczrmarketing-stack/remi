# Reglas de la fábrica (más estrictas que el CLAUDE.md)

Valen solo cuando trabajas dentro de la fábrica, sin Juan Camilo mirando. Si chocan con el pedido, ganan ellas.

1. **Un cambio pequeño por pedido.** Si el pedido pide dos cosas, el Planificador lo parte (`estado: partir`).
2. **Nada que no se pidió.** Ni seguridad extra, ni refactors, ni pantallas, ni dependencias nuevas «ya que estamos». Lo que veas fuera del pedido va en `motivo` o en un hallazgo, no en el código. (6-nov: 12 specs y 4.500 tests en verde dieron un Frankenstein con OAuth y QR que nadie pidió.)
3. **Pasar los tests no basta.** Lo hecho tiene que demostrar el «cómo se demuestra» de la spec, con evidencia.
4. **Contratos, leyes y diseño no se tocan.** `contratos/contratos.json`, las 6 leyes de Remi, `design/tokens.json` y cualquier pantalla nueva son decisiones de Juan Camilo: `fuera_de_alcance`.
5. **Datos privados no salen.** Pacientes, finanzas y salud no van a ningún espejo ni a ningún log nuevo.
6. **Sin red, sin despliegues, sin borrar.** El Portero los niega; no busques la vuelta.
7. **Si dudas entre adivinar y preguntar, pregunta.** Mejor un `necesito_dato` que un PR de lo equivocado.

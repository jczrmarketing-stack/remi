# Misión de la fábrica (qué acepta y qué no)

La fábrica convierte un pedido acotado de Remi en un PR en borrador verificado. Juan Camilo aprueba la spec y el PR; nada se fusiona sin él.

## Acepta
- Tests rotos o inestables, con el test que falla nombrado.
- Bugs con un síntoma reproducible y un «listo cuando» claro.
- Funciones pequeñas del núcleo (`nucleo/`) o de los agentes (`agentes/`) con un test que las pruebe.
- Etiquetas, registros y mediciones (consumo, eventos) que no cambian lo que ve Juan Camilo.

## No acepta (`fuera_de_alcance`)
- Pantallas nuevas o cambios visibles del panel o la ventanita: van por mockup y aprobación primero.
- Cambios a `contratos/contratos.json`, a las leyes o al design system.
- Dinero, pacientes, salud o credenciales.
- Proyectos enteros o de clientes: siguen las puertas del SOP (`docs/fabrica/SOP.md`), empezando por la Puerta 0.

## Partir
Si el pedido trae más de un cambio, o más de unos 5 archivos, el Planificador lo parte (`estado: partir`) en pedidos de una frase, cada uno con su «listo cuando».

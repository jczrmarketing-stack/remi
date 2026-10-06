#!/usr/bin/env node
// Un núcleo falso, en JS puro, solo para Playwright: mismas rutas y forma
// de respuesta que servidor.py, con datos fijos. Playwright.config.ts lo
// levanta como webServer aparte; nunca toca el núcleo real ni su base.
import { createServer } from "node:http";

const PUERTO = Number(process.env.PUERTO_NUCLEO_FALSO || 4498);

const TAREA_ID = "11111111-1111-1111-1111-111111111111";
const SESION_ID = "22222222-2222-2222-2222-222222222222";
const IDEA_FRIA_ID = "33333333-3333-3333-3333-333333333333";
const IDEA_TIBIA_ID = "44444444-4444-4444-4444-444444444444";
const NUDGE_ID = "55555555-5555-5555-5555-555555555555";

const AHORA = Date.now();
const iso = (msDelta) => new Date(AHORA + msDelta).toISOString();
// Fechas de día completo: 00:00 UTC del día LOCAL (+n días). Así «hoy» es hoy
// aunque ya sea de noche en América y UTC haya pasado a mañana.
const dia = (n) => {
  const d = new Date(AHORA);
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate() + n)).toISOString();
};

let nudgeRespuesta = null;
let ideaFriaEstado = "enfriando";
// Solo para las pruebas: POST /__escenario deja el núcleo falso como recién
// arrancado (el nudge sin contestar, la idea fría en la Bandeja, los hitos
// sin tocar), y con { bloque: false } deja Hoy sin nada abierto; POST
// /bloque lo vuelve a abrir — igual que el núcleo real.
let hayBloque = true;
// El tema del bloque abierto: «upvisuals» de entrada; POST /bloque lo cambia.
let temaDelBloque = "upvisuals";

const tareaSuelta = (id, titulo, hora) => ({
  tarea: { id, titulo, proyecto_id: null, estado: "hoy", paso_minimo: "Cinco minutos.", estimado_min: null, real_min: null, hora, fecha_limite: null, compartible: false },
  sesiones: [],
  ultima_vez_min: null,
});

// Lo anotado para hoy sin bloque abierto: ya viene ordenado por hora.
const DEMAS_HOY = [
  tareaSuelta("66666666-6666-6666-6666-666666666666", "Enviar factura a Alfonso", "15:00"),
  tareaSuelta("77777777-7777-7777-7777-777777777777", "Revisar Bandeja", "16:30"),
];

const AGENDA = {
  manana: [
    { id: "88888888-8888-8888-8888-888888888888", titulo: "Llamada con el banco", proyecto_id: null, estado: "camino", paso_minimo: "Cinco minutos.", estimado_min: null, real_min: null, hora: null, fecha_limite: dia(1), compartible: false },
  ],
  vence: [
    { titulo: "Factura Omniway", fecha: dia(0), monto: null, origen: "tarea", vence_hoy: true },
    { titulo: "Entrega Alfonso", fecha: dia(3), monto: 1000, origen: "entrega", vence_hoy: false },
    { titulo: "Formulario IRS", fecha: dia(20), monto: null, origen: "tarea", vence_hoy: false },
  ],
};

let tituloDelBloque = "Terminar el flujo de distribución";
const bloqueAbierto = () => ({
  tarea: { id: TAREA_ID, titulo: tituloDelBloque, proyecto_id: null, estado: "hoy", paso_minimo: "Cinco minutos.", estimado_min: null, real_min: null, hora: null, fecha_limite: null, compartible: false },
  sesiones: [{ id: SESION_ID, tarea_id: TAREA_ID, inicio: iso(-10 * 60000), fin: null, real_min: 0, app_contexto: temaDelBloque }],
  ultima_vez_min: 80,
});

// Los caminos: cada hito con la línea del SOP que lo explica (`detalle`).
// `cerrados`: { indice: {tipo, ref, en} } — forma K (B3.4), un hito que se
// cerró solo, no a mano.
const hitosDe = (pasos, hechos, cerrados = {}) =>
  pasos.map(([texto, detalle], i) => ({ texto, hecho: i < hechos, detalle, cerrado_por: cerrados[i] ?? null }));

const PASOS_UPVISUALS = [
  ["Contrato firmado", "Corto, amable, y que protege a Omniway."],
  ["Anticipo recibido", ""],
  ["Distribución", "El flujo de distribución corre con datos reales."],
  ["Seguridad crítica", "Accesos y llaves revisados antes de entregar."],
];
const PASOS_CLIENTE = [
  ["Intake", "Qué pide, qué necesita de verdad, plata en juego, urgencia y riesgo."],
  ["Descubrimiento (5 preguntas)", "Máximo cinco preguntas, las que cambian la propuesta."],
  ["Propuesta por fases", "Cada fase con alcance, monto y «listo cuando»."],
  ["Contrato", "Corto, amable, y que protege a Omniway."],
  ["Pago antes de arrancar", "En cuotas, con tolerancia de días. El trabajo empieza cuando el pago está completo."],
  ["Entregas medidas", "Cada fase se cierra con una demo y el «listo cuando» cumplido."],
  ["Cobro y cierre", "Factura, comprobante, libro actualizado y la siguiente fase propuesta."],
  ["Producción", "La lista del oficio «producción» completa antes de entregar."],
  ["Entrega y capacitación", "Demo, cuentas a nombre del cliente y runbook."],
  ["Mensualidad", "Se propone en la entrega. Es el objetivo del ciclo."],
];
const PASOS_PROPIO = [
  ["Bandeja 48 h", "La idea enfría 48 h. Sin excepción."],
  ["Revisión en frío", "Loco + útil + estratégico. Si falta uno, se suelta sin culpa."],
  ["Biblia corta", "Una página: problema, para quién, qué no es, stack y fases."],
  ["Mockups A/B/C", "Diseño primero: mockups, aprobación, código."],
  ["Encargos a Claude Code", "De una tarea, por la puerta de Remi."],
  ["Actualizar libro y camino", "Cada fase cerrada actualiza el libro y sus hitos."],
  ["Prioridad por plata", "Lo que trae plata pronto va primero."],
];

// Lo único que cambia entre pruebas: cuántos hitos de UpVisuals están hechos
// (POST /libros/upvisuals/camino/:n lo mueve; /__escenario lo devuelve a 2,
// o a 2 con el hito 0 cerrado solo si manda `{ cerradoSolo: true }` — forma
// K, B3.4, para probar la tarjeta «lo cerré por…» y su deshacer).
let hitosUpvisuals = hitosDe(PASOS_UPVISUALS, 2);

// B6 (tablero 5, la ficha de cliente): los gastos de upvisuals, mutables
// (PATCH /gastos/:id los corrige a mano).
let gastosUpvisuals = [{ id: "gasto-servidor-1", concepto: "servidor", monto: 40 }];

// B4 (forma J): qué responde GET /hoy/aldia. `null` es el de siempre;
// "borrador" trae un mensaje para copiar; "cierre" trae un hito recién
// cerrado solo, para probar la celebración (revisión de B4).
let alDiaEscenario = null;

// La idea destacada de la semana: una sola (POST /idea/:id/destacar la cambia).
const DESTACADA_DE_ENTRADA = "99999999-9999-9999-9999-999999999992";
let destacadaId = DESTACADA_DE_ENTRADA;

// Lo que Remi pregunta (forma F): a UpVisuals le falta el «listo cuando» de la
// Fase 2 y la carpeta del código; a Malik, saber si es de un cliente o propio.
// Contestar escribe el dato (acá, en memoria; en el núcleo real, en el libro).
const preguntasDeEntrada = () => [
  { id: "aaaaaaaa-0000-0000-0000-000000000001", tema: "upvisuals", campo: "fase.2.listo_cuando", voz: "¿Cuándo está lista la Fase 2 de Upvisuals?", estado: "pendiente", creada_en: iso(-3600000), disponible_desde: iso(-3600000) },
  { id: "aaaaaaaa-0000-0000-0000-000000000002", tema: "upvisuals", campo: "ruta", voz: "¿En qué carpeta está el código de Upvisuals?", estado: "pendiente", creada_en: iso(-3600000), disponible_desde: iso(-3600000) },
  { id: "aaaaaaaa-0000-0000-0000-000000000003", tema: "malik", campo: "tipo", voz: "¿Malik es de un cliente o es tuyo?", estado: "pendiente", creada_en: iso(-3600000), disponible_desde: iso(-3600000) },
];
let preguntas = preguntasDeEntrada();
let listoCuandoFase2 = "";
let tipoDeMalik = null;

// GET /semana: lo cerrado y lo aplazado desde el lunes.
const SEMANA = {
  desde: iso(-3 * 86400000),
  cerrado: [
    { titulo: "Contrato de UpVisuals", tema: "upvisuals", real_min: 95 },
    { titulo: "Biblia corta de Omniway", tema: "omniway", real_min: 40 },
  ],
  aplazado: [
    { titulo: "Formulario IRS", tema: "omniway" },
    { titulo: "Llamada con el banco", tema: null },
  ],
};

const PLATA = {
  semana: { cobrado: 500, meta_semanal: 554.27 },
  mes: {
    cobrado: 500,
    meta: 2400,
    faltan: 1900,
    entregas: [
      { cliente: "Beto", fecha: iso(-5 * 86400000), monto: 400 },
      { cliente: "Canal de Malik", fecha: iso(-2 * 86400000), monto: 100 },
    ],
  },
  proximo: { cliente: "Alfonso", fecha: dia(3), monto: 1000 },
  // 500 de 2.400 = 21 %: la segunda meta todavía duerme (despierta al 50 %).
  metas: [
    { nombre: "Vivir solo", horizonte_meses: 12, monto_mes: 2400, activa: true, activa_desde_pct: null },
    { nombre: "Carro", horizonte_meses: 18, monto_mes: 1100, activa: false, activa_desde_pct: 50 },
  ],
  revision_fria: { dia: "viernes", hora: "16:30", minutos: 10 },
  // Software: 400 en 2 h = 200 por hora. Malik: 100 en 2 h = 50 por hora.
  por_linea: [
    { id: "software", nombre: "Software (clientes)", cobrado_mes: 400, minutos_mes: 120 },
    { id: "malik", nombre: "Malik (contenido)", cobrado_mes: 100, minutos_mes: 120 },
  ],
};

// Lo que el núcleo deriva del camino: el hito encendido, hasta tres que
// siguen y qué hace Remi en ese paso.
function conCamino(libro, hitos, pasoRemi) {
  const i = hitos.findIndex((h) => !h.hecho);
  return {
    ...libro,
    hitos,
    hito_actual: i >= 0 ? hitos[i] : null,
    siguientes: i >= 0 ? hitos.slice(i + 1, i + 4) : [],
    paso_remi: i >= 0 ? pasoRemi : "",
  };
}

const libros = () => [
  conCamino(
    {
      tema: "upvisuals",
      titulo: "Upvisuals",
      resumen: "Distribución de contenido para el artista.",
      compartible: true,
      quedaste: "armando el contrato.",
      proximo_paso: "mandar la propuesta.",
      entrega_cercana: { cliente: "Alfonso", fecha: dia(3), monto: 1000 },
      ultimo_estado_en: iso(-1 * 3600000),
      tipo: "cliente",
      cliente: "Alfonso",
      // 1.500 cobrados del proyecto: en cascada, todo cae en la Fase 1.
      fases: [
        { nombre: "Fase 1", alcance: "Distribución de contenido + seguridad crítica", monto: 5000, listo_cuando: "La demo de distribución corre con datos reales.", estado: "pagando", cobrado: 1500 },
        { nombre: "Fase 2", alcance: "Generador de imágenes", monto: 3700, listo_cuando: listoCuandoFase2, estado: "propuesta", cobrado: 0 },
        { nombre: "Fase 3", alcance: "Multi-cliente para agencias", monto: null, listo_cuando: "", estado: "sin alcance", cobrado: 0 },
      ],
      fase_actual_n: 1,
    },
    hitosUpvisuals,
    "Escribe los encargos y lleva el camino.",
  ),
  // Un libro de cliente que todavía no tiene fases: el camino del SOP entero.
  conCamino(
    {
      tema: "beam",
      titulo: "BeaM — vender compartiendo la pantalla",
      resumen: "Ventas compartiendo la pantalla.",
      compartible: false,
      quedaste: "",
      proximo_paso: "",
      entrega_cercana: null,
      ultimo_estado_en: iso(-24 * 3600000),
      tipo: "cliente",
      cliente: "Beto",
      fases: [],
      fase_actual_n: null,
    },
    hitosDe(PASOS_CLIENTE, 3),
    "Escribe el borrador en la voz de Juan Camilo.",
  ),
  // Sin tipo y sin camino: un libro recién sembrado.
  {
    tema: "malik",
    titulo: "Malik",
    resumen: "Las cuentas de X y Reddit.",
    compartible: false,
    quedaste: "",
    proximo_paso: "",
    hitos: [],
    entrega_cercana: null,
    ultimo_estado_en: iso(-48 * 3600000),
    tipo: tipoDeMalik,
    cliente: null,
    fases: [],
    fase_actual_n: null,
    hito_actual: null,
    siguientes: [],
    paso_remi: "",
  },
  // Propio: camino del SOP propio, sin fases ni plata.
  conCamino(
    {
      tema: "omniway",
      titulo: "Omniway",
      resumen: "La empresa.",
      compartible: false,
      quedaste: "",
      proximo_paso: "",
      entrega_cercana: null,
      ultimo_estado_en: iso(-200 * 3600000),
      tipo: "propio",
      cliente: null,
      fases: [],
      fase_actual_n: null,
    },
    hitosDe(PASOS_PROPIO, 2),
    "Ayuda a armar la Biblia corta de una página.",
  ),
];

function bandeja() {
  // Igual que bandeja.listar_abiertas: solo estado enfriando|lista queda
  // en la lista — soltada y proyecto salen.
  // A propósito fuera de orden: el panel pone la destacada arriba, después
  // la que ya se puede decidir y después lo que enfría, lo que sale antes primero.
  const todas = [
    { idea: { id: "99999999-9999-9999-9999-999999999991", texto: "Curso de After Effects", origen: "texto", creada_en: iso(-2 * 3600000), enfria_hasta: iso(46 * 3600000), estado: "enfriando", problema_vision: null, tema: "aprender" }, fria: false },
    { idea: { id: IDEA_FRIA_ID, texto: "Automatizar las facturas", origen: "texto", creada_en: iso(-50 * 3600000), enfria_hasta: iso(-2 * 3600000), estado: ideaFriaEstado, problema_vision: null, tema: "omniway" }, fria: ideaFriaEstado === "enfriando" },
    { idea: { id: IDEA_TIBIA_ID, texto: "App de recetas con IA", origen: "texto", creada_en: iso(-10 * 3600000), enfria_hasta: iso(38 * 3600000), estado: "enfriando", problema_vision: null, tema: null }, fria: false },
    { idea: { id: "99999999-9999-9999-9999-999999999992", texto: "Router de leads que agenda solo", origen: "voz", creada_en: iso(-20 * 3600000), enfria_hasta: iso(28 * 3600000), estado: "enfriando", problema_vision: null, tema: "organic-cash" }, fria: false },
  ];
  return todas
    .filter((f) => f.idea.estado === "enfriando" || f.idea.estado === "lista")
    .map((f) => ({ ...f, destacada: f.idea.id === destacadaId }));
}

function nudge() {
  if (nudgeRespuesta) return null;
  return { id: NUDGE_ID, tipo: "ritual", voz: "Hay 1 idea fría. ¿La miramos 2 minutos?", salida_amable: true, respuesta: null };
}

function enviarJSON(res, estado, cuerpo) {
  res.writeHead(estado, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(cuerpo === undefined ? "" : JSON.stringify(cuerpo));
}

// B1: el tope de gasto en Ajustes → Conexiones. En memoria, como el resto
// del núcleo falso.
let configGasto = { tope_dia_usd: 5.0, tope_mes_usd: 50.0, activo: true };
const vistaGasto = () => ({ ...configGasto, gastado_dia_usd: 0, gastado_mes_usd: 0 });

// R1-R5: Rumbo. Datos fijos que cubren los cinco estados de la escalera,
// los cuatro tipos y los tres orígenes de la partida, una apuesta activa y
// una cerrada, y dos caminos (uno listo con fuentes, uno investigando).
// `metaConfirmada` es lo único que /__escenario resetea (empieza sin meta:
// así se prueba que «Contar mi visión» no la cambia sola).
const ESCALERA = [
  { n: 1, texto: "Primeros clientes", criterio: "2 mensualidades seguidas", estado: "conquistado" },
  { n: 2, texto: "Vivir solo", criterio: "$2.400/mes, 6 meses seguidos", estado: "ahora" },
  { n: 3, texto: "Un mes de margen", criterio: "3 meses de gasto fijo guardados", estado: "sigue" },
  { n: 4, texto: "Dos líneas estables", criterio: "ningún cliente > 40 %", estado: "luego" },
  { n: 5, texto: "Patrimonio", criterio: "$1.000.000 guardado y trabajando", estado: "norte" },
];
const PARTIDA = [
  { tipo: "recurso", texto: "Horas reales por semana", valor: "22 h", origen: "medido", dominio: null },
  { tipo: "recurso", texto: "Meses de gasto fijo guardados", valor: "2", origen: "medido", dominio: null },
  { tipo: "habilidad", texto: "Software para clientes", valor: "6 proyectos entregados", origen: "medido", dominio: "cirujano" },
  { tipo: "habilidad", texto: "Contenido (Malik)", valor: "2 cuentas creciendo", origen: "medido", dominio: "sabe" },
  { tipo: "habilidad", texto: "Vender por llamada", valor: "sin evidencia todavía", origen: "pregunta", dominio: "aprendiz" },
  { tipo: "cuesta", texto: "Seguimiento de propuestas", valor: "le cuesta sostenerlo", origen: "dicho", dominio: null },
  { tipo: "preferencia", texto: "Prefiere mensualidad a pago único", valor: "", origen: "dicho", dominio: null },
];
let metaConfirmada = null;
let visionTexto = null;
const CUENTA = {
  meta_mes: 2400,
  ticket: 1000,
  necesarias: 3,
  tienes: 1,
  cierre: { p: 0.25, base_n: 8, origen: "propia" },
  propuestas_semana: 2,
  hechas_semana: 1,
  horas_semana: [
    { camino: "Clientes de software", pct: 60 },
    { camino: "Malik (contenido)", pct: 30 },
    { camino: "Sin planear", pct: 10 },
  ],
};
const APUESTAS = [
  {
    id: "apuesta-1",
    camino: "Mensualidad de mantenimiento",
    inicio: dia(-7),
    fin: dia(7),
    tope_horas: 20,
    tope_plata: 0,
    gastado_horas: 9,
    gastado_plata: 0,
    senal_sigue: true,
    senal_pausa: false,
    progreso: { hecho: 1, meta: 2 },
    resultado: null,
  },
  {
    id: "apuesta-2",
    camino: "Curso corto de edición",
    inicio: dia(-30),
    fin: dia(-16),
    tope_horas: 10,
    tope_plata: 50,
    gastado_horas: 10,
    gastado_plata: 48,
    senal_sigue: false,
    senal_pausa: true,
    progreso: { hecho: 0, meta: 1 },
    resultado: "pausa",
  },
];
const CAMINOS = {
  "camino-1": {
    estado: "listo",
    mercado: "Negocios chicos que ya tienen web y necesitan mantenimiento mensual.",
    competidores: "Freelancers sueltos, sin contrato de mensualidad.",
    juego: "El cliente prueba un mes; si responde rápido, se queda.",
    a_favor: "Ya tiene 6 proyectos entregados en software para clientes.",
    en_contra: "Depende de conseguir el primer cliente de mantenimiento.",
    dominio: "cirujano",
    base: { texto: "De cada 10 freelancers que ofrecen mantenimiento, 3 lo sostienen un año.", fuente_id: "f1" },
    palancas: "Ofrecer el primer mes a mitad de precio.",
    objeciones: "El precio de mantenimiento puede parecer alto sin un caso mostrado.",
    prueba: "Ofrecerlo a un cliente actual por un mes.",
    fuentes: [
      { id: "f1", url: "https://example.com/freelance-retention", fecha: dia(-20), fragmento: "3 de 10 freelancers sostienen un contrato mensual más de un año.", verificada: true, tipo: "fuente" },
    ],
  },
  "camino-2": {
    estado: "investigando",
    mercado: null,
    competidores: null,
    juego: null,
    a_favor: null,
    en_contra: null,
    dominio: null,
    base: null,
    palancas: null,
    objeciones: null,
    prueba: null,
    fuentes: [],
  },
};
// R5.2, forma S: si el reloj, los pronósticos o la cuenta no reciben datos
// en 2 días, una pieza del latido lo dice — sin alarma, sin rojo.
const LATIDO = [
  { pieza: "reloj", ultimo_dato: iso(-2 * 3600000), callado_dias: 0 },
  { pieza: "pronosticos", ultimo_dato: dia(-3), callado_dias: 3 },
  { pieza: "cuenta", ultimo_dato: dia(-1), callado_dias: 1 },
];

function leerCuerpo(req) {
  return new Promise((resolve) => {
    let datos = "";
    req.on("data", (d) => (datos += d));
    req.on("end", () => resolve(datos ? JSON.parse(datos) : {}));
  });
}

const servidor = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PUERTO}`);
  const ruta = url.pathname;

  if (req.method === "OPTIONS") return enviarJSON(res, 200);

  if (req.method === "GET" && ruta === "/salud") return enviarJSON(res, 200, { ok: true, db: true });
  if (req.method === "POST" && ruta === "/__escenario") {
    const cuerpo = await leerCuerpo(req);
    hayBloque = cuerpo.bloque !== false;
    temaDelBloque = "upvisuals";
    tituloDelBloque = "Terminar el flujo de distribución";
    nudgeRespuesta = null;
    ideaFriaEstado = "enfriando";
    hitosUpvisuals = hitosDe(
      PASOS_UPVISUALS,
      2,
      cuerpo.cerradoSolo ? { 0: { tipo: "encargo", ref: "s1", en: iso(-60 * 60000) } } : {},
    );
    alDiaEscenario = cuerpo.alDia ?? null;
    gastosUpvisuals = [{ id: "gasto-servidor-1", concepto: "servidor", monto: 40 }];
    destacadaId = DESTACADA_DE_ENTRADA;
    preguntas = preguntasDeEntrada();
    listoCuandoFase2 = "";
    tipoDeMalik = null;
    metaConfirmada = null;
    visionTexto = null;
    return enviarJSON(res, 200, { bloque: hayBloque });
  }
  if (req.method === "GET" && ruta === "/rumbo") {
    return enviarJSON(res, 200, { vision: visionTexto, meta: metaConfirmada, escalera: ESCALERA, partida: PARTIDA });
  }
  if (req.method === "POST" && ruta === "/rumbo/vision") {
    const cuerpo = await leerCuerpo(req);
    visionTexto = String(cuerpo.texto ?? "");
    return enviarJSON(res, 200, {
      propuesta: { monto_min: 2400, monto_max: 3000, meses_seguidos: 6, limites: "ningún cliente más del 40 %" },
      voz: "Entendí: entre $2.400 y $3.000 al mes, seis meses seguidos. ¿Confirmas?",
    });
  }
  if (req.method === "POST" && ruta === "/rumbo/meta") {
    const cuerpo = await leerCuerpo(req);
    if (cuerpo.confirmada === true) {
      metaConfirmada = {
        monto_min: cuerpo.monto_min ?? null,
        monto_max: cuerpo.monto_max ?? null,
        meses_seguidos: cuerpo.meses_seguidos ?? null,
        limites: cuerpo.limites ?? null,
      };
    }
    return enviarJSON(res, 200, metaConfirmada);
  }
  if (req.method === "GET" && ruta === "/rumbo/cuenta") return enviarJSON(res, 200, CUENTA);
  if (req.method === "GET" && ruta === "/rumbo/apuestas") return enviarJSON(res, 200, APUESTAS);
  if (req.method === "GET" && ruta.match(/^\/rumbo\/caminos\/[^/]+$/)) {
    const id = decodeURIComponent(ruta.split("/")[3]);
    const camino = CAMINOS[id];
    if (!camino) return enviarJSON(res, 404, { detail: "no tengo un análisis para ese camino" });
    return enviarJSON(res, 200, camino);
  }
  if (req.method === "GET" && ruta === "/rumbo/latido") return enviarJSON(res, 200, LATIDO);
  if (req.method === "GET" && ruta === "/hoy") return enviarJSON(res, 200, hayBloque ? [bloqueAbierto(), ...DEMAS_HOY] : DEMAS_HOY);
  if (req.method === "GET" && ruta === "/hoy/agenda") return enviarJSON(res, 200, AGENDA);
  if (req.method === "POST" && ruta === "/bloque") {
    const cuerpo = await leerCuerpo(req);
    if (hayBloque) return enviarJSON(res, 409, { detail: "ya hay un bloque abierto" });
    hayBloque = true;
    temaDelBloque = cuerpo.tema ?? null;
    tituloDelBloque = cuerpo.titulo;
    const abierto = bloqueAbierto();
    return enviarJSON(res, 201, { tarea: abierto.tarea, sesion: abierto.sesiones[0] });
  }
  if (req.method === "POST" && ruta.match(/^\/libros\/[^/]+\/camino\/\d+\/deshacer$/)) {
    const [, , temaCrudo, , nCrudo] = ruta.split("/");
    const n = Number(nCrudo);
    if (decodeURIComponent(temaCrudo) !== "upvisuals") return enviarJSON(res, 404, { detail: "no tengo un libro con ese tema" });
    if (n < 1 || n > hitosUpvisuals.length) return enviarJSON(res, 404, { detail: `ese libro tiene ${hitosUpvisuals.length} hito(s)` });
    hitosUpvisuals = hitosUpvisuals.map((h, i) => (i === n - 1 ? { ...h, hecho: false, cerrado_por: null } : h));
    const libro = libros().find((l) => l.tema === "upvisuals");
    return enviarJSON(res, 200, {
      ...libro,
      estado_completo: libro.quedaste ? `Quedaste: ${libro.quedaste}\nDecisiones: cuotas con cinco días de tolerancia.\nPróximo paso: ${libro.proximo_paso}` : "",
      ultimo_episodio: null,
    });
  }
  if (req.method === "GET" && ruta === "/hoy/aldia") {
    if (alDiaEscenario === "borrador") {
      return enviarJSON(res, 200, {
        estamos_en: { tema: "upvisuals", fase_n: 5, paso: "Cobro y cierre" },
        lo_ultimo: { texto: "Cobraste a Alfonso (1500)", hace_min: 5, evidencia: { tipo: "cobro", ref: "c2" } },
        sigue: { texto: "Cobro y cierre", borrador: "Alfonso, te mando la factura de esta fase. Quedamos al día." },
        mientras_no_estabas: [],
      });
    }
    if (alDiaEscenario === "cierre") {
      return enviarJSON(res, 200, {
        estamos_en: { tema: "upvisuals", fase_n: 4, paso: "Seguridad crítica" },
        lo_ultimo: { texto: "Cerraste el paso Distribución con un encargo", hace_min: 1, evidencia: { tipo: "encargo", ref: "s-cierre-1" } },
        sigue: { texto: "Seguridad crítica", borrador: null },
        mientras_no_estabas: [],
      });
    }
    return enviarJSON(res, 200, {
      estamos_en: { tema: "upvisuals", fase_n: 3, paso: "Distribución" },
      lo_ultimo: { texto: "Diste un commit: ajustar el flujo de distribución", hace_min: 12, evidencia: { tipo: "commit", ref: "e1" } },
      sigue: { texto: "Distribución", borrador: null },
      mientras_no_estabas: [
        { texto: "Cobraste a Alfonso (1500)", tema: "upvisuals", hora: iso(-3 * 60 * 60000), evidencia: { tipo: "cobro", ref: "c1" } },
      ],
    });
  }
  if (req.method === "POST" && ruta.match(/^\/libros\/[^/]+\/camino\/\d+$/)) {
    const [, , temaCrudo, , nCrudo] = ruta.split("/");
    const cuerpo = await leerCuerpo(req);
    const n = Number(nCrudo);
    if (decodeURIComponent(temaCrudo) !== "upvisuals") return enviarJSON(res, 404, { detail: "no tengo un libro con ese tema" });
    if (n < 1 || n > hitosUpvisuals.length) return enviarJSON(res, 404, { detail: `ese libro tiene ${hitosUpvisuals.length} hito(s)` });
    hitosUpvisuals = hitosUpvisuals.map((h, i) => (i === n - 1 ? { ...h, hecho: cuerpo.hecho === true } : h));
    return enviarJSON(res, 200, { hitos: hitosUpvisuals, siguiente: hitosUpvisuals.find((h) => !h.hecho) ?? null });
  }
  if (req.method === "GET" && ruta.startsWith("/libros/")) {
    const tema = decodeURIComponent(ruta.split("/")[2] || "");
    const libro = libros().find((l) => l.tema === tema);
    if (!libro) return enviarJSON(res, 404, { detail: "no tengo un libro con ese tema" });
    const gastos = tema === "upvisuals" ? gastosUpvisuals : [];
    const gastado = gastos.reduce((s, g) => s + g.monto, 0);
    return enviarJSON(res, 200, {
      ...libro,
      estado_completo: libro.quedaste ? `Quedaste: ${libro.quedaste}\nDecisiones: cuotas con cinco días de tolerancia.\nPróximo paso: ${libro.proximo_paso}` : "",
      ultimo_episodio: null,
      gastado,
      gastos,
      minutos_total: 300,
      por_hora: gastado ? Math.round(((1500 - gastado) / (300 / 60)) * 100) / 100 : null,
      decisiones: tema === "upvisuals" ? ["Fase 2 se deja para noviembre."] : [],
      entregas_futuras: tema === "upvisuals" ? ["Alfonso: 1000 el " + dia(3)] : [],
      lo_que_paso: tema === "upvisuals" ? [
        { texto: "Cobro de Alfonso: $1.500", origen: "cobro", hace_min: 90 },
        { texto: "Commit: ajustar el contrato", origen: "commit", hace_min: 200 },
      ] : [],
      atento_a: tema === "upvisuals" ? ["Queda 1 paso del camino."] : [],
    });
  }
  if (req.method === "PATCH" && ruta.match(/^\/gastos\/[^/]+$/)) {
    const id = decodeURIComponent(ruta.split("/")[2]);
    const cuerpo = await leerCuerpo(req);
    const gasto = gastosUpvisuals.find((g) => g.id === id);
    if (!gasto) return enviarJSON(res, 404, { detail: "no tengo ese gasto" });
    if (typeof cuerpo.monto !== "number" || cuerpo.monto < 0) return enviarJSON(res, 422, { detail: "monto inválido" });
    gasto.monto = cuerpo.monto;
    return enviarJSON(res, 200, gasto);
  }
  if (req.method === "GET" && ruta === "/ultima-vez") return enviarJSON(res, 200, { minutos: 80 });
  if (req.method === "GET" && ruta === "/entregas") return enviarJSON(res, 200, []);
  if (req.method === "GET" && ruta === "/bandeja") return enviarJSON(res, 200, bandeja());
  if (req.method === "GET" && ruta === "/preguntas") {
    const tema = url.searchParams.get("tema");
    const pendientes = preguntas.filter((p) => p.estado === "pendiente" && (!tema || p.tema === tema));
    return enviarJSON(res, 200, pendientes.slice(0, 3));
  }
  if (req.method === "POST" && ruta.match(/^\/preguntas\/[^/]+\/(respuesta|despues)$/)) {
    const [, , id, accion] = ruta.split("/");
    const pregunta = preguntas.find((p) => p.id === id);
    if (!pregunta) return enviarJSON(res, 404, { detail: "no tengo esa pregunta" });
    if (accion === "despues") {
      pregunta.estado = "despues";
      return enviarJSON(res, 200, pregunta);
    }
    const texto = String((await leerCuerpo(req)).texto ?? "").trim();
    // Una respuesta que no se entiende: Remi repregunta con el formato y no guarda nada.
    if (texto.length < 3) {
      return enviarJSON(res, 200, { pregunta, voz: "No te entendí. Dímelo en una frase corta." });
    }
    pregunta.estado = "respondida";
    if (pregunta.campo === "fase.2.listo_cuando") listoCuandoFase2 = texto;
    if (pregunta.campo === "tipo") tipoDeMalik = /cliente/i.test(texto) ? "cliente" : "propio";
    const voz = pregunta.campo === "tipo" ? `Anotado: Malik es ${tipoDeMalik}.` : "Anotado. Quedó en el libro de Upvisuals.";
    return enviarJSON(res, 200, { pregunta, voz });
  }
  if (req.method === "GET" && ruta === "/semana") {
    const filas = bandeja();
    const destacada = filas.find((f) => f.destacada);
    return enviarJSON(res, 200, {
      ...SEMANA,
      ideas_frias: filas.filter((f) => f.fria).length,
      destacada: destacada ? { id: destacada.idea.id, texto: destacada.idea.texto, tema: destacada.idea.tema } : null,
    });
  }
  if (req.method === "POST" && ruta.match(/^\/idea\/.+\/destacar$/)) {
    const id = ruta.split("/")[2];
    const cuerpo = await leerCuerpo(req);
    if (cuerpo.destacada === true) destacadaId = id;
    else if (destacadaId === id) destacadaId = null;
    const fila = bandeja().find((f) => f.idea.id === id);
    if (!fila) return enviarJSON(res, 404, { detail: "no tengo esa idea en la Bandeja" });
    return enviarJSON(res, 200, fila);
  }
  if (req.method === "GET" && ruta === "/plata") return enviarJSON(res, 200, PLATA);
  if (req.method === "GET" && ruta === "/config/gasto") return enviarJSON(res, 200, vistaGasto());
  if (req.method === "PUT" && ruta === "/config/gasto") {
    const cuerpo = await leerCuerpo(req);
    configGasto = { tope_dia_usd: cuerpo.tope_dia_usd, tope_mes_usd: cuerpo.tope_mes_usd, activo: cuerpo.activo };
    return enviarJSON(res, 200, vistaGasto());
  }
  if (req.method === "GET" && ruta === "/libros") return enviarJSON(res, 200, libros());
  if (req.method === "GET" && ruta === "/nudges/pendiente") return enviarJSON(res, 200, nudge());
  if (req.method === "POST" && ruta.match(/^\/nudges\/.+\/respuesta$/)) {
    const cuerpo = await leerCuerpo(req);
    nudgeRespuesta = cuerpo.respuesta;
    return enviarJSON(res, 200, { id: NUDGE_ID, tipo: "ritual", voz: "Hay 1 idea fría. ¿La miramos 2 minutos?", salida_amable: true, respuesta: nudgeRespuesta });
  }
  if (req.method === "POST" && ruta.match(/^\/idea\/.+\/revision$/)) {
    const cuerpo = await leerCuerpo(req);
    if (cuerpo.decision === "soltar") ideaFriaEstado = "soltada";
    if (cuerpo.decision === "tarea") ideaFriaEstado = "proyecto";
    if (cuerpo.decision === "mantener") ideaFriaEstado = "enfriando";
    return enviarJSON(res, 200, { idea: { id: IDEA_FRIA_ID, texto: "Automatizar las facturas", origen: "texto", creada_en: iso(-50 * 3600000), enfria_hasta: iso(-2 * 3600000), estado: ideaFriaEstado, problema_vision: null, tema: "omniway" }, tarea: null });
  }
  if (req.method === "POST" && ruta === "/mensaje") {
    const cuerpo = await leerCuerpo(req);
    if (cuerpo.texto === "listo") {
      const abierto = bloqueAbierto();
      return enviarJSON(res, 200, { tipo: "hecha", texto: "Cerrada. 42 min.", voz: "Cerrada. 42 min.", tarea: { ...abierto.tarea, estado: "hecha" }, sesion: { ...abierto.sesiones[0], fin: iso(0), real_min: 42 } });
    }
    return enviarJSON(res, 200, { tipo: "cliente", texto: "Lectura de prueba para copiar.", voz: "Tenés la lectura lista.", tarea: null, sesion: null });
  }

  enviarJSON(res, 404, { detail: "no existe esa ruta en el núcleo falso" });
});

servidor.listen(PUERTO, () => {
  console.log(`núcleo falso escuchando en ${PUERTO}`);
});

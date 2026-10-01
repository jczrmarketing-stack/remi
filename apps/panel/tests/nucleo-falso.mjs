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

let nudgeRespuesta = null;
let ideaFriaEstado = "enfriando";
// Solo para las pruebas: POST /__escenario deja el núcleo falso como recién
// arrancado (el nudge sin contestar, la idea fría en la Bandeja), y con
// { bloque: false } deja Hoy sin nada abierto; POST /bloque lo vuelve a
// abrir — igual que el núcleo real.
let hayBloque = true;

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
    { id: "88888888-8888-8888-8888-888888888888", titulo: "Llamada con el banco", proyecto_id: null, estado: "camino", paso_minimo: "Cinco minutos.", estimado_min: null, real_min: null, hora: null, fecha_limite: iso(86400000), compartible: false },
  ],
  vence: [
    { titulo: "Factura Omniway", fecha: iso(0), monto: null, origen: "tarea", vence_hoy: true },
    { titulo: "Entrega Alfonso", fecha: iso(3 * 86400000), monto: 1000, origen: "entrega", vence_hoy: false },
    { titulo: "Formulario IRS", fecha: iso(20 * 86400000), monto: null, origen: "tarea", vence_hoy: false },
  ],
};

const HOY = [
  {
    tarea: { id: TAREA_ID, titulo: "Terminar el flujo de distribución", proyecto_id: null, estado: "hoy", paso_minimo: "Cinco minutos.", estimado_min: null, real_min: null, hora: null, fecha_limite: null, compartible: false },
    sesiones: [{ id: SESION_ID, tarea_id: TAREA_ID, inicio: iso(-10 * 60000), fin: null, real_min: 0, app_contexto: "upvisuals" }],
    ultima_vez_min: 80,
  },
];

const CAMINO_UPVISUALS = {
  hitos: [
    { texto: "Contrato firmado", hecho: true },
    { texto: "Anticipo recibido", hecho: true },
    { texto: "Distribución", hecho: false },
    { texto: "Seguridad crítica", hecho: false },
  ],
  siguiente: { texto: "Distribución", hecho: false },
};

const PLATA = {
  semana: { cobrado: 500, meta_semanal: 554.27 },
  mes: {
    cobrado: 500,
    meta: 2400,
    faltan: 1900,
    entregas: [{ cliente: "Beto", fecha: iso(-5 * 86400000), monto: 500 }],
  },
  proximo: { cliente: "Alfonso", fecha: iso(3 * 86400000), monto: 1000 },
  // 500 de 2.400 = 21 %: la segunda meta todavía duerme (despierta al 50 %).
  metas: [
    { nombre: "Vivir solo", horizonte_meses: 12, monto_mes: 2400, activa: true, activa_desde_pct: null },
    { nombre: "Carro", horizonte_meses: 18, monto_mes: 1100, activa: false, activa_desde_pct: 50 },
  ],
  revision_fria: { dia: "viernes", hora: "16:30", minutos: 10 },
};

const LIBROS = [
  {
    tema: "upvisuals",
    titulo: "Upvisuals",
    resumen: "Distribución de contenido para el artista.",
    compartible: true,
    quedaste: "armando el contrato.",
    proximo_paso: "mandar la propuesta.",
    hitos: CAMINO_UPVISUALS.hitos,
    entrega_cercana: { cliente: "Alfonso", fecha: iso(3 * 86400000), monto: 1000 },
    ultimo_estado_en: iso(-1 * 3600000),
    tipo: "cliente",
    fases: [
      { nombre: "Fase 1", alcance: "Distribución de contenido + seguridad crítica", monto: 5000, listo_cuando: "La demo de distribución corre con datos reales.", estado: "pagando" },
      { nombre: "Fase 2", alcance: "Generador de imágenes", monto: 3700, listo_cuando: "Genera una imagen desde el panel.", estado: "propuesta" },
      { nombre: "Fase 3", alcance: "Multi-cliente para agencias", monto: null, listo_cuando: "", estado: "sin alcance" },
    ],
    fase_actual_n: 1,
    hito_actual: { texto: "Distribución", hecho: false },
    siguientes: [{ texto: "Seguridad crítica", hecho: false }],
    paso_remi: "Escribe los encargos y lleva el camino.",
  },
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
    tipo: null,
    fases: [],
    fase_actual_n: null,
    hito_actual: null,
    siguientes: [],
    paso_remi: "",
  },
  {
    tema: "omniway",
    titulo: "Omniway",
    resumen: "La empresa.",
    compartible: false,
    quedaste: "",
    proximo_paso: "",
    hitos: [],
    entrega_cercana: null,
    ultimo_estado_en: iso(-200 * 3600000),
    tipo: null,
    fases: [],
    fase_actual_n: null,
    hito_actual: null,
    siguientes: [],
    paso_remi: "",
  },
];

function bandeja() {
  // Igual que bandeja.listar_abiertas: solo estado enfriando|lista queda
  // en la lista — soltada y proyecto salen.
  const todas = [
    { idea: { id: IDEA_FRIA_ID, texto: "Automatizar las facturas", origen: "texto", creada_en: iso(-50 * 3600000), enfria_hasta: iso(-2 * 3600000), estado: ideaFriaEstado, problema_vision: null, tema: "omniway" }, fria: ideaFriaEstado === "enfriando" },
    { idea: { id: IDEA_TIBIA_ID, texto: "App de recetas con IA", origen: "texto", creada_en: iso(-10 * 3600000), enfria_hasta: iso(38 * 3600000), estado: "enfriando", problema_vision: null, tema: null }, fria: false },
  ];
  return todas.filter((f) => f.idea.estado === "enfriando" || f.idea.estado === "lista");
}

function nudge() {
  if (nudgeRespuesta) return null;
  return { id: NUDGE_ID, tipo: "ritual", voz: "Hay 1 idea fría. ¿La miramos 2 minutos?", salida_amable: true, respuesta: null };
}

function enviarJSON(res, estado, cuerpo) {
  res.writeHead(estado, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(cuerpo === undefined ? "" : JSON.stringify(cuerpo));
}

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
    nudgeRespuesta = null;
    ideaFriaEstado = "enfriando";
    return enviarJSON(res, 200, { bloque: hayBloque });
  }
  if (req.method === "GET" && ruta === "/hoy") return enviarJSON(res, 200, hayBloque ? [...HOY, ...DEMAS_HOY] : DEMAS_HOY);
  if (req.method === "GET" && ruta === "/hoy/agenda") return enviarJSON(res, 200, AGENDA);
  if (req.method === "POST" && ruta === "/bloque") {
    const cuerpo = await leerCuerpo(req);
    if (hayBloque) return enviarJSON(res, 409, { detail: "ya hay un bloque abierto" });
    hayBloque = true;
    return enviarJSON(res, 201, { tarea: { ...HOY[0].tarea, titulo: cuerpo.titulo }, sesion: { ...HOY[0].sesiones[0], app_contexto: cuerpo.tema ?? null } });
  }
  if (req.method === "GET" && ruta.startsWith("/libros/")) {
    const tema = decodeURIComponent(ruta.split("/")[2] || "");
    const libro = LIBROS.find((l) => l.tema === tema);
    if (!libro) return enviarJSON(res, 404, { detail: "no tengo un libro con ese tema" });
    return enviarJSON(res, 200, {
      ...libro,
      estado_completo: libro.quedaste ? `Quedaste: ${libro.quedaste}\nDecisiones: cuotas con cinco días de tolerancia.\nPróximo paso: ${libro.proximo_paso}` : "",
      ultimo_episodio: null,
    });
  }
  if (req.method === "GET" && ruta === "/ultima-vez") return enviarJSON(res, 200, { minutos: 80 });
  if (req.method === "GET" && ruta === "/entregas") return enviarJSON(res, 200, []);
  if (req.method === "GET" && ruta === "/bandeja") return enviarJSON(res, 200, bandeja());
  if (req.method === "GET" && ruta === "/plata") return enviarJSON(res, 200, PLATA);
  if (req.method === "GET" && ruta === "/libros") return enviarJSON(res, 200, LIBROS);
  if (req.method === "GET" && ruta === "/nudges/pendiente") return enviarJSON(res, 200, nudge());
  if (req.method === "GET" && ruta.startsWith("/camino/")) {
    const tema = decodeURIComponent(ruta.split("/")[2] || "");
    if (tema === "upvisuals") return enviarJSON(res, 200, CAMINO_UPVISUALS);
    return enviarJSON(res, 404, { detail: "no tengo un libro con ese tema" });
  }
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
      return enviarJSON(res, 200, { tipo: "hecha", texto: "Cerrada. 42 min.", voz: "Cerrada. 42 min.", tarea: { ...HOY[0].tarea, estado: "hecha" }, sesion: { ...HOY[0].sesiones[0], fin: iso(0), real_min: 42 } });
    }
    return enviarJSON(res, 200, { tipo: "cliente", texto: "Lectura de prueba para copiar.", voz: "Tenés la lectura lista.", tarea: null, sesion: null });
  }

  enviarJSON(res, 404, { detail: "no existe esa ruta en el núcleo falso" });
});

servidor.listen(PUERTO, () => {
  console.log(`núcleo falso escuchando en ${PUERTO}`);
});

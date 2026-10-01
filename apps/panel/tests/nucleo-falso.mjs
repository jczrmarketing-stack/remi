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

const HOY = [
  {
    tarea: { id: TAREA_ID, titulo: "Terminar el flujo de distribución", proyecto_id: null, estado: "hoy", paso_minimo: "Cinco minutos.", estimado_min: null, real_min: null, compartible: false },
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
  mes: { cobrado: 500, meta: 2400, faltan: 1900 },
  proximo: { cliente: "Alfonso", fecha: iso(3 * 86400000), monto: 1000 },
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
  },
  {
    tema: "malik",
    titulo: "Malik",
    resumen: "Las cuentas de X y Reddit.",
    compartible: false,
    quedaste: "",
    proximo_paso: "",
    hitos: [],
  },
];

function bandeja() {
  // Igual que bandeja.listar_abiertas: solo estado enfriando|lista queda
  // en la lista — soltada y proyecto salen.
  const todas = [
    { idea: { id: IDEA_FRIA_ID, texto: "Automatizar las facturas", origen: "texto", creada_en: iso(-50 * 3600000), enfria_hasta: iso(-2 * 3600000), estado: ideaFriaEstado, problema_vision: null }, fria: ideaFriaEstado === "enfriando" },
    { idea: { id: IDEA_TIBIA_ID, texto: "App de recetas con IA", origen: "texto", creada_en: iso(-10 * 3600000), enfria_hasta: iso(38 * 3600000), estado: "enfriando", problema_vision: null }, fria: false },
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
  if (req.method === "GET" && ruta === "/hoy") return enviarJSON(res, 200, HOY);
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
    return enviarJSON(res, 200, { idea: { id: IDEA_FRIA_ID, texto: "Automatizar las facturas", origen: "texto", creada_en: iso(-50 * 3600000), enfria_hasta: iso(-2 * 3600000), estado: ideaFriaEstado, problema_vision: null }, tarea: null });
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

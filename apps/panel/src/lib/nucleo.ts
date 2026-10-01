// Cliente del núcleo: fetch simples contra las rutas reales de servidor.py.
// Nada de mocks acá — tests/ trae su propio núcleo falso para Playwright.
// En producción, "/nucleo" es mismo origen: next.config.mjs reenvía
// /nucleo/:path* al núcleo real (127.0.0.1:puerto, de config/nucleo.json),
// cabeceras incluidas — así el panel sirve desde el teléfono sin CORS ni la
// IP del Mac a mano. NEXT_PUBLIC_URL_NUCLEO solo manda en Playwright.
import type { Entrega, Idea, Nudge, Sesion, Tarea } from "@/contratos";

const BASE = process.env.NEXT_PUBLIC_URL_NUCLEO || "/nucleo";

export class NucleoApagado extends Error {
  status?: number;
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (error) {
    throw new NucleoApagado(`no pude llegar a ${ruta}: ${(error as Error).message}`);
  }
  if (!respuesta.ok) {
    const error = new NucleoApagado(`${ruta} devolvió ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}

export type TareaConHistorial = { tarea: Tarea; sesiones: Sesion[]; ultima_vez_min: number | null };
export type Salud = { ok: boolean; db: boolean };
export type IdeaBandeja = { idea: Idea; fria: boolean };
// `detalle`: la línea del SOP que explica ese paso (forma A del plan). Un
// núcleo que todavía no la sirve la deja sin definir; "" si el hito no es del SOP.
export type Hito = { texto: string; hecho: boolean; detalle?: string };
export type Camino = { hitos: Hito[]; siguiente: Hito | null };
export type EntregaCercana = { cliente: string; fecha: string; monto: number };
// Una fase de la propuesta, tal como está en el frontmatter del libro.
// `cobrado`: lo pagado del proyecto repartido en cascada entre las fases
// (forma A); sin definir mientras el núcleo no lo sirva.
export type Fase = { nombre: string; alcance: string; monto: number | null; listo_cuando: string; estado: string; cobrado?: number };
export type Libro = {
  tema: string;
  titulo: string;
  resumen: string;
  compartible: boolean;
  // Vacíos si el libro no tiene ## Estado todavía — nunca ausentes.
  quedaste: string;
  proximo_paso: string;
  hitos: Hito[];
  // La entrega viva (con dinero) más cercana de este libro, para el orden
  // del líder en Proyectos.
  entrega_cercana: EntregaCercana | null;
  // mtime del archivo del libro (ISO): el último escalón de ese orden.
  ultimo_estado_en: string;
  // El camino sale del SOP: «propio» | «cliente» | null si el libro no lo dice.
  tipo: string | null;
  // El nombre del cliente, del frontmatter del libro (forma A).
  cliente?: string | null;
  fases: Fase[];
  // La fase en la que está, contando desde 1. null sin fases.
  fase_actual_n: number | null;
  // El primer hito sin marcar y hasta tres que vienen después.
  hito_actual: Hito | null;
  siguientes: Hito[];
  // Qué hace Remi en el paso actual, según el SOP. "" si no aplica.
  paso_remi: string;
};
export type UltimoEpisodio = { titulo: string; resumen: string; archivo: string };
// GET /libros/{tema}: lo mismo, más el Estado entero y el último episodio.
export type LibroDetalle = Libro & { estado_completo: string; ultimo_episodio: UltimoEpisodio | null };
// GET /hoy/agenda: lo que la base sabe de fechas.
export type Vencimiento = { titulo: string; fecha: string; monto: number | null; origen: "tarea" | "entrega"; vence_hoy: boolean };
export type AgendaDeHoy = { manana: Tarea[]; vence: Vencimiento[] };
export type Meta = { nombre: string; horizonte_meses: number | null; monto_mes: number; activa: boolean; activa_desde_pct: number | null };
export type RevisionFria = { dia: string; hora: string; minutos: number | null };
export type EntregaCobrada = { cliente: string; fecha: string; monto: number };
// Lo que trajo cada línea de ingreso en el mes y los minutos que se le
// dedicaron (forma C del plan): una por línea de config/plata.json.
export type LineaDelMes = { id: string; nombre: string; cobrado_mes: number; minutos_mes: number };
export type Plata = {
  semana: { cobrado: number; meta_semanal: number };
  mes: { cobrado: number; meta: number; faltan: number; entregas: EntregaCobrada[] };
  proximo: { cliente: string; fecha: string; monto: number } | null;
  metas: Meta[];
  revision_fria: RevisionFria | null;
  // Sin definir mientras el núcleo no lo sirva.
  por_linea?: LineaDelMes[];
};
export type RespuestaMensaje = { tipo: string; texto: string; voz: string; tarea: Tarea | null; sesion: Sesion | null };

// nucleo/conexiones.py: no es un contrato (contratos/contratos.json no
// las tiene), son los tipos propios de esa ruta.
export type Prueba = { ok: boolean; mensaje_humano: string };
export type Conexion = { puesta: boolean; termina_en: string | null; ultima_prueba: Prueba | null };
export type ConexionesEstado = Record<string, Conexion>;

export const nucleo = {
  salud: () => pedir<Salud>("/salud"),
  hoy: () => pedir<TareaConHistorial[]>("/hoy"),
  ultimaVez: () => pedir<{ minutos: number | null }>("/ultima-vez"),
  entregas: () => pedir<Entrega[]>("/entregas"),
  bandeja: () => pedir<IdeaBandeja[]>("/bandeja"),
  nudgePendiente: () => pedir<Nudge | null>("/nudges/pendiente"),
  plata: () => pedir<Plata>("/plata"),
  libros: () => pedir<Libro[]>("/libros"),
  agenda: () => pedir<AgendaDeHoy>("/hoy/agenda"),
  // 404 acá es un dato legítimo (ese tema no tiene libro), no el núcleo
  // caído: null, no una excepción.
  libro: async (tema: string): Promise<LibroDetalle | null> => {
    try {
      return await pedir<LibroDetalle>(`/libros/${encodeURIComponent(tema)}`);
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return null;
      throw error;
    }
  },

  responderNudge: (id: string, respuesta: "listo" | "ahora_no") =>
    pedir<Nudge>(`/nudges/${id}/respuesta`, { method: "POST", body: JSON.stringify({ respuesta }) }),

  revisarIdea: (id: string, decision: "soltar" | "mantener" | "tarea") =>
    pedir<{ idea: Idea; tarea: Tarea | null }>(`/idea/${id}/revision`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),

  cerrarBloque: () =>
    pedir<RespuestaMensaje>("/mensaje", { method: "POST", body: JSON.stringify({ texto: "listo" }) }),

  abrirDesdeTexto: (texto: string) =>
    pedir<RespuestaMensaje>("/mensaje", { method: "POST", body: JSON.stringify({ texto }) }),

  // Un botón del panel abre un bloque sin pasar por el clasificador. 409 si
  // ya hay otro abierto: una cosa a la vez.
  abrirBloque: (titulo: string, tema: string | null) =>
    pedir<{ tarea: Tarea; sesion: Sesion }>("/bloque", { method: "POST", body: JSON.stringify({ titulo, tema }) }),

  // Marca o desmarca el hito número `n` (desde 1) del camino de ese libro.
  // El núcleo edita solo esa línea y deja un commit en la bóveda.
  marcarHito: (tema: string, n: number, hecho: boolean) =>
    pedir<Camino>(`/libros/${encodeURIComponent(tema)}/camino/${n}`, { method: "POST", body: JSON.stringify({ hecho }) }),

  pasoMinimo: (tareaId: string, paso_minimo: string) =>
    pedir<Tarea>(`/tarea/${tareaId}/paso-minimo`, { method: "POST", body: JSON.stringify({ paso_minimo }) }),

  // Remi redacta, nunca envía: la respuesta se copia, no sale sola.
  leerParaCliente: (texto: string) =>
    pedir<RespuestaMensaje>("/mensaje", {
      method: "POST",
      body: JSON.stringify({ texto, think: true }),
    }),

  // Ajustes → Conexiones. Solo funciona desde el Mac: con una cabecera
  // Cf-* (vino por el túnel) el núcleo responde 403.
  conexiones: () => pedir<ConexionesEstado>("/config/conexiones"),
  guardarConexion: (nombre: string, valor: string) =>
    pedir<Conexion>(`/config/conexiones/${encodeURIComponent(nombre)}`, {
      method: "PUT",
      body: JSON.stringify({ valor }),
    }),
  probarConexion: (nombre: string) =>
    pedir<Prueba>(`/config/conexiones/${encodeURIComponent(nombre)}/probar`, { method: "POST" }),
  guardarMetaMensual: (meta_mensual: number) =>
    pedir<{ meta_mensual: number; moneda: string }>("/config/plata", {
      method: "PUT",
      body: JSON.stringify({ meta_mensual }),
    }),
};

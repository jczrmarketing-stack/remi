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
export type Hito = { texto: string; hecho: boolean };
export type Camino = { hitos: Hito[]; siguiente: Hito | null };
export type EntregaCercana = { cliente: string; fecha: string; monto: number };
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
};
export type EntregaCobrada = { cliente: string; fecha: string; monto: number };
export type Plata = {
  semana: { cobrado: number; meta_semanal: number };
  mes: { cobrado: number; meta: number; faltan: number; entregas: EntregaCobrada[] };
  proximo: { cliente: string; fecha: string; monto: number } | null;
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
  // 404 acá es un dato legítimo (ese tema no tiene libro), no el núcleo
  // caído: null, no una excepción.
  camino: async (tema: string): Promise<Camino | null> => {
    try {
      return await pedir<Camino>(`/camino/${encodeURIComponent(tema)}`);
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return null;
      throw error;
    }
  },
  nudgePendiente: () => pedir<Nudge | null>("/nudges/pendiente"),
  plata: () => pedir<Plata>("/plata"),
  libros: () => pedir<Libro[]>("/libros"),

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

import type { Sesion, Tarea } from "./contratos";
import { URL_NUCLEO } from "./config";

// Solo viene cuando pensó con Claude. Dato de operación: va a la consola,
// nunca a la pantalla.
export interface TokensClaude {
  entrada: number;
  salida: number;
  modelo: string;
}

export interface RespuestaMensaje {
  tarea: Tarea;
  sesion: Sesion;
  voz: string;
  tokens: TokensClaude | null;
}

// Si el núcleo no responde, no nos quedamos esperando para siempre en
// "pensando" — a los 8s el fetch se cancela solo y enviar() lo trata
// como cualquier otro fallo (ley 3: Remi lo dice sin culpa, no revienta).
const TIMEOUT_NUCLEO_MS = 8000;

// think: opt-in por mensaje a pensar con Claude. Apagado, el núcleo no
// gasta un token.
export async function enviarMensaje(texto: string, think = false): Promise<RespuestaMensaje> {
  const controlador = new AbortController();
  const limite = setTimeout(() => controlador.abort(), TIMEOUT_NUCLEO_MS);
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/mensaje`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto, think }),
      signal: controlador.signal,
    });
    if (!respuesta.ok) {
      throw new Error(`El núcleo respondió ${respuesta.status}`);
    }
    return (await respuesta.json()) as RespuestaMensaje;
  } finally {
    clearTimeout(limite);
  }
}

interface TareaConHistorial {
  tarea: Tarea;
  sesiones: Sesion[];
  ultima_vez_min: number | null;
}

// Ley 1 hecha dato: cuánto tardó la última vez, para comparar contra
// la sesión en curso. null si la tarea nunca tuvo una sesión cerrada
// — no hay de dónde sacarlo, y no se inventa.
export async function obtenerUltimaVezMin(tareaId: string): Promise<number | null> {
  const respuesta = await fetch(`${URL_NUCLEO}/hoy`);
  if (!respuesta.ok) {
    throw new Error(`El núcleo respondió ${respuesta.status}`);
  }
  const tareas = (await respuesta.json()) as TareaConHistorial[];
  const encontrada = tareas.find((t) => t.tarea.id === tareaId);
  return encontrada ? encontrada.ultima_vez_min : null;
}

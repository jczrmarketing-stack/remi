import type { Sesion, Tarea } from "./contratos";
import { URL_NUCLEO } from "./config";

export interface RespuestaMensaje {
  tarea: Tarea;
  sesion: Sesion;
  voz: string;
}

export async function enviarMensaje(texto: string): Promise<RespuestaMensaje> {
  const respuesta = await fetch(`${URL_NUCLEO}/mensaje`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto }),
  });
  if (!respuesta.ok) {
    throw new Error(`El núcleo respondió ${respuesta.status}`);
  }
  return (await respuesta.json()) as RespuestaMensaje;
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

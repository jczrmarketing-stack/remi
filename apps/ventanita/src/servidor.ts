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

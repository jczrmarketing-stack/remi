import type { Sesion, Tarea } from "./contratos";
import { URL_NUCLEO } from "./config";

// Solo viene cuando pensó con Claude. Dato de operación: va a la consola,
// nunca a la pantalla.
export interface TokensClaude {
  entrada: number;
  salida: number;
  modelo: string;
}

// Lo que decís no siempre es una tarea: el núcleo clasifica sin IA.
// "idea" enfría en la Bandeja y no crea nada; "hoy" abre un bloque;
// "hecha" cierra el que estaba. Por eso tarea y sesion pueden faltar.
export type TipoMensaje = "idea" | "hoy" | "hecha" | "pregunta" | "encargo";

export interface RespuestaMensaje {
  tipo: TipoMensaje;
  tarea: Tarea | null;
  sesion: Sesion | null;
  // Lo que se ve, completo.
  texto: string;
  // Lo que se dice: igual a texto, salvo por voz (hasta 3 frases).
  voz: string;
  tokens: TokensClaude | null;
}

// Si el núcleo no responde, no nos quedamos esperando para siempre en
// "pensando": el fetch se cancela solo y enviar() lo trata como cualquier
// otro fallo (ley 3: Remi lo dice sin culpa, no revienta).
//
// Tiene que ser MAYOR que nucleo/pensar.py:PEOR_CASO_SEGUNDOS (Opus en
// extra 90 s + Sonnet 45 s + Haiku 20 s = 155 s, si cae por toda la cadena). Estaba en 8 s: Remi decía «No pude guardarlo» mientras el núcleo
// seguía guardando, y si lo repetías quedaba duplicado — una culpa por
// algo que sí había pasado, que es lo que la ley 3 prohíbe.
// pruebas/test_timeouts.py ata los dos números para que no se separen.
const TIMEOUT_NUCLEO_MS = 160000;

export interface MotorDePensar {
  id: string;
  label: string;
  disponible: boolean;
  detalle: string;
}

// Lo que el dropdown puede elegir, y qué le falta a cada uno.
export async function obtenerMotores(): Promise<MotorDePensar[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/pensar/motores`);
  if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
  return (await respuesta.json()) as MotorDePensar[];
}

// think: opt-in por mensaje a pensar. Apagado, el núcleo no gasta un token.
// motor: con cuál, elegido a conciencia en el dropdown.
export async function enviarMensaje(
  texto: string,
  think = false,
  motor: string | null = null,
  modo: string | null = null,
  nivel: string | null = null,
): Promise<RespuestaMensaje> {
  const controlador = new AbortController();
  const limite = setTimeout(() => controlador.abort(), TIMEOUT_NUCLEO_MS);
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/mensaje`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        texto,
        think,
        motor: think ? motor : null,
        ...(think && modo ? { modo } : {}),
        ...(think && nivel ? { nivel } : {}),
      }),
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

async function obtenerHoy(): Promise<TareaConHistorial[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/hoy`);
  if (!respuesta.ok) {
    throw new Error(`El núcleo respondió ${respuesta.status}`);
  }
  return (await respuesta.json()) as TareaConHistorial[];
}

// Ley 1 hecha dato: cuánto tardó la última vez, para comparar contra
// la sesión en curso. null si la tarea nunca tuvo una sesión cerrada
// — no hay de dónde sacarlo, y no se inventa.
export async function obtenerUltimaVezMin(tareaId: string): Promise<number | null> {
  const encontrada = (await obtenerHoy()).find((t) => t.tarea.id === tareaId);
  return encontrada ? encontrada.ultima_vez_min : null;
}

// Para el reposo: cuánto tardó el último bloque que se cerró. null hasta
// que se cierre el primero — la ley 1 no inventa números.
//
// No es «la última vez que hiciste ESTA tarea», que sería lo ideal, porque
// en reposo no hay ninguna tarea elegida: al decir «listo» la tarea pasa a
// `hecha` y sale de las de hoy, así que mirar ahí nunca mostraría el bloque
// que acabás de cerrar.
export async function obtenerUltimaVezDeHoy(): Promise<number | null> {
  const respuesta = await fetch(`${URL_NUCLEO}/ultima-vez`);
  if (!respuesta.ok) {
    throw new Error(`El núcleo respondió ${respuesta.status}`);
  }
  return ((await respuesta.json()) as { minutos: number | null }).minutos;
}

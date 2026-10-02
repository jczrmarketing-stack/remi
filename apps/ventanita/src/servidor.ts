import type { Entrega, Nudge, Sesion, Tarea } from "./contratos";
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
// "agenda" (T2): una fecha/hora reconocida, crea tarea sin abrir bloque.
// "cobro" y "entrega" (T2): plata que entró o que viene, habladas — ninguna
// de las tres lleva sesion, así que nunca abren el Reloj.
export type TipoMensaje =
  | "idea" | "hoy" | "hecha" | "pregunta" | "encargo"
  | "agenda" | "cobro" | "entrega";

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
// Con qué piensa este mensaje (el chip de cerebro) y cómo entró.
export interface OpcionesMensaje {
  think: boolean;
  motor: string;
  modo?: string | null;
  nivel?: string | null;
  modeloOllama?: string | null;
  modeloVenice?: string | null;
  // Por voz, lo que se dice son hasta 3 frases; el chat muestra todo.
  origen?: "voz" | "texto";
}

export async function enviarMensaje(texto: string, opciones: OpcionesMensaje): Promise<RespuestaMensaje> {
  const { think, motor, modo, nivel, modeloOllama, modeloVenice, origen } = opciones;
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
        ...(think && modeloOllama ? { modelo_ollama: modeloOllama } : {}),
        ...(think && modeloVenice ? { modelo_venice: modeloVenice } : {}),
        ...(origen ? { origen } : {}),
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

// — El chat (3c) —

export interface TurnoDelChat {
  rol: "juan" | "remi";
  texto: string;
  fecha: string;
}

// La conversación vigente (la de la última hora), para abrir con el chat.
// Tres líneas al abrir, si hay un proyecto activo. Vacío: no se dice nada.
export async function dondeQuede(): Promise<string[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/donde-quede`);
  if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
  const datos = (await respuesta.json()) as { lineas: string[] };
  return datos.lineas;
}

export async function obtenerConversacion(): Promise<TurnoDelChat[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/conversacion`);
  if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
  return (await respuesta.json()) as TurnoDelChat[];
}

// Lo que da `ollama list`. Vacío si Ollama no está.
export async function obtenerModelosOllama(): Promise<string[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/pensar/ollama`);
  if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
  return (await respuesta.json()) as string[];
}

export interface EpisodioGuardado {
  titulo: string;
  tema: string;
  resumen: string;
  archivo: string;
  resumido_por: string;
}

// Una charla pegada, resumida y guardada en remi-mente/episodios/.
export async function guardarEpisodio(texto: string): Promise<EpisodioGuardado> {
  const controlador = new AbortController();
  const limite = setTimeout(() => controlador.abort(), TIMEOUT_NUCLEO_MS);
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/episodio`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto }),
      signal: controlador.signal,
    });
    if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
    return (await respuesta.json()) as EpisodioGuardado;
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
// «Hecha»: cierra el bloque abierto, marca la tarea hecha y devuelve la
// duración real de la sesión (ley 1). null si el núcleo no respondió — sin
// eso, el chat no celebra una fiesta que no pasó (ley 3).
export async function cerrarTarea(tareaId: string): Promise<number | null> {
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/tarea/${tareaId}/estado`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estado: "hecha" }),
    });
    if (!respuesta.ok) return null;
    const tarea = (await respuesta.json()) as Tarea;
    return tarea.real_min ?? 0;
  } catch {
    return null;
  }
}

// Piel dinero (3f · 3): si el proyecto de la tarea abierta tiene una
// entrega viva (no pagada, con monto), Remi se pinta de `dinero` en vez de
// `brasa`. null ante cualquier falla: sin entrega no cambia nada, no rompe.
export async function obtenerEntregaDeProyecto(proyectoId: string): Promise<Entrega | null> {
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/entregas/de-proyecto/${proyectoId}`);
    if (!respuesta.ok) return null;
    return (await respuesta.json()) as Entrega | null;
  } catch {
    return null;
  }
}

// Nudges dentro del chat (3f · 6). El backend todavía puede no existir
// (Fase 3): un 404/500/red caído no rompe nada, solo dice «no hay».
export async function obtenerNudgePendiente(): Promise<Nudge | null> {
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/nudges/pendiente`);
    if (!respuesta.ok) return null;
    return (await respuesta.json()) as Nudge | null;
  } catch {
    return null;
  }
}

export async function responderNudge(nudgeId: string, respuesta: "listo" | "ahora_no"): Promise<boolean> {
  try {
    const contestada = await fetch(`${URL_NUCLEO}/nudges/${nudgeId}/respuesta`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ respuesta }),
    });
    return contestada.ok;
  } catch {
    return false;
  }
}

export async function obtenerUltimaVezDeHoy(): Promise<number | null> {
  const respuesta = await fetch(`${URL_NUCLEO}/ultima-vez`);
  if (!respuesta.ok) {
    throw new Error(`El núcleo respondió ${respuesta.status}`);
  }
  return ((await respuesta.json()) as { minutos: number | null }).minutos;
}

// Aviso de Notion en la ventanita: lo que el núcleo trajo de «Remi · CRM de
// vida» (nucleo/notion_avisos.py). Acá solo lo puro y lo que habla con el
// núcleo; lo que toca la ventana de Tauri vive en useAvisoNotion.ts.
import { URL_NUCLEO } from "./config";
import type { Pantalla, Posicion, Tamano } from "./ventana";

// El núcleo ya consulta Notion cada 5 min; esto solo pregunta a la máquina de
// casa (127.0.0.1), así que 30 s no cuesta nada y el aviso sale casi al vencer.
export const MS_ENTRE_CONSULTAS_AVISO_NOTION = 30 * 1000;
export const TAMANO_AVISO_NOTION: Tamano = { width: 360, height: 220 };
const ALTO_BARRA_DE_MENU = 40;

export interface AvisoDeNotion {
  id: string;
  que: string;
  paso_minimo: string;
  // Ya salió antes: ahora va el paso mínimo primero, no lo mismo (ley 3).
  encogido: boolean;
}

export type RespuestaAvisoNotion = "listo" | "ahora_no";

/** Mientras es true, App no guarda el lugar de la ventana ni la redimensiona sola. */
export const avisoEnPantalla = { activo: false };

export interface BloqueAviso {
  rotulo: string | null;
  texto: string;
  fuerte: boolean;
}

/**
 * Qué se muestra y qué pesa más. La primera vez: el «Qué» y debajo su paso
 * mínimo. Si ya salió antes, el paso mínimo es lo que se ve y el «Qué» queda
 * callado. Nada se marca urgente (ley 4): lo que pesa más se ve más calmado,
 * no más grande ni de otro color.
 */
export function bloquesDelAviso(aviso: AvisoDeNotion): BloqueAviso[] {
  const que = aviso.que.trim();
  const paso = aviso.paso_minimo.trim();
  if (!paso) return [{ rotulo: null, texto: que, fuerte: true }];
  if (aviso.encogido) {
    return [
      { rotulo: "Paso mínimo", texto: paso, fuerte: true },
      { rotulo: null, texto: que, fuerte: false },
    ];
  }
  return [
    { rotulo: null, texto: que, fuerte: true },
    { rotulo: "Paso mínimo", texto: paso, fuerte: false },
  ];
}

/** Pegada al borde derecho de la pantalla, debajo de la barra de menú: de ahí entra deslizándose. */
export function lugarDelAviso(pantalla: Pantalla, tamano: Tamano): Posicion {
  return {
    x: Math.round(pantalla.x + pantalla.width - tamano.width),
    y: Math.round(pantalla.y + ALTO_BARRA_DE_MENU),
  };
}

export async function obtenerAvisoNotionPendiente(): Promise<AvisoDeNotion | null> {
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/notion/avisos/pendiente`);
    if (!respuesta.ok) return null;
    return (await respuesta.json()) as AvisoDeNotion | null;
  } catch {
    return null;
  }
}

export async function responderAvisoNotion(id: string, respuesta: RespuestaAvisoNotion): Promise<boolean> {
  try {
    const contestada = await fetch(`${URL_NUCLEO}/notion/avisos/${encodeURIComponent(id)}/respuesta`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ respuesta }),
    });
    return contestada.ok;
  } catch {
    return false;
  }
}

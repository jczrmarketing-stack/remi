// Tamaño y lugar de la ventana abierta (3c · 6): redimensionable, movible,
// y se acuerda de los dos entre aperturas. Lo que decide es puro y se
// prueba; lo que toca Tauri vive en App.

export interface Tamano {
  width: number;
  height: number;
}

export interface Posicion {
  x: number;
  y: number;
}

export interface Pantalla {
  x: number;
  y: number;
  width: number;
  height: number;
}

export const TAMANO_MINIMO: Tamano = { width: 360, height: 240 };
export const TAMANO_CHAT_POR_DEFECTO: Tamano = { width: 420, height: 520 };
// Nunca más grande que esto de la pantalla.
export const FRACCION_MAXIMA = 0.9;

export function tamanoMaximo(pantalla: Pantalla): Tamano {
  return {
    width: Math.floor(pantalla.width * FRACCION_MAXIMA),
    height: Math.floor(pantalla.height * FRACCION_MAXIMA),
  };
}

export function limitarTamano(tamano: Tamano, pantalla: Pantalla | null): Tamano {
  const maximo = pantalla ? tamanoMaximo(pantalla) : { width: Infinity, height: Infinity };
  return {
    width: Math.round(Math.max(TAMANO_MINIMO.width, Math.min(maximo.width, tamano.width))),
    height: Math.round(Math.max(TAMANO_MINIMO.height, Math.min(maximo.height, tamano.height))),
  };
}

/**
 * Dónde poner la ventana para que entre entera en la pantalla. Abrir el
 * chat desde una píldora pegada al borde de abajo lo dejaría medio afuera:
 * se corre lo justo, hacia arriba o a la izquierda.
 */
export function posicionQueEntra(posicion: Posicion, tamano: Tamano, pantalla: Pantalla | null): Posicion {
  if (!pantalla) return posicion;
  const x = Math.min(Math.max(pantalla.x, posicion.x), pantalla.x + pantalla.width - tamano.width);
  const y = Math.min(Math.max(pantalla.y, posicion.y), pantalla.y + pantalla.height - tamano.height);
  return { x: Math.round(Math.max(pantalla.x, x)), y: Math.round(Math.max(pantalla.y, y)) };
}

const CLAVE_TAMANO = "remi.ventana.tamano";
const CLAVE_POSICION = "remi.ventana.posicion";

function leerJson<T>(clave: string, valido: (v: unknown) => v is T): T | null {
  try {
    const crudo = localStorage.getItem(clave);
    if (!crudo) return null;
    const valor: unknown = JSON.parse(crudo);
    return valido(valor) ? valor : null;
  } catch {
    return null;
  }
}

function guardarJson(clave: string, valor: unknown): void {
  try {
    localStorage.setItem(clave, JSON.stringify(valor));
  } catch {
    // Sin almacenamiento, la ventana arranca con lo de siempre.
  }
}

const esTamano = (v: unknown): v is Tamano =>
  typeof v === "object" && v !== null && Number.isFinite((v as Tamano).width) && Number.isFinite((v as Tamano).height);
const esPosicion = (v: unknown): v is Posicion =>
  typeof v === "object" && v !== null && Number.isFinite((v as Posicion).x) && Number.isFinite((v as Posicion).y);

export const obtenerTamanoChat = (): Tamano => leerJson(CLAVE_TAMANO, esTamano) ?? TAMANO_CHAT_POR_DEFECTO;
export const fijarTamanoChat = (t: Tamano): void => guardarJson(CLAVE_TAMANO, { width: Math.round(t.width), height: Math.round(t.height) });
export const obtenerPosicion = (): Posicion | null => leerJson(CLAVE_POSICION, esPosicion);
export const fijarPosicion = (p: Posicion): void => guardarJson(CLAVE_POSICION, { x: Math.round(p.x), y: Math.round(p.y) });

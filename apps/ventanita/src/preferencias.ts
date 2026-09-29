// Preferencias de la voz de Remi, persistidas entre sesiones (localStorage
// del webview: sobrevive a cerrar y volver a abrir la ventanita). El mute y
// la velocidad viven juntos acá: son las dos perillas de la misma voz.
const CLAVE_SILENCIO = "remi.voz.silenciada";
const CLAVE_VELOCIDAD = "remi.voz.velocidad";

export const VELOCIDADES = [1, 1.5, 2] as const;
export type Velocidad = (typeof VELOCIDADES)[number];

function leer(clave: string): string | null {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
}

function guardar(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    // Sin localStorage la preferencia no persiste, pero tampoco rompe nada.
  }
}

export function estaSilenciado(): boolean {
  return leer(CLAVE_SILENCIO) === "1";
}

export function alternarSilencio(): boolean {
  const nuevo = !estaSilenciado();
  guardar(CLAVE_SILENCIO, nuevo ? "1" : "0");
  return nuevo;
}

function esVelocidad(valor: number): valor is Velocidad {
  return (VELOCIDADES as readonly number[]).includes(valor);
}

export function obtenerVelocidad(): Velocidad {
  const guardada = Number(leer(CLAVE_VELOCIDAD));
  return esVelocidad(guardada) ? guardada : 1;
}

export function fijarVelocidad(velocidad: Velocidad): void {
  guardar(CLAVE_VELOCIDAD, String(velocidad));
}

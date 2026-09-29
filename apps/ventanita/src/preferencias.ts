// Preferencias de la voz de Remi, persistidas entre sesiones (localStorage
// del webview: sobrevive a cerrar y volver a abrir la ventanita). El mute y
// la velocidad viven juntos acá: son las dos perillas de la misma voz.
const CLAVE_SILENCIO = "remi.voz.silenciada";
const CLAVE_VELOCIDAD = "remi.voz.velocidad";
const CLAVE_VOZ = "remi.voz.elegida";
const CLAVE_MOTOR = "remi.pensar.motor";

export const VELOCIDADES = [1, 1.5, 2] as const;
export type Velocidad = (typeof VELOCIDADES)[number];

// "auto" deja que el núcleo elija por el texto; el resto es el id de una
// voz concreta. Se guarda como string: si el núcleo cambia su lista, una
// preferencia vieja simplemente deja de coincidir y vuelve a "auto".
export type PreferenciaVoz = string;
export const VOZ_AUTOMATICA = "auto";

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

export function obtenerVoz(): PreferenciaVoz {
  return leer(CLAVE_VOZ) ?? VOZ_AUTOMATICA;
}

export function fijarVoz(voz: PreferenciaVoz): void {
  guardar(CLAVE_VOZ, voz);
}

// Con qué motor piensa Remi, elegido a conciencia en el dropdown. Se guarda
// como string: si el núcleo cambia su lista, uno viejo cae al por defecto
// del núcleo y no rompe nada.
export type Motor = string;
export const MOTOR_POR_DEFECTO: Motor = "claude";

export function obtenerMotor(): Motor {
  return leer(CLAVE_MOTOR) ?? MOTOR_POR_DEFECTO;
}

export function fijarMotor(motor: Motor): void {
  guardar(CLAVE_MOTOR, motor);
}

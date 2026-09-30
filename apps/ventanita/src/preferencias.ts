// Preferencias de la voz de Remi, persistidas entre sesiones (localStorage
// del webview: sobrevive a cerrar y volver a abrir la ventanita). El mute y
// la velocidad viven juntos acá: son las dos perillas de la misma voz.
const CLAVE_SILENCIO = "remi.voz.silenciada";
const CLAVE_VELOCIDAD = "remi.voz.velocidad";
const CLAVE_VOZ = "remi.voz.elegida";
const CLAVE_MOTOR = "remi.pensar.motor";
const CLAVE_SIN_PENSAR = "remi.pensar.apagado";
const CLAVE_MODO = "remi.pensar.modo";

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

// Venice es pago: se elige a mano cada vez, nunca queda como valor por
// defecto ni vuelve por arrastre de una preferencia vieja.
const MOTORES_QUE_NO_SE_HEREDAN: readonly Motor[] = ["venice"];

export function obtenerMotor(): Motor {
  const guardado = leer(CLAVE_MOTOR) ?? MOTOR_POR_DEFECTO;
  return MOTORES_QUE_NO_SE_HEREDAN.includes(guardado) ? MOTOR_POR_DEFECTO : guardado;
}

export function fijarMotor(motor: Motor): void {
  guardar(CLAVE_MOTOR, motor);
}

// «sin pensar»: apaga el envío al modelo. NO se apaga solo tras un mensaje:
// es una decisión que queda puesta hasta que la saques.
export function estaSinPensar(): boolean {
  return leer(CLAVE_SIN_PENSAR) === "1";
}

export function fijarSinPensar(apagado: boolean): void {
  guardar(CLAVE_SIN_PENSAR, apagado ? "1" : "0");
}

// Rápido (Haiku), equilibrio (Sonnet) o inteligente (Opus con razonamiento).
// «prompt» no es un cerebro sino un formato: lo que decís vuelve como un
// encargo de una tarea para Claude Code.
export const MODOS = ["rapido", "equilibrio", "inteligente", "prompt"] as const;
export type ModoPensar = (typeof MODOS)[number];
export const MODO_POR_DEFECTO: ModoPensar = "equilibrio";

export function obtenerModo(): ModoPensar {
  const guardado = leer(CLAVE_MODO);
  return (MODOS as readonly string[]).includes(guardado ?? "") ? (guardado as ModoPensar) : MODO_POR_DEFECTO;
}

export function fijarModo(modo: ModoPensar): void {
  guardar(CLAVE_MODO, modo);
}

// — El chip «Opus 5.5 · Medio» (maqueta de Juan Camilo, 30/09/2026) —
// Un solo lugar elige con qué piensa Remi. Por debajo sigue siendo lo mismo
// de antes (motor + modo + «sin pensar»): el chip solo lo nombra distinto.
export const CEREBROS = ["haiku", "sonnet", "opus", "venice", "ollama", "prompt", "sin-pensar"] as const;
export type Cerebro = (typeof CEREBROS)[number];

export const NIVELES = ["bajo", "medio", "alto"] as const;
export type Nivel = (typeof NIVELES)[number];

interface Eleccion {
  motor: Motor;
  modo: ModoPensar;
  sinPensar: boolean;
}

const MODO_DE_CLAUDE: Partial<Record<Cerebro, ModoPensar>> = {
  haiku: "rapido",
  sonnet: "equilibrio",
  opus: "inteligente",
};

export function cerebroDe({ motor, modo, sinPensar }: Eleccion): Cerebro {
  if (sinPensar) return "sin-pensar";
  if (modo === "prompt") return "prompt";
  if (motor === "venice" || motor === "ollama") return motor;
  if (modo === "rapido") return "haiku";
  if (modo === "inteligente") return "opus";
  return "sonnet";
}

export function eleccionDe(cerebro: Cerebro): Eleccion {
  if (cerebro === "sin-pensar") return { motor: MOTOR_POR_DEFECTO, modo: MODO_POR_DEFECTO, sinPensar: true };
  if (cerebro === "prompt") return { motor: MOTOR_POR_DEFECTO, modo: "prompt", sinPensar: false };
  if (cerebro === "venice" || cerebro === "ollama") return { motor: cerebro, modo: MODO_POR_DEFECTO, sinPensar: false };
  return { motor: MOTOR_POR_DEFECTO, modo: MODO_DE_CLAUDE[cerebro] ?? MODO_POR_DEFECTO, sinPensar: false };
}

// Solo los modelos de Anthropic tienen nivel. Opus arranca en medio (lo que
// ya hacía: piensa antes); Haiku y Sonnet, en bajo.
export function tieneNivel(cerebro: Cerebro): boolean {
  return cerebro === "haiku" || cerebro === "sonnet" || cerebro === "opus";
}

export function nivelPorDefecto(cerebro: Cerebro): Nivel {
  return cerebro === "opus" ? "medio" : "bajo";
}

const CLAVE_NIVEL = "remi.pensar.nivel";

export function obtenerNivel(): Nivel | null {
  const guardado = leer(CLAVE_NIVEL);
  return (NIVELES as readonly string[]).includes(guardado ?? "") ? (guardado as Nivel) : null;
}

export function fijarNivel(nivel: Nivel): void {
  guardar(CLAVE_NIVEL, nivel);
}

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

// Desde 3c el chip nombra la voz («Alex · 1,5×»): «auto» (que elegía por
// idioma) pasa a Alex, la de español por defecto.
export const VOZ_POR_DEFECTO: PreferenciaVoz = "em_alex";

export function obtenerVoz(): PreferenciaVoz {
  const guardada = leer(CLAVE_VOZ);
  return !guardada || guardada === VOZ_AUTOMATICA ? VOZ_POR_DEFECTO : guardada;
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

// — El chip de cerebro (3c · 4) —
// Un solo menú elige el motor y lo que ese motor ofrece: Claude (por Max)
// con modelo × nivel de razonamiento; Ollama con su lista real; Venice.
// El modo Prompt y «sin pensar» ya no se eligen (3b.5/3b.6).
export const MODELOS_CLAUDE = ["haiku", "sonnet", "opus"] as const;
export type ModeloClaude = (typeof MODELOS_CLAUDE)[number];

// «extra» se muestra «máx»: es el mismo valor que ya entiende el núcleo.
export const NIVELES = ["bajo", "medio", "alto", "extra"] as const;
export type Nivel = (typeof NIVELES)[number];

// Los dos de Venice. El primero es el económico; Grok es el que menos inventa.
export const MODELOS_VENICE = ["z-ai-glm-5-3-flash", "grok-4-7"] as const;
export type ModeloVenice = (typeof MODELOS_VENICE)[number];
const NOMBRE_VENICE: Record<ModeloVenice, string> = {
  "z-ai-glm-5-3-flash": "GLM Flash",
  "grok-4-7": "Grok 4.7",
};

export type EleccionCerebro =
  | { motor: "claude"; modelo: ModeloClaude; nivel: Nivel }
  | { motor: "ollama"; modelo: string }
  | { motor: "groq" }
  | { motor: "venice"; modelo: ModeloVenice };

export const CEREBRO_POR_DEFECTO: EleccionCerebro = { motor: "claude", modelo: "sonnet", nivel: "bajo" };

const MODO_DE: Record<ModeloClaude, ModoPensar> = { haiku: "rapido", sonnet: "equilibrio", opus: "inteligente" };
const NOMBRE_MODELO: Record<ModeloClaude, string> = { haiku: "Haiku", sonnet: "Sonnet", opus: "Opus" };
export const NOMBRE_NIVEL: Record<Nivel, string> = { bajo: "bajo", medio: "medio", alto: "alto", extra: "máx" };

/** Cómo va en el <select> y en el guardado: «claude:sonnet:medio», «ollama:gemma3:4b», «venice:grok-4-7». */
export function valorDe(e: EleccionCerebro): string {
  if (e.motor === "claude") return `claude:${e.modelo}:${e.nivel}`;
  if (e.motor === "ollama") return `ollama:${e.modelo}`;
  if (e.motor === "groq") return "groq";
  return `venice:${e.modelo}`;
}

function esModeloVenice(valor: string): valor is ModeloVenice {
  return (MODELOS_VENICE as readonly string[]).includes(valor);
}

export function deValor(valor: string | null): EleccionCerebro | null {
  if (!valor) return null;
  if (valor === "groq") return { motor: "groq" };
  // «venice» a secas es una preferencia vieja: cae al económico.
  if (valor === "venice" || valor.startsWith("venice:")) {
    const id = valor === "venice" ? MODELOS_VENICE[0] : valor.slice("venice:".length);
    return esModeloVenice(id) ? { motor: "venice", modelo: id } : null;
  }
  if (valor.startsWith("ollama:") && valor.length > "ollama:".length) {
    return { motor: "ollama", modelo: valor.slice("ollama:".length) };
  }
  const [motor, modelo, nivel] = valor.split(":");
  if (
    motor === "claude" &&
    (MODELOS_CLAUDE as readonly string[]).includes(modelo) &&
    (NIVELES as readonly string[]).includes(nivel)
  ) {
    return { motor: "claude", modelo: modelo as ModeloClaude, nivel: nivel as Nivel };
  }
  return null;
}

/** Lo que muestra el chip: «Sonnet · medio», «gemma3:4b», «Grok 4.7». */
export function etiquetaDe(e: EleccionCerebro): string {
  if (e.motor === "claude") return `${NOMBRE_MODELO[e.modelo]} · ${NOMBRE_NIVEL[e.nivel]}`;
  if (e.motor === "ollama") return e.modelo;
  if (e.motor === "groq") return "Groq · rápido";
  return NOMBRE_VENICE[e.modelo];
}

/** Lo que viaja al núcleo con cada mensaje. */
export function paraEnviar(e: EleccionCerebro): {
  motor: string;
  modo: ModoPensar;
  nivel: Nivel | null;
  modeloOllama: string | null;
  modeloVenice: string | null;
} {
  if (e.motor === "claude") {
    return { motor: "claude", modo: MODO_DE[e.modelo], nivel: e.nivel, modeloOllama: null, modeloVenice: null };
  }
  if (e.motor === "ollama") {
    return { motor: "ollama", modo: MODO_POR_DEFECTO, nivel: null, modeloOllama: e.modelo, modeloVenice: null };
  }
  if (e.motor === "groq") {
    return { motor: "groq", modo: MODO_POR_DEFECTO, nivel: null, modeloOllama: null, modeloVenice: null };
  }
  return { motor: "venice", modo: MODO_POR_DEFECTO, nivel: null, modeloOllama: null, modeloVenice: e.modelo };
}

const CLAVE_CEREBRO = "remi.pensar.cerebro";
const CLAVE_NIVEL = "remi.pensar.nivel";

/**
 * La elección guardada. Si no hay (primera vez con 3c), sale de lo que
 * quedó de antes: motor + modo + nivel. Venice no se hereda nunca: es pago
 * y se elige a mano cada vez (decisión de 2i, se mantiene).
 */
export function obtenerCerebro(): EleccionCerebro {
  const guardado = deValor(leer(CLAVE_CEREBRO));
  if (guardado) return guardado.motor === "venice" ? CEREBRO_POR_DEFECTO : guardado;
  const motor = leer(CLAVE_MOTOR);
  if (motor === "ollama") return { motor: "ollama", modelo: "gemma3:4b" };
  const modo = leer(CLAVE_MODO);
  const modelo: ModeloClaude = modo === "rapido" ? "haiku" : modo === "inteligente" ? "opus" : "sonnet";
  const nivel = leer(CLAVE_NIVEL);
  return {
    motor: "claude",
    modelo,
    nivel: (NIVELES as readonly string[]).includes(nivel ?? "") ? (nivel as Nivel) : modelo === "opus" ? "medio" : "bajo",
  };
}

export function fijarCerebro(e: EleccionCerebro): void {
  guardar(CLAVE_CEREBRO, valorDe(e));
}

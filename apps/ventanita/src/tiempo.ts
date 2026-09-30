// Ley 1 (ceguera temporal) en reposo: cuánto hace de la última vez que
// hablaste con Remi, relativo y calmo — nunca un reloj. Se persiste en
// localStorage para que sobreviva a cerrar la ventanita.
const CLAVE_ULTIMA_INTERACCION = "remi.ultima_interaccion";

export function registrarInteraccion(ahora: number = Date.now()): void {
  try {
    localStorage.setItem(CLAVE_ULTIMA_INTERACCION, String(ahora));
  } catch {
    // Sin localStorage no se recuerda entre sesiones; no rompe nada.
  }
}

export function ultimaInteraccion(): number | null {
  try {
    const valor = Number(localStorage.getItem(CLAVE_ULTIMA_INTERACCION));
    return Number.isFinite(valor) && valor > 0 ? valor : null;
  } catch {
    return null;
  }
}

// «40 min» · «1 h 40» · «3 h». El formato de la ley 1, el mismo que usa el
// núcleo al cerrar un bloque (servidor.py, formatear_duracion).
export function formatearDuracion(minutos: number): string {
  const enteros = Math.max(0, Math.floor(minutos));
  if (enteros < 60) return `${enteros} min`;
  const horas = Math.floor(enteros / 60);
  const resto = enteros % 60;
  return resto > 0 ? `${horas} h ${String(resto).padStart(2, "0")}` : `${horas} h`;
}

// Reloj de una línea bajo el chat (3f · 4): «0:31» — h:mm compacto, en
// `num` (Geist Mono). Mismo dato que formatearDuracion, otra forma: acá
// cabe en una línea junto a «la última vez».
export function formatearReloj(totalMinutos: number): string {
  const enteros = Math.max(0, Math.floor(totalMinutos));
  const horas = Math.floor(enteros / 60);
  const minutos = enteros % 60;
  return `${horas}:${String(minutos).padStart(2, "0")}`;
}

// «recién» · «hace 6 min» · «hace 1 h 40» · «hace 3 h» · «hace 2 d».
export function formatearHace(desde: number, ahora: number = Date.now()): string {
  const minutos = Math.max(0, Math.floor((ahora - desde) / 60000));
  if (minutos < 1) return "recién";
  const horas = Math.floor(minutos / 60);
  if (horas >= 24) return `hace ${Math.floor(horas / 24)} d`;
  return `hace ${formatearDuracion(minutos)}`;
}

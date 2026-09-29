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

// «recién» · «hace 6 min» · «hace 1 h 40» · «hace 3 h» · «hace 2 d».
// Mismo formato que la ley 1 usa al planear («1 h 40»).
export function formatearHace(desde: number, ahora: number = Date.now()): string {
  const minutos = Math.max(0, Math.floor((ahora - desde) / 60000));
  if (minutos < 1) return "recién";
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) {
    const resto = minutos % 60;
    return resto > 0 ? `hace ${horas} h ${String(resto).padStart(2, "0")}` : `hace ${horas} h`;
  }
  return `hace ${Math.floor(horas / 24)} d`;
}

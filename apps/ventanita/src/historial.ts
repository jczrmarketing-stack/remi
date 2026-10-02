// El cajón del historial (T7): cuándo fue cada conversación, en palabras
// calmadas. Nada de «hace N días sin…»: solo dónde quedó, sin contar nada.

const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function dosDigitos(n: number): string {
  return String(n).padStart(2, "0");
}

function inicioDelDia(fecha: Date): number {
  return new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime();
}

export function etiquetaDeFecha(ultimoIso: string, ahoraMs: number): string {
  const fecha = new Date(ultimoIso);
  if (Number.isNaN(fecha.getTime())) return "";
  const dias = Math.round((inicioDelDia(new Date(ahoraMs)) - inicioDelDia(fecha)) / 86_400_000);
  const hora = `${dosDigitos(fecha.getHours())}:${dosDigitos(fecha.getMinutes())}`;
  if (dias <= 0) return `hoy · ${hora}`;
  if (dias === 1) return `ayer · ${hora}`;
  if (dias < 7) return `${DIAS[fecha.getDay()]} · ${hora}`;
  return `${fecha.getDate()} ${MESES[fecha.getMonth()]}`;
}

// Formatos del panel que no son de una sola pantalla: horas, fechas cortas,
// nombres de proyecto y la frase de la plata. Todo texto fijo, sin IA.
import type { Plata, RevisionFria } from "@/lib/nucleo";

const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const DIAS_LARGOS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function moneda(valor: number): string {
  return `$${Math.round(valor).toLocaleString("es-CO")}`;
}

// «08:00» → «8:00», «15:00» → «3:00 p». La mañana va sin marca; la tarde
// lleva una «p»: así se lee de un vistazo qué queda para después de comer.
export function formatoHora(hora: string): string {
  const [h, m] = hora.split(":").map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return hora;
  const minutos = String(m).padStart(2, "0");
  if (h < 12) return `${h === 0 ? 12 : h}:${minutos}`;
  return `${h === 12 ? 12 : h - 12}:${minutos} p`;
}

// B4: la hora del reloj (local), de un datetime ISO completo con hora real
// — a diferencia de `formatoHora`, que recibe «HH:MM» ya sueltos.
export function horaDeISO(iso: string): string {
  const fecha = new Date(iso);
  const h = String(fecha.getHours()).padStart(2, "0");
  const m = String(fecha.getMinutes()).padStart(2, "0");
  return formatoHora(`${h}:${m}`);
}

// Las fechas de tareas y entregas se guardan a las 00:00 UTC del día que
// nombran: el día es el de su parte de fecha, no el de la zona del teléfono.
function diaDe(iso: string): Date {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function diasHasta(iso: string, ahora: Date): number {
  const hoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());
  return Math.round((diaDe(iso).getTime() - hoy.getTime()) / 86400000);
}

// «hoy», «mañana», «vie 3» si cae en los próximos días, «18 oct» si no.
export function fechaCorta(iso: string, ahora: Date = new Date()): string {
  const faltan = diasHasta(iso, ahora);
  const dia = diaDe(iso);
  if (faltan === 0) return "hoy";
  if (faltan === 1) return "mañana";
  if (faltan > 1 && faltan < 7) return `${DIAS[dia.getDay()]} ${dia.getDate()}`;
  return `${dia.getDate()} ${MESES[dia.getMonth()]}`;
}

// «vence hoy», «vence mañana», «vence el viernes», «vence el 18 de oct».
export function venceTexto(iso: string, ahora: Date = new Date()): string {
  const faltan = diasHasta(iso, ahora);
  const dia = diaDe(iso);
  if (faltan === 0) return "vence hoy";
  if (faltan === 1) return "vence mañana";
  if (faltan > 1 && faltan < 7) return `vence el ${DIAS_LARGOS[dia.getDay()]}`;
  return `vence el ${dia.getDate()} de ${MESES[dia.getMonth()]}`;
}

// «1 oct»: el día de un instante real (cuándo se tocó un libro), en la hora
// del que mira.
export function diaDelInstante(iso: string): string {
  const dia = new Date(iso);
  if (Number.isNaN(dia.getTime())) return "";
  return `${dia.getDate()} ${MESES[dia.getMonth()]}`;
}

// «Pago antes de arrancar» → «pago antes de arrancar»: para decirlo dentro
// de una frase («Seguir con pago antes de arrancar»).
export function enFrase(texto: string): string {
  return texto.charAt(0).toLowerCase() + texto.slice(1);
}

export function diaDeLaSemana(ahora: Date = new Date()): string {
  const dia = DIAS_LARGOS[ahora.getDay()];
  return dia.charAt(0).toUpperCase() + dia.slice(1);
}

// «UpVisuals — cliente Alfonso» → «UpVisuals»: el título del libro trae una
// explicación después de la raya; en una etiqueta alcanza con el nombre.
export function nombreCorto(titulo: string): string {
  return titulo.split(/\s[—–-]\s/)[0].trim() || titulo;
}

// «viernes 4:30 p».
export function cuandoEsLaRevision(revision: RevisionFria | null): string | null {
  if (!revision) return null;
  return `${revision.dia} ${formatoHora(revision.hora)}`;
}

// Debajo de la brecha, siempre una acción con número — nunca solo el
// diagnóstico (Biblia, Parte VII). Con una entrega pendiente, cobrarla es
// la acción concreta; sin ninguna, el tamaño de entrega que haría falta.
export function accionDeLaBrecha(plata: Plata): string {
  if (plata.proximo) {
    const cierra = Math.min(plata.proximo.monto, plata.mes.faltan);
    return `Cobrar la de ${plata.proximo.cliente} cierra ${moneda(cierra)}.`;
  }
  return `Para cerrar la brecha: una entrega de ${moneda(plata.mes.faltan)}.`;
}

// La misma acción, en la línea de la plata de la semana: corta y en minúscula.
export function accionCorta(plata: Plata): string {
  if (plata.proximo) {
    const cierra = Math.min(plata.proximo.monto, plata.mes.faltan);
    return `cobrar la de ${plata.proximo.cliente} cierra ${moneda(cierra)}`;
  }
  return `una entrega de ${moneda(plata.mes.faltan)} la cierra`;
}

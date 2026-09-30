// Todo lo que pide la pantalla Hoy, en una sola carga: el bloque abierto
// (si hay), la plata de la semana, las ideas frías y el nudge pendiente.
import { nucleo, type Camino, type IdeaBandeja, type Plata, type TareaConHistorial } from "@/lib/nucleo";
import type { Nudge } from "@/contratos";

export type BloqueAbierto = {
  tarea: TareaConHistorial;
  inicioISO: string;
  tema: string | null;
  camino: Camino | null;
};

export type DatosHoy = {
  bloque: BloqueAbierto | null;
  demasHoy: TareaConHistorial[];
  plata: Plata;
  ideasFrias: IdeaBandeja[];
  nudge: Nudge | null;
};

export async function cargarHoy(): Promise<DatosHoy> {
  const [tareas, plata, bandeja, nudge] = await Promise.all([
    nucleo.hoy(),
    nucleo.plata(),
    nucleo.bandeja(),
    nucleo.nudgePendiente(),
  ]);

  const conBloqueAbierto = tareas.find((t) => t.sesiones.some((s) => s.fin === null));
  let bloque: BloqueAbierto | null = null;

  if (conBloqueAbierto) {
    const sesion = conBloqueAbierto.sesiones.find((s) => s.fin === null)!;
    const tema = sesion.app_contexto ?? null;
    const camino = tema ? await nucleo.camino(tema) : null;
    bloque = { tarea: conBloqueAbierto, inicioISO: sesion.inicio, tema, camino };
  }

  const demasHoy = tareas.filter((t) => t !== conBloqueAbierto).slice(0, 3);
  const ideasFrias = bandeja.filter((f) => f.fria);

  return { bloque, demasHoy, plata, ideasFrias, nudge };
}

export function minutosDesde(iso: string, ahoraMs: number): number {
  return Math.max(0, Math.round((ahoraMs - new Date(iso).getTime()) / 60000));
}

export function formatoDuracion(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return m ? `${h} h ${String(m).padStart(2, "0")}` : `${h} h`;
}

export function formatoMoneda(valor: number): string {
  return `$${Math.round(valor).toLocaleString("es-CO")}`;
}

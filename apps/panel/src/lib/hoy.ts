// Todo lo que pide la pantalla Hoy, en una sola carga: el bloque abierto
// (si hay) con su libro, la plata de la semana, la agenda (mañana y lo que
// vence), las ideas frías, el nudge pendiente y, si no hay nada abierto, lo
// que Remi propone por el orden del líder.
import {
  nucleo,
  type AgendaDeHoy,
  type AlDia,
  type Camino,
  type EntregaCercana,
  type IdeaBandeja,
  type Libro,
  type LibroDetalle,
  type Plata,
  type TareaConHistorial,
} from "@/lib/nucleo";
import { faseDe, hitoDe, liderDe } from "@/lib/lider";
import { nombreCorto } from "@/lib/formato";
import type { Nudge } from "@/contratos";

export type BloqueAbierto = {
  tarea: TareaConHistorial;
  inicioISO: string;
  tema: string | null;
  camino: Camino | null;
  // El libro del bloque: de acá salen el proyecto, la fase, el hito y la
  // entrega. null si el bloque no es de ningún libro.
  libro: LibroDetalle | null;
};

// Lo que Remi propone cuando no hay nada abierto.
export type Propuesta = {
  tema: string | null;
  proyecto: string;
  // El título del bloque que se abre al tocar «Empezar con eso».
  titulo: string;
  hito: { n: number; total: number; texto: string } | null;
  fase: string | null;
  entrega: EntregaCercana | null;
};

export type DatosHoy = {
  bloque: BloqueAbierto | null;
  demasHoy: TareaConHistorial[];
  plata: Plata;
  agenda: AgendaDeHoy;
  ideasFrias: IdeaBandeja[];
  nudge: Nudge | null;
  propuesta: Propuesta | null;
  // B2/B4: Al día — se actualiza sola, sin que Juan Camilo marque nada.
  alDia: AlDia | null;
};

// Por el orden del líder: primero la entrega con dinero más cercana; sin
// ninguna, el hito encendido del proyecto que más importa — los de cliente
// antes que los propios, y entre iguales el que se tocó hace menos.
export function proponer(libros: Libro[], plata: Plata): Propuesta | null {
  const lider = liderDe(libros);
  if (lider && lider.entrega_cercana) {
    return {
      tema: lider.tema,
      proyecto: nombreCorto(lider.titulo),
      titulo: `Entrega de ${lider.entrega_cercana.cliente}`,
      hito: hitoDe(lider),
      fase: faseDe(lider),
      entrega: lider.entrega_cercana,
    };
  }
  if (plata.proximo) {
    // Una entrega con dinero que no es de ningún libro: igual va primero.
    return {
      tema: null,
      proyecto: plata.proximo.cliente,
      titulo: `Entrega de ${plata.proximo.cliente}`,
      hito: null,
      fase: null,
      entrega: plata.proximo,
    };
  }
  const conHito = libros
    .filter((l) => hitoDe(l) !== null)
    .sort((a, b) => {
      const cliente = Number(b.tipo === "cliente") - Number(a.tipo === "cliente");
      if (cliente !== 0) return cliente;
      return new Date(b.ultimo_estado_en).getTime() - new Date(a.ultimo_estado_en).getTime();
    });
  const primero = conHito[0];
  if (!primero) return null;
  const hito = hitoDe(primero)!;
  const proyecto = nombreCorto(primero.titulo);
  return { tema: primero.tema, proyecto, titulo: `${proyecto} · ${hito.texto}`, hito, fase: faseDe(primero), entrega: null };
}

export async function cargarHoy(): Promise<DatosHoy> {
  const [tareas, plata, bandeja, nudge, agenda, alDia] = await Promise.all([
    nucleo.hoy(),
    nucleo.plata(),
    nucleo.bandeja(),
    nucleo.nudgePendiente(),
    nucleo.agenda(),
    nucleo.alDia(),
  ]);

  const conBloqueAbierto = tareas.find((t) => t.sesiones.some((s) => s.fin === null));
  let bloque: BloqueAbierto | null = null;
  let propuesta: Propuesta | null = null;

  if (conBloqueAbierto) {
    const sesion = conBloqueAbierto.sesiones.find((s) => s.fin === null)!;
    const tema = sesion.app_contexto ?? null;
    const libro = tema ? await nucleo.libro(tema) : null;
    const siguiente = libro?.hitos.find((h) => !h.hecho) ?? null;
    const camino = libro && libro.hitos.length > 0 ? { hitos: libro.hitos, siguiente } : null;
    bloque = { tarea: conBloqueAbierto, inicioISO: sesion.inicio, tema, camino, libro };
  } else {
    propuesta = proponer(await nucleo.libros(), plata);
  }

  const demasHoy = tareas.filter((t) => t !== conBloqueAbierto).slice(0, 3);
  const ideasFrias = bandeja.filter((f) => f.fria);

  return { bloque, demasHoy, plata, agenda, ideasFrias, nudge, propuesta, alDia };
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

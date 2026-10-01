// El orden fijo del líder (Biblia, Parte VII): decide qué va primero en
// Hoy, en Proyectos y en «Nada abierto». Nunca se negocia por ánimo.
//   1) el libro con la entrega con dinero más cercana (uno solo),
//   2) el del bloque abierto, si no es ya el líder,
//   3) el resto, por fecha de último Estado (lo más reciente primero).
import type { Libro } from "@/lib/nucleo";

export type Escalon = 1 | 2 | 3;

export function liderDe(libros: Libro[]): Libro | null {
  const conEntrega = libros.filter((l) => l.entrega_cercana);
  if (conEntrega.length === 0) return null;
  return conEntrega.reduce((a, b) =>
    new Date(a.entrega_cercana!.fecha).getTime() <= new Date(b.entrega_cercana!.fecha).getTime() ? a : b,
  );
}

export function escalonDe(libro: Libro, lider: Libro | null, abiertoTema: string | null): Escalon {
  if (lider && libro.tema === lider.tema) return 1;
  if (libro.tema === abiertoTema) return 2;
  return 3;
}

export function ordenDelLider(libros: Libro[], abiertoTema: string | null): Libro[] {
  const lider = liderDe(libros);
  return [...libros].sort((a, b) => {
    const diferencia = escalonDe(a, lider, abiertoTema) - escalonDe(b, lider, abiertoTema);
    if (diferencia !== 0) return diferencia;
    return new Date(b.ultimo_estado_en).getTime() - new Date(a.ultimo_estado_en).getTime();
  });
}

// El paso que está encendido en el camino de un libro: «hito 5 de 10».
export function hitoDe(libro: Pick<Libro, "hitos">): { n: number; total: number; texto: string } | null {
  const total = libro.hitos.length;
  const indice = libro.hitos.findIndex((h) => !h.hecho);
  if (total === 0 || indice < 0) return null;
  return { n: indice + 1, total, texto: libro.hitos[indice].texto };
}

// «Fase 1»: el nombre que el libro le dio a la fase en la que está.
export function faseDe(libro: Pick<Libro, "fases" | "fase_actual_n">): string | null {
  if (!libro.fase_actual_n) return null;
  return libro.fases[libro.fase_actual_n - 1]?.nombre || `Fase ${libro.fase_actual_n}`;
}

// Nudges dentro del chat (3f · 6): «Listo» / «Ahora no», Enter/Escape, sin
// sonido — ley 5 (cuerpo primero) siempre con salida amable que nunca se
// registra como fallo. El backend (/nudges/pendiente, /nudges/{id}/respuesta)
// puede no existir todavía: esto no rompe si /nudges/pendiente da 404.
export const MS_ENTRE_CONSULTAS_NUDGE = 5 * 60 * 1000;

export type RespuestaNudge = "listo" | "ahora_no";

/** Enter → listo, Escape → ahora no; cualquier otra tecla no responde nada. */
export function respuestaDeTecla(tecla: string): RespuestaNudge | null {
  if (tecla === "Enter") return "listo";
  if (tecla === "Escape") return "ahora_no";
  return null;
}

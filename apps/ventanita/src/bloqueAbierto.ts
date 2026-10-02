import type { Sesion, Tarea } from "./contratos";

// Forma G (T2): «agenda», «cobro» y «entrega» nunca llevan `sesion` — así
// que un mensaje de esos tipos nunca prende el Reloj, aunque sí traiga
// `tarea` (el caso de «agenda», que crea la tarea sin abrir bloque).
export function debeMostrarReloj(
  tarea: Tarea | null | undefined,
  sesion: Sesion | null | undefined,
): boolean {
  return tarea != null && tarea.estado === "hoy" && sesion != null;
}

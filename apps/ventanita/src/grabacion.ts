// Revisión del 3-oct: minimizar la ventanita mientras escuchaba la mandaba a
// reposo pero el micrófono seguía grabando por detrás. Cada click siguiente
// fallaba con «ya había una grabación activa» y el micrófono quedaba prendido
// sin que Remi escuchara (la Biblia: micrófono solo en «escuchando»).

/** El error de Rust cuando quedó una grabación vieja colgada. */
export function quedoUnaGrabacionColgada(error: unknown): boolean {
  const texto = error instanceof Error ? error.message : String(error ?? "");
  return texto.includes("ya había una grabación activa");
}

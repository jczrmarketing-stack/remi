// V3 (2/10/2026): la respuesta llega en frases, a medida que el motor la
// escribe. El núcleo manda NDJSON por POST /mensaje/stream: una línea
// {"frase": "...", "voz": "..."|null} por oración completa y al final
// {"fin": {...la respuesta entera, igual que /mensaje...}}. Acá está lo que
// se puede probar sin red: partir el chorro en líneas y leer cada una.

export interface FraseEnVivo {
  // Lo que se ve en el chat, tal cual lo escribió el modelo.
  frase: string;
  // Lo que se dice: la frase sin markdown, o null si ya no se dice (el
  // núcleo solo pone voz a las primeras tres, como para_hablar).
  voz: string | null;
}

export type LineaEnVivo = { tipo: "frase"; frase: FraseEnVivo } | { tipo: "fin"; fin: unknown };

/**
 * Parte lo que llegó en líneas enteras. Devuelve las líneas completas y lo
 * que quedó sin cerrar (una línea a medias espera al próximo trozo).
 */
export function partirLineas(acumulado: string): { lineas: string[]; resto: string } {
  const partes = acumulado.split("\n");
  const resto = partes.pop() ?? "";
  return { lineas: partes.filter((l) => l.trim() !== ""), resto };
}

/** Lee una línea del núcleo. null si no es ninguna de las dos formas. */
export function leerLinea(linea: string): LineaEnVivo | null {
  let datos: unknown;
  try {
    datos = JSON.parse(linea);
  } catch {
    return null;
  }
  if (!datos || typeof datos !== "object") return null;
  const objeto = datos as Record<string, unknown>;
  if ("fin" in objeto && objeto.fin && typeof objeto.fin === "object") {
    return { tipo: "fin", fin: objeto.fin };
  }
  if (typeof objeto.frase === "string") {
    const voz = typeof objeto.voz === "string" && objeto.voz.trim() !== "" ? objeto.voz : null;
    return { tipo: "frase", frase: { frase: objeto.frase, voz } };
  }
  return null;
}

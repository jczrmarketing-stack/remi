// Lectura biónica (Biblia v3.1, Parte II «Lectura»): el comienzo de cada
// palabra en grueso (el ancla) y el resto más claro. El ojo salta de ancla
// en ancla y el cerebro completa la palabra. Pura: se prueba sin DOM.

/** Cuántas letras van en el ancla: 1–3 → 1 · 4 → 2 · 5+ → la mitad (impar: mitad + 1). */
export function largoAncla(letras: number): number {
  if (letras <= 0) return 0;
  if (letras <= 3) return 1;
  if (letras === 4) return 2;
  return Math.ceil(letras / 2);
}

export type TrozoBionico = { tipo: "ancla" | "resto" | "entre"; texto: string };

// Una palabra: letras y números (con tildes, ñ y diéresis). Lo demás —
// espacios, signos, emojis— pasa tal cual.
const PALABRA = /[\p{L}\p{M}\p{N}]+/gu;

export function partirBionica(texto: string): TrozoBionico[] {
  const trozos: TrozoBionico[] = [];
  let desde = 0;
  for (const encontrado of texto.matchAll(PALABRA)) {
    const inicio = encontrado.index ?? 0;
    if (inicio > desde) trozos.push({ tipo: "entre", texto: texto.slice(desde, inicio) });
    // Por letras visibles, no por unidades de UTF-16: «ñandú» son 5.
    const letras = Array.from(encontrado[0]);
    const corte = largoAncla(letras.length);
    trozos.push({ tipo: "ancla", texto: letras.slice(0, corte).join("") });
    if (corte < letras.length) trozos.push({ tipo: "resto", texto: letras.slice(corte).join("") });
    desde = inicio + encontrado[0].length;
  }
  if (desde < texto.length) trozos.push({ tipo: "entre", texto: texto.slice(desde) });
  return trozos;
}

/**
 * La intensidad del deslizador (0 = suave, 1 = fuerte) a las perillas de
 * la Biblia: peso del ancla 700–800, el resto al 85 %–55 % de la tinta, e
 * interlineado 1,6–1,8.
 */
export function perillasBionica(intensidad: number): { pesoAncla: number; tintaResto: number; interlineado: number } {
  const i = Math.min(1, Math.max(0, intensidad));
  return {
    pesoAncla: Math.round(700 + 100 * i),
    tintaResto: Math.round(85 - 30 * i),
    interlineado: Math.round((1.6 + 0.2 * i) * 100) / 100,
  };
}

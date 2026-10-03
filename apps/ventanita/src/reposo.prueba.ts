import { describe, expect, it } from "vitest";
import { MS_ISLA_VISIBLE, TAMANO_ISLA_NUDGE, mostrarTextoIsla, TAMANO_ISLA_CON_TEXTO, TAMANO_ISLA_MINIMA, tamanoIsla } from "./reposo";

describe("mostrarTextoIsla", () => {
  it("sin contenido nunca muestra texto, ni con el mouse encima", () => {
    expect(mostrarTextoIsla(0, false, false)).toBe(false);
    expect(mostrarTextoIsla(0, true, false)).toBe(false);
  });

  it("con contenido, se muestra apenas se vuelve a reposo", () => {
    expect(mostrarTextoIsla(0, false, true)).toBe(true);
  });

  it("con contenido, se muestra hasta justo antes de los 4 s", () => {
    expect(mostrarTextoIsla(MS_ISLA_VISIBLE - 1, false, true)).toBe(true);
  });

  it("con contenido, se encoge a partir de los 4 s", () => {
    expect(mostrarTextoIsla(MS_ISLA_VISIBLE, false, true)).toBe(false);
    expect(mostrarTextoIsla(MS_ISLA_VISIBLE + 5000, false, true)).toBe(false);
  });

  it("con el mouse encima se vuelve a mostrar aunque hayan pasado los 4 s", () => {
    expect(mostrarTextoIsla(MS_ISLA_VISIBLE + 5000, true, true)).toBe(true);
  });
});

describe("tamanoIsla", () => {
  it("72×72 sin texto: el cuadradito", () => {
    expect(tamanoIsla(false)).toEqual(TAMANO_ISLA_MINIMA);
    expect(TAMANO_ISLA_MINIMA).toEqual({ width: 72, height: 72 });
  });

  it("200×72 con texto: crece a lo ancho, no a lo alto", () => {
    expect(tamanoIsla(true)).toEqual(TAMANO_ISLA_CON_TEXTO);
    expect(TAMANO_ISLA_CON_TEXTO).toEqual({ width: 200, height: 72 });
  });
});

describe("tamanoIsla con nudge", () => {
  it("el nudge manda sobre el texto de la isla", () => {
    expect(tamanoIsla(true, true)).toEqual(TAMANO_ISLA_NUDGE);
    expect(tamanoIsla(false, true)).toEqual(TAMANO_ISLA_NUDGE);
  });
});

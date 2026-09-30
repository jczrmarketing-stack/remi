import { describe, expect, it } from "vitest";
import { largoAncla, partirBionica, perillasBionica } from "./bionica";

describe("lectura biónica", () => {
  it("el ancla sigue la regla de la Biblia", () => {
    expect([1, 2, 3, 4, 5, 6, 7, 8, 9].map(largoAncla)).toEqual([1, 1, 1, 2, 3, 3, 4, 4, 5]);
  });

  it("parte una frase real sin perder nada", () => {
    const frase = "Hoy solo esto: la tarjeta.";
    const trozos = partirBionica(frase);
    expect(trozos.map((t) => t.texto).join("")).toBe(frase);
    expect(trozos.filter((t) => t.tipo === "ancla").map((t) => t.texto)).toEqual(["H", "so", "es", "l", "tarj"]);
  });

  it("cuenta letras con tildes y ñ, no unidades de código", () => {
    expect(partirBionica("ñandú")).toEqual([
      { tipo: "ancla", texto: "ñan" },
      { tipo: "resto", texto: "dú" },
    ]);
    expect(partirBionica("¿Qué?")[1]).toEqual({ tipo: "ancla", texto: "Q" });
  });

  it("la intensidad va de suave a fuerte", () => {
    expect(perillasBionica(0)).toEqual({ pesoAncla: 700, tintaResto: 85, interlineado: 1.6 });
    expect(perillasBionica(1)).toEqual({ pesoAncla: 800, tintaResto: 55, interlineado: 1.8 });
    expect(perillasBionica(7)).toEqual(perillasBionica(1));
  });
});

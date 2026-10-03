import { describe, expect, it } from "vitest";
import { dividirEnFrases } from "./voz";

describe("dividirEnFrases", () => {
  it("parte en frases y pega las muy cortas a la siguiente", () => {
    expect(dividirEnFrases("Ajá. Hoy solo esto: la tarjeta. Cinco minutos y ya.")).toEqual([
      "Ajá. Hoy solo esto: la tarjeta.",
      "Cinco minutos y ya.",
    ]);
  });

  it("una frase sola queda entera", () => {
    expect(dividirEnFrases("Hoy solo la tarjeta, cinco minutos.")).toEqual(["Hoy solo la tarjeta, cinco minutos."]);
    expect(dividirEnFrases("  ")).toEqual([]);
  });

  it("la cola corta se pega a la anterior", () => {
    expect(dividirEnFrases("Esto es una frase larga de verdad. Listo.")).toEqual([
      "Esto es una frase larga de verdad. Listo.",
    ]);
  });
});

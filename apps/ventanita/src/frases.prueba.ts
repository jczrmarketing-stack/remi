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

describe("repartirVelocidad", () => {
  it("hasta 1,5× la hace el modelo; el 2× completa estirando solo el resto", async () => {
    const { repartirVelocidad } = await import("./voz");
    expect(repartirVelocidad(1)).toEqual({ modelo: 1, reproductor: 1 });
    expect(repartirVelocidad(1.5)).toEqual({ modelo: 1.5, reproductor: 1 });
    const dos = repartirVelocidad(2);
    expect(dos.modelo).toBe(1.5);
    expect(dos.modelo * dos.reproductor).toBeCloseTo(2);
  });
});

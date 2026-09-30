import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { limitarTamano, posicionQueEntra } from "./ventana";

const PANTALLA = { x: 0, y: 25, width: 1440, height: 875 };

describe("el tamaño de la ventana", () => {
  it("nunca menos de 360×240 ni más del 90 % de la pantalla", () => {
    expect(limitarTamano({ width: 100, height: 100 }, PANTALLA)).toEqual({ width: 360, height: 240 });
    expect(limitarTamano({ width: 5000, height: 5000 }, PANTALLA)).toEqual({ width: 1296, height: 787 });
    expect(limitarTamano({ width: 420, height: 520 }, PANTALLA)).toEqual({ width: 420, height: 520 });
  });

  it("abrir desde una píldora pegada abajo a la derecha corre la ventana para que entre", () => {
    expect(posicionQueEntra({ x: 1380, y: 850 }, { width: 420, height: 520 }, PANTALLA)).toEqual({ x: 1020, y: 380 });
    expect(posicionQueEntra({ x: 100, y: 100 }, { width: 420, height: 520 }, PANTALLA)).toEqual({ x: 100, y: 100 });
  });
});

describe("se acuerda entre aperturas", () => {
  beforeEach(() => {
    const datos = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => datos.get(k) ?? null,
      setItem: (k: string, v: string) => void datos.set(k, v),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("tamaño y posición", async () => {
    const v = await import("./ventana");
    expect(v.obtenerTamanoChat()).toEqual({ width: 420, height: 520 });
    expect(v.obtenerPosicion()).toBeNull();
    v.fijarTamanoChat({ width: 600.4, height: 700 });
    v.fijarPosicion({ x: 10, y: 40 });
    expect(v.obtenerTamanoChat()).toEqual({ width: 600, height: 700 });
    expect(v.obtenerPosicion()).toEqual({ x: 10, y: 40 });
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  const datos = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => datos.get(k) ?? null,
    setItem: (k: string, v: string) => void datos.set(k, v),
  });
});
afterEach(() => vi.unstubAllGlobals());

describe("la preferencia de lectura", () => {
  it("por defecto: Noche, sin biónica", async () => {
    const { obtenerLectura } = await import("./lectura");
    expect(obtenerLectura()).toEqual({ tema: "noche", bionica: false, intensidad: 0.5 });
  });

  it("se guarda y vuelve igual; lo raro se corrige", async () => {
    const { fijarLectura, obtenerLectura } = await import("./lectura");
    fijarLectura({ tema: "claro", bionica: true, intensidad: 0.9 });
    expect(obtenerLectura()).toEqual({ tema: "claro", bionica: true, intensidad: 0.9 });
    localStorage.setItem("remi.lectura", JSON.stringify({ tema: "rosa", bionica: "sí", intensidad: 9 }));
    expect(obtenerLectura()).toEqual({ tema: "noche", bionica: false, intensidad: 1 });
  });
});

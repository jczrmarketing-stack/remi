import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Un localStorage de mentira, suficiente para las preferencias.
function almacenFalso() {
  const datos = new Map<string, string>();
  return {
    getItem: (k: string) => datos.get(k) ?? null,
    setItem: (k: string, v: string) => void datos.set(k, v),
  };
}

beforeEach(() => vi.stubGlobal("localStorage", almacenFalso()));
afterEach(() => vi.unstubAllGlobals());

describe("el motor guardado", () => {
  it("por defecto es Claude", async () => {
    const { obtenerMotor } = await import("./preferencias");
    expect(obtenerMotor()).toBe("claude");
  });

  it("Ollama y Claude se heredan entre sesiones", async () => {
    const { fijarMotor, obtenerMotor } = await import("./preferencias");
    fijarMotor("ollama");
    expect(obtenerMotor()).toBe("ollama");
  });

  it("Venice es pago: nunca vuelve por arrastre de una preferencia vieja", async () => {
    const { fijarMotor, obtenerMotor } = await import("./preferencias");
    fijarMotor("venice");
    expect(obtenerMotor()).toBe("claude");
  });
});

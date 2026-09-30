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

describe("el chip de modelo", () => {
  it("cada modelo va y vuelve igual", async () => {
    const { CEREBROS, cerebroDe, eleccionDe } = await import("./preferencias");
    for (const c of CEREBROS) expect(cerebroDe(eleccionDe(c))).toBe(c);
  });

  it("lo guardado de antes se lee como su modelo", async () => {
    const { cerebroDe } = await import("./preferencias");
    expect(cerebroDe({ motor: "claude", modo: "inteligente", sinPensar: false })).toBe("opus");
    expect(cerebroDe({ motor: "ollama", modo: "equilibrio", sinPensar: false })).toBe("ollama");
    expect(cerebroDe({ motor: "claude", modo: "rapido", sinPensar: true })).toBe("sin-pensar");
  });

  it("solo Anthropic tiene nivel, y Opus arranca en medio", async () => {
    const { tieneNivel, nivelPorDefecto } = await import("./preferencias");
    expect(tieneNivel("venice")).toBe(false);
    expect(tieneNivel("haiku")).toBe(true);
    expect(nivelPorDefecto("opus")).toBe("medio");
    expect(nivelPorDefecto("sonnet")).toBe("bajo");
  });
});

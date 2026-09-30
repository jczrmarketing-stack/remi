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

describe("el chip de cerebro", () => {
  it("cada elección va y vuelve igual por el <select>", async () => {
    const { deValor, valorDe } = await import("./preferencias");
    for (const e of [
      { motor: "claude", modelo: "opus", nivel: "extra" },
      { motor: "ollama", modelo: "gemma3:4b" },
      { motor: "venice" },
    ] as const) {
      expect(deValor(valorDe(e))).toEqual(e);
    }
    expect(deValor("claude:gpt:alto")).toBeNull();
  });

  it("el chip dice «Sonnet · medio», y extra se lee máx", async () => {
    const { etiquetaDe } = await import("./preferencias");
    expect(etiquetaDe({ motor: "claude", modelo: "sonnet", nivel: "medio" })).toBe("Sonnet · medio");
    expect(etiquetaDe({ motor: "claude", modelo: "opus", nivel: "extra" })).toBe("Opus · máx");
    expect(etiquetaDe({ motor: "ollama", modelo: "gemma3:4b" })).toBe("gemma3:4b");
  });

  it("se recuerda la elección, salvo Venice (pago)", async () => {
    const { fijarCerebro, obtenerCerebro } = await import("./preferencias");
    fijarCerebro({ motor: "claude", modelo: "haiku", nivel: "alto" });
    expect(obtenerCerebro()).toEqual({ motor: "claude", modelo: "haiku", nivel: "alto" });
    fijarCerebro({ motor: "venice" });
    expect(obtenerCerebro()).toEqual({ motor: "claude", modelo: "sonnet", nivel: "bajo" });
  });

  it("sin elección guardada, sale de lo de antes", async () => {
    localStorage.setItem("remi.pensar.modo", "inteligente");
    const { obtenerCerebro } = await import("./preferencias");
    expect(obtenerCerebro()).toEqual({ motor: "claude", modelo: "opus", nivel: "medio" });
  });

  it("lo que viaja: Sonnet medio va como equilibrio + medio; Ollama con su modelo", async () => {
    const { paraEnviar } = await import("./preferencias");
    expect(paraEnviar({ motor: "claude", modelo: "sonnet", nivel: "medio" })).toEqual({
      motor: "claude",
      modo: "equilibrio",
      nivel: "medio",
      modeloOllama: null,
    });
    expect(paraEnviar({ motor: "ollama", modelo: "llama3" }).modeloOllama).toBe("llama3");
  });
});

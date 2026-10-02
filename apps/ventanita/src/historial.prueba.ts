import { describe, expect, it } from "vitest";
import { etiquetaDeFecha } from "./historial";

const ahora = new Date(2026, 9, 1, 20, 0).getTime();

describe("etiquetaDeFecha", () => {
  it("hoy lleva la hora", () => {
    expect(etiquetaDeFecha(new Date(2026, 9, 1, 9, 5).toISOString(), ahora)).toBe("hoy · 09:05");
  });
  it("ayer", () => {
    expect(etiquetaDeFecha(new Date(2026, 8, 30, 23, 40).toISOString(), ahora)).toBe("ayer · 23:40");
  });
  it("esta semana, el día", () => {
    expect(etiquetaDeFecha(new Date(2026, 8, 27, 10, 0).toISOString(), ahora)).toBe("dom · 10:00");
  });
  it("más viejo, la fecha", () => {
    expect(etiquetaDeFecha(new Date(2026, 8, 3, 10, 0).toISOString(), ahora)).toBe("3 sep");
  });
  it("una fecha rota no revienta", () => {
    expect(etiquetaDeFecha("nada", ahora)).toBe("");
  });
});

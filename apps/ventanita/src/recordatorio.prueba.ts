import { describe, expect, it } from "vitest";
import { MS_ENTRE_RECORDATORIOS, tocaRecordar } from "./recordatorio";

describe("el recordatorio del motor", () => {
  it("toca a la media hora, en reposo", () => {
    expect(tocaRecordar(0, MS_ENTRE_RECORDATORIOS, true)).toBe(true);
    expect(tocaRecordar(0, MS_ENTRE_RECORDATORIOS - 1000, true)).toBe(false);
  });

  it("nunca mientras trabajás", () => {
    expect(tocaRecordar(0, MS_ENTRE_RECORDATORIOS * 3, false)).toBe(false);
  });

  it("se mide desde el último recordatorio, no desde el último uso", () => {
    const ultimo = 10 * 60 * 1000;
    // Usar Remi a los 20 min no reinicia nada: a los 40 toca.
    expect(tocaRecordar(ultimo, 39 * 60 * 1000, true)).toBe(false);
    expect(tocaRecordar(ultimo, 40 * 60 * 1000, true)).toBe(true);
  });
});

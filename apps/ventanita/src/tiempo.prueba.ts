import { describe, expect, it } from "vitest";
import { formatearReloj } from "./tiempo";

describe("formatearReloj", () => {
  it("minutos sueltos con cero adelante", () => {
    expect(formatearReloj(31)).toBe("0:31");
    expect(formatearReloj(5)).toBe("0:05");
  });

  it("pasada la hora", () => {
    expect(formatearReloj(80)).toBe("1:20");
  });

  it("nunca negativo", () => {
    expect(formatearReloj(-5)).toBe("0:00");
  });
});

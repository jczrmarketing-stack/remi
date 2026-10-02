import { describe, expect, it } from "vitest";
import { respuestaDeTecla } from "./nudges";

describe("respuestaDeTecla", () => {
  it("Enter es listo", () => {
    expect(respuestaDeTecla("Enter")).toBe("listo");
  });

  it("Escape es ahora_no — salida amable, ley 5", () => {
    expect(respuestaDeTecla("Escape")).toBe("ahora_no");
  });

  it("cualquier otra tecla no responde nada", () => {
    expect(respuestaDeTecla("a")).toBeNull();
    expect(respuestaDeTecla("Tab")).toBeNull();
  });

  it("con algo escrito en el campo, Enter y Escape no son del nudge", () => {
    expect(respuestaDeTecla("Enter", true)).toBeNull();
    expect(respuestaDeTecla("Escape", true)).toBeNull();
  });

  it("con el campo vacío siguen respondiendo", () => {
    expect(respuestaDeTecla("Enter", false)).toBe("listo");
    expect(respuestaDeTecla("Escape", false)).toBe("ahora_no");
  });
});

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
});

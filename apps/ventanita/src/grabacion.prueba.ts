import { describe, expect, it } from "vitest";
import { quedoUnaGrabacionColgada } from "./grabacion";

describe("quedoUnaGrabacionColgada", () => {
  it("reconoce el error de Rust, venga como texto o como Error", () => {
    expect(quedoUnaGrabacionColgada("ya había una grabación activa")).toBe(true);
    expect(quedoUnaGrabacionColgada(new Error("ya había una grabación activa"))).toBe(true);
  });
  it("cualquier otro error no es eso", () => {
    expect(quedoUnaGrabacionColgada("ffmpeg terminó enseguida: permiso")).toBe(false);
    expect(quedoUnaGrabacionColgada(undefined)).toBe(false);
  });
});

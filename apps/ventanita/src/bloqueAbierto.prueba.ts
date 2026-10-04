import { describe, expect, it } from "vitest";
import { debeMostrarReloj } from "./bloqueAbierto";
import type { Sesion, Tarea } from "./contratos";

const TAREA_HOY: Tarea = {
  id: "1", titulo: "x", proyecto_id: null, estado: "hoy", paso_minimo: "p",
  estimado_min: null, real_min: null, hora: null, fecha_limite: null, tipo: null, compartible: false,
};

const SESION: Sesion = {
  id: "2", tarea_id: "1", inicio: "2026-10-01T10:00:00Z", fin: null, real_min: 0, app_contexto: null,
};

describe("debeMostrarReloj", () => {
  it("no prende el Reloj sin sesion — el caso de agenda/cobro/entrega (Forma G)", () => {
    expect(debeMostrarReloj(TAREA_HOY, null)).toBe(false);
  });

  it("tampoco prende sin tarea", () => {
    expect(debeMostrarReloj(null, SESION)).toBe(false);
  });

  it("prende con tarea de hoy y sesion — el caso de siempre (hoy)", () => {
    expect(debeMostrarReloj(TAREA_HOY, SESION)).toBe(true);
  });

  it("una tarea archivada (T1) tampoco prende el Reloj", () => {
    expect(debeMostrarReloj({ ...TAREA_HOY, estado: "archivada" }, SESION)).toBe(false);
  });
});

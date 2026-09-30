import { describe, expect, it } from "vitest";
import { limpiarMarkdown } from "./markdown";

describe("limpiarMarkdown", () => {
  it("la respuesta real de las 19:xx sobre Alfonso sale sin asteriscos", () => {
    const crudo =
      "Lo que está abierto:\n\n- **Pagos de Fase 1 (USD 5.000):** USD 1.500 al inicio.\n- **Contrato:** ley de Wyoming.";
    const limpio = limpiarMarkdown(crudo);
    expect(limpio).not.toContain("*");
    expect(limpio).toContain("· Pagos de Fase 1 (USD 5.000): USD 1.500 al inicio.");
    expect(limpio).toContain("· Contrato: ley de Wyoming.");
  });

  it("títulos, citas, enlaces, código y cursivas", () => {
    expect(limpiarMarkdown("## Pendientes\nuno")).toBe("Pendientes\nuno");
    expect(limpiarMarkdown("> ojo con esto")).toBe("ojo con esto");
    expect(limpiarMarkdown("mirá [la ficha](http://x.y)")).toBe("mirá la ficha");
    expect(limpiarMarkdown("corré `npm test`")).toBe("corré npm test");
    expect(limpiarMarkdown("es *muy* importante")).toBe("es muy importante");
  });

  it("no toca lo que no es markdown", () => {
    const normal = "Arrancás el 18 de octubre, con 5 días de tolerancia. 3 * 4 = 12.";
    expect(limpiarMarkdown(normal)).toBe(normal);
    expect(limpiarMarkdown("snake_case_de_una_variable")).toBe("snake_case_de_una_variable");
  });
});

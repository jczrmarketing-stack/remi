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

describe("el chat: links y encargos", () => {
  it("la respuesta de la búsqueda real trae tres links clicables", async () => {
    const { partesConEnlaces } = await import("./markdown");
    const partes = partesConEnlaces(
      "Está en GitHub.\n\n[whisper.cpp en GitHub](https://github.com/ggerganov/whisper.cpp) — el repo oficial",
    );
    expect(partes).toEqual([
      { tipo: "texto", texto: "Está en GitHub.\n\n" },
      { tipo: "enlace", texto: "whisper.cpp en GitHub", url: "https://github.com/ggerganov/whisper.cpp" },
      { tipo: "texto", texto: " — el repo oficial" },
    ]);
  });

  it("un link suelto también", async () => {
    const { partesConEnlaces } = await import("./markdown");
    expect(partesConEnlaces("mirá https://x.co/a y listo")).toEqual([
      { tipo: "texto", texto: "mirá " },
      { tipo: "enlace", texto: "https://x.co/a", url: "https://x.co/a" },
      { tipo: "texto", texto: " y listo" },
    ]);
  });

  it("un encargo sale como tarjeta desde QUÉ", async () => {
    const { partirRespuesta } = await import("./markdown");
    const bloques = partirRespuesta("Listo, acá va.\n\nQUÉ\nUna X.\n\nDÓNDE\nApp.tsx\n\nLISTO CUANDO\n- se ve");
    expect(bloques[0]).toMatchObject({ tipo: "texto" });
    expect(bloques[1]).toEqual({ tipo: "encargo", texto: "QUÉ\nUna X.\n\nDÓNDE\nApp.tsx\n\nLISTO CUANDO\n- se ve" });
  });

  it("lo que el modelo agrega después de las secciones vuelve a ser texto", async () => {
    const { partirRespuesta } = await import("./markdown");
    const bloques = partirRespuesta("QUÉ\nUna X.\n\nLISTO CUANDO\n- se ve\n\nNO TOCAR\n- nada\n\nUn detalle de diseño: puse la X arriba.");
    expect(bloques.map((b) => b.tipo)).toEqual(["encargo", "texto"]);
    expect(bloques[0]).toEqual({ tipo: "encargo", texto: "QUÉ\nUna X.\n\nLISTO CUANDO\n- se ve\n\nNO TOCAR\n- nada" });
  });

  it("con una línea en blanco entre el título y su texto, igual es tarjeta", async () => {
    const { partirRespuesta } = await import("./markdown");
    const bloques = partirRespuesta("QUÉ\n\nUna X.\n\nLISTO CUANDO\n\n- se ve");
    expect(bloques).toEqual([{ tipo: "encargo", texto: "QUÉ\n\nUna X.\n\nLISTO CUANDO\n\n- se ve" }]);
  });

  it("un bloque ``` también es tarjeta, y QUÉ sin LISTO CUANDO no", async () => {
    const { partirRespuesta } = await import("./markdown");
    expect(partirRespuesta("Pegá esto:\n```\nnpm test\n```")[1]).toEqual({ tipo: "encargo", texto: "npm test" });
    expect(partirRespuesta("QUÉ\nes esto").every((b) => b.tipo === "texto")).toBe(true);
  });
});

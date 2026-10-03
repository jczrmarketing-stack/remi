import { describe, expect, it } from "vitest";
import { leerLinea, partirLineas } from "./envivo";

describe("partirLineas", () => {
  it("devuelve las líneas completas y guarda la que quedó a medias", () => {
    expect(partirLineas('{"frase":"a"}\n{"frase":"b"}\n{"fr')).toEqual({
      lineas: ['{"frase":"a"}', '{"frase":"b"}'],
      resto: '{"fr',
    });
  });
  it("sin salto de línea, todo es resto; las líneas vacías se saltan", () => {
    expect(partirLineas('{"frase":"a"}')).toEqual({ lineas: [], resto: '{"frase":"a"}' });
    expect(partirLineas("\n\n{\"fin\":{}}\n")).toEqual({ lineas: ['{"fin":{}}'], resto: "" });
  });
});

describe("leerLinea", () => {
  it("una frase con voz, una sin voz y el fin", () => {
    expect(leerLinea('{"frase":"**Parás** ahora.","voz":"Parás ahora."}')).toEqual({
      tipo: "frase",
      frase: { frase: "**Parás** ahora.", voz: "Parás ahora." },
    });
    expect(leerLinea('{"frase":"Y nada más.","voz":null}')).toEqual({
      tipo: "frase",
      frase: { frase: "Y nada más.", voz: null },
    });
    expect(leerLinea('{"fin":{"tipo":"pregunta","texto":"x","voz":"x"}}')).toEqual({
      tipo: "fin",
      fin: { tipo: "pregunta", texto: "x", voz: "x" },
    });
  });
  it("lo que no se entiende es null, nunca una excepción", () => {
    expect(leerLinea("no es json")).toBeNull();
    expect(leerLinea('{"otra":"cosa"}')).toBeNull();
    expect(leerLinea("null")).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import { PREGUNTA_GUARDAR, yaPreguntoSiGuarda } from "./guardarCharla";

const pregunta = {
  texto: PREGUNTA_GUARDAR,
  pregunta: { onSi: () => {}, onNo: () => {} },
};

describe("pegar largo pregunta una sola vez", () => {
  it("no hay pregunta si el chat está vacío o habla de otra cosa", () => {
    expect(yaPreguntoSiGuarda([])).toBe(false);
    expect(yaPreguntoSiGuarda([{ texto: "Hoy solo esto: la tarjeta." }])).toBe(false);
    expect(yaPreguntoSiGuarda([{ texto: PREGUNTA_GUARDAR }])).toBe(false);
  });

  it("con la pregunta en pantalla, un segundo pegado no la repite", () => {
    expect(yaPreguntoSiGuarda([pregunta])).toBe(true);
    expect(yaPreguntoSiGuarda([{ texto: "hola" }, pregunta, { texto: "seguimos" }])).toBe(true);
  });

  it("después de Sí o No la pregunta ya no está y se puede volver a preguntar", () => {
    const sinElla = [pregunta].filter((m) => m.texto !== PREGUNTA_GUARDAR);
    expect(yaPreguntoSiGuarda(sinElla)).toBe(false);
  });
});

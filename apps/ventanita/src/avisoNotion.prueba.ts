import { describe, expect, it } from "vitest";
import { bloquesDelAviso, lugarDelAviso, TAMANO_AVISO_NOTION } from "./avisoNotion";

const aviso = { id: "a", que: "Llamar a Alfonso", paso_minimo: "Abrir el chat", encogido: false };

describe("bloquesDelAviso", () => {
  it("la primera vez muestra el Qué y debajo el paso mínimo", () => {
    expect(bloquesDelAviso(aviso)).toEqual([
      { rotulo: null, texto: "Llamar a Alfonso", fuerte: true },
      { rotulo: "Paso mínimo", texto: "Abrir el chat", fuerte: false },
    ]);
  });

  it("si ya salió antes, el paso mínimo pasa adelante y el Qué se calla (ley 3)", () => {
    const [primero, segundo] = bloquesDelAviso({ ...aviso, encogido: true });
    expect(primero).toEqual({ rotulo: "Paso mínimo", texto: "Abrir el chat", fuerte: true });
    expect(segundo).toEqual({ rotulo: null, texto: "Llamar a Alfonso", fuerte: false });
  });

  it("sin paso mínimo solo muestra el Qué, sin rótulo vacío", () => {
    expect(bloquesDelAviso({ ...aviso, paso_minimo: "  " })).toEqual([
      { rotulo: null, texto: "Llamar a Alfonso", fuerte: true },
    ]);
  });
});

describe("lugarDelAviso", () => {
  it("queda pegado al borde derecho, bajo la barra de menú", () => {
    const pantalla = { x: 0, y: 0, width: 1440, height: 900 };
    expect(lugarDelAviso(pantalla, TAMANO_AVISO_NOTION)).toEqual({ x: 1080, y: 40 });
  });

  it("respeta un monitor que no empieza en 0,0", () => {
    const pantalla = { x: 1440, y: -200, width: 1920, height: 1080 };
    expect(lugarDelAviso(pantalla, TAMANO_AVISO_NOTION)).toEqual({ x: 3000, y: -160 });
  });
});

import { describe, expect, it } from "vitest";
import {
  cortePorSilencioAplica,
  decidir,
  decidirPalanca,
  decidirTrasVacia,
  MAX_VACIAS_SEGUIDAS,
  MS_ANTES_DE_REARMAR,
  MS_GRACIA,
  MS_RACHA,
  RACHA_VACIA,
  type Entrada,
  type Racha,
} from "./gestos";

/** Un clicker: mantiene la racha y el estado como lo hace la ventanita. */
function crearVentanita(inicial: Partial<Entrada> = {}) {
  let racha: Racha = RACHA_VACIA;
  const estado = {
    estado: "reposo" as Entrada["estado"],
    modo: "texto" as Entrada["modo"],
    grabando: false,
    textoVacio: true,
    grabacionDesde: null as number | null,
    ...inicial,
  };

  return {
    get estado() {
      return estado;
    },
    click(ahora: number, dentroDeControl = false, dentroDelCuadro = false) {
      const decision = decidir({ ...estado, dentroDeControl, dentroDelCuadro, ahora, racha });
      racha = decision.racha;

      // Lo que haría App.tsx con cada acción.
      switch (decision.accion.tipo) {
        case "abrirTexto":
          estado.estado = "escuchando";
          estado.modo = "texto";
          break;
        case "grabarVoz":
          estado.estado = "escuchando";
          estado.modo = "voz";
          estado.grabando = true;
          estado.grabacionDesde = ahora;
          break;
        case "pasarADialogo":
          estado.modo = "dialogo";
          break;
        case "pararGrabacion":
          estado.grabando = false;
          estado.grabacionDesde = null;
          estado.estado = "pensando";
          break;
        case "volverAReposo":
          estado.estado = "reposo";
          estado.modo = "texto";
          estado.grabando = false;
          estado.grabacionDesde = null;
          break;
      }
      return decision.accion;
    },
  };
}

describe("la secuencia real del log del 29 de septiembre", () => {
  it("clicks a 0, 167, 366 y 1300 ms: llega a diálogo y NO se corta", () => {
    const v = crearVentanita();

    expect(v.click(0).tipo).toBe("abrirTexto");
    expect(v.click(167).tipo).toBe("grabarVoz");
    expect(v.click(366).tipo).toBe("pasarADialogo");
    expect(v.estado.modo).toBe("dialogo");
    expect(v.estado.grabando).toBe(true);

    // El 4.º dedo, 934 ms después del 3.º. Antes cortaba la grabación a los
    // 411 ms de nacida y arrancaba la cadena de cinco ciclos.
    const tardio = v.click(1300);
    expect(tardio.tipo).toBe("nada");
    expect(v.estado.grabando).toBe(true);
  });

  it("un doble click llega a grabar sin esperar ningún temporizador", () => {
    const v = crearVentanita();
    v.click(0);
    expect(v.click(167).tipo).toBe("grabarVoz");
    // Grabando ya, en el mismo instante del click: no a los 520 ms.
    expect(v.estado.grabacionDesde).toBe(167);
  });
});

describe("el periodo de gracia", () => {
  it("un click a los 300 ms de arrancar no para la grabación", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(167);
    const durante = v.click(167 + 300);
    expect(durante.tipo).not.toBe("pararGrabacion");
    expect(v.estado.grabando).toBe(true);
  });

  it("pasada la gracia, un click sí para el dictado", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(167);
    const despues = v.click(167 + MS_GRACIA + 50);
    expect(despues.tipo).toBe("pararGrabacion");
    expect(v.estado.grabando).toBe(false);
  });

  it("en diálogo ningún click para la grabación, ni pasada la gracia", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(167);
    v.click(366);
    expect(v.estado.modo).toBe("dialogo");
    for (const t of [366 + MS_GRACIA + 100, 4000, 9000]) {
      expect(v.click(t).tipo).toBe("nada");
      expect(v.estado.grabando).toBe(true);
    }
  });
});

describe("los clicks que sobran", () => {
  it("el 4.º de la misma racha se absorbe", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(100);
    v.click(200);
    const cuarto = v.click(300);
    expect(cuarto.tipo).toBe("nada");
    expect(cuarto).toMatchObject({ razon: "absorbido (n=4)" });
    expect(v.estado.grabando).toBe(true);
    expect(v.estado.modo).toBe("dialogo");
  });

  it("un click dentro de un control no es un gesto ni corta la racha", () => {
    const v = crearVentanita();
    v.click(0);
    // Tocar el toggle entre el 1.º y el 2.º no rompe el doble click.
    expect(v.click(80, true).tipo).toBe("nada");
    expect(v.click(160).tipo).toBe("grabarVoz");
  });
});

describe("un click suelto", () => {
  it("en reposo abre el texto", () => {
    const v = crearVentanita();
    expect(v.click(0).tipo).toBe("abrirTexto");
  });

  it("con texto escrito, lo manda", () => {
    const v = crearVentanita({ estado: "escuchando", textoVacio: false });
    expect(v.click(5000).tipo).toBe("mandarTexto");
  });

  it("mientras Remi habla, vuelve a reposo", () => {
    const v = crearVentanita({ estado: "hablando" });
    expect(v.click(5000).tipo).toBe("volverAReposo");
  });

  it("dos clicks lejanos son dos clicks sueltos, no un doble", () => {
    const v = crearVentanita();
    expect(v.click(0).tipo).toBe("abrirTexto");
    // Más que MS_RACHA: la racha se reinicia, no hay doble click.
    expect(v.click(MS_RACHA + 100).tipo).not.toBe("grabarVoz");
  });
});

describe("la palanca (atajo global)", () => {
  it("sin grabación, graba en modo voz", () => {
    expect(decidirPalanca({ estado: "reposo", modo: "texto", grabando: false }).tipo).toBe("grabarVoz");
    expect(decidirPalanca({ estado: "escuchando", modo: "texto", grabando: false }).tipo).toBe("grabarVoz");
  });

  it("con dictado en curso, lo para — aunque acabe de arrancar", () => {
    // Es una tecla, no un dedo que sigue cayendo: no hay gracia.
    expect(decidirPalanca({ estado: "escuchando", modo: "voz", grabando: true }).tipo).toBe("pararGrabacion");
  });

  it("en diálogo, lo termina", () => {
    expect(decidirPalanca({ estado: "escuchando", modo: "dialogo", grabando: true }).tipo).toBe("terminarDialogo");
  });

  it("mientras Remi piensa o habla, no hace nada", () => {
    expect(decidirPalanca({ estado: "pensando", modo: "voz", grabando: false }).tipo).toBe("nada");
    expect(decidirPalanca({ estado: "hablando", modo: "voz", grabando: false }).tipo).toBe("nada");
  });
});

describe("el corte por silencio", () => {
  it("el dictado NUNCA corta por silencio: cuatro segundos callado no mandan nada", () => {
    expect(cortePorSilencioAplica("voz")).toBe(false);
    expect(cortePorSilencioAplica("texto")).toBe(false);
  });

  it("solo el diálogo se corta solo", () => {
    expect(cortePorSilencioAplica("dialogo")).toBe(true);
  });
});

describe("escuchas vacías en diálogo", () => {
  it("la primera vacía re-arma, pero no en el acto", () => {
    expect(decidirTrasVacia(1)).toEqual({ tipo: "rearmar", enMs: MS_ANTES_DE_REARMAR });
    expect(MS_ANTES_DE_REARMAR).toBeGreaterThanOrEqual(1000);
  });

  it("dos vacías seguidas → reposo, sin decir nada", () => {
    expect(decidirTrasVacia(MAX_VACIAS_SEGUIDAS)).toEqual({ tipo: "reposo" });
    expect(decidirTrasVacia(MAX_VACIAS_SEGUIDAS + 1)).toEqual({ tipo: "reposo" });
  });
});

describe("la secuencia real del log de las 16:18: el cuadro aparece bajo el mouse", () => {
  it("2.º click a 584 ms, dentro del cuadro vacío → graba", () => {
    const v = crearVentanita();
    // 1.er click en reposo: abre texto y la ventana crece a 420×520 con el
    // cuadro llenándola. (El cambio de tamaño es lo que pone el cuadro bajo
    // el mouse: acá se modela como estado=escuchando + dentroDelCuadro.)
    expect(v.click(0).tipo).toBe("abrirTexto");
    expect(v.estado.estado).toBe("escuchando");

    const segundo = v.click(584, false, true);
    expect(segundo.tipo).toBe("grabarVoz");
    expect(v.estado.grabando).toBe(true);
  });

  it("3.º click también dentro del cuadro → diálogo", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(584, false, true);
    expect(v.click(584 + 180, false, true).tipo).toBe("pasarADialogo");
  });

  it("con texto escrito, un click dentro del cuadro es para escribir", () => {
    const v = crearVentanita({ estado: "escuchando", textoVacio: false });
    expect(v.click(0, false, true)).toMatchObject({ tipo: "nada", razon: "dentro del cuadro (escribiendo)" });
    expect(v.click(180, false, true)).toMatchObject({ tipo: "nada" });
    expect(v.estado.grabando).toBe(false);
  });

  it("un click suelto dentro del cuadro vacío no graba, pero abre la racha", () => {
    const v = crearVentanita({ estado: "escuchando" });
    // Sin racha viva, un click en el cuadro es para escribir…
    expect(v.click(5000, false, true)).toMatchObject({ tipo: "nada" });
    // …pero cuenta como 1.º: el siguiente rápido es el 2.º y graba. Es lo
    // que pasó a las 16:18:44 (dos clicks a 183 ms, los dos en el cuadro).
    expect(v.click(5183, false, true).tipo).toBe("grabarVoz");
  });

  it("un click sobre un control nunca cuenta, ni con el cuadro vacío", () => {
    const v = crearVentanita({ estado: "escuchando" });
    expect(v.click(0, true).tipo).toBe("nada");
    expect(v.click(150, true).tipo).toBe("nada");
    expect(v.estado.grabando).toBe(false);
  });
});

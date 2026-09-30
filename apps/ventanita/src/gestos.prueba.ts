import { describe, expect, it } from "vitest";
import {
  cortePorSilencioAplica,
  decidir,
  decidirPalanca,
  decidirTrasVacia,
  MAX_VACIAS_SEGUIDAS,
  MS_ANTES_DE_REARMAR,
  MS_FANTASMA_RESIZE,
  MS_FANTASMA_SEGUIDO,
  MS_GRACIA,
  MS_RACHA,
  MS_TRIPLE,
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
    click(ahora: number, dentroDeControl = false, dentroDelCuadro = false, msDesdeCambioDeTamano: number | null = null) {
      const decision = decidir({ ...estado, dentroDeControl, dentroDelCuadro, msDesdeCambioDeTamano, ahora, racha });
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
          estado.grabacionDesde = ahora;
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
    // Fuera de la gracia Y fuera de la ventana del triple (2 s desde el
    // 1.º): antes de eso, un click es el 3.º y pasa a diálogo.
    const despues = v.click(MS_TRIPLE + 50);
    expect(despues.tipo).toBe("pararGrabacion");
    expect(v.estado.grabando).toBe(false);
  });

  it("en diálogo, dentro de la gracia un click no para; pasada, sí", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(167);
    v.click(366);
    expect(v.estado.modo).toBe("dialogo");
    expect(v.click(366 + 500).tipo).toBe("nada");
    expect(v.estado.grabando).toBe(true);
    // Una racha nueva (más de MS_RACHA después), ya fuera de la gracia.
    expect(v.click(366 + 500 + MS_RACHA + MS_GRACIA).tipo).toBe("pararGrabacion");
    expect(v.estado.grabando).toBe(false);
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

  it("mientras Remi habla, un click no la cancela", () => {
    const v = crearVentanita({ estado: "hablando" });
    expect(v.click(5000)).toMatchObject({ tipo: "nada" });
    expect(v.click(5200)).toMatchObject({ tipo: "nada" });
    expect(v.estado.estado).toBe("hablando");
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

describe("la secuencia real del log de las 16:43: doble click para parar", () => {
  it("un 3.º click accidental entra en diálogo, y un doble click 50 s después para sin cancelar", () => {
    const v = crearVentanita();
    expect(v.click(0).tipo).toBe("abrirTexto");
    expect(v.click(672, false, true).tipo).toBe("grabarVoz");
    // El dedo cayó una vez más, 411 ms después: diálogo sin querer.
    expect(v.click(1083, false, true).tipo).toBe("pasarADialogo");
    expect(v.estado.modo).toBe("dialogo");

    // 50 s hablando. Después, un doble click para parar: el 1.º para…
    expect(v.click(50000).tipo).toBe("pararGrabacion");
    expect(v.estado.estado).toBe("pensando");
    // …y el 2.º, 158 ms después, no cancela la transcripción.
    expect(v.click(50158).tipo).toBe("nada");
    expect(v.estado.estado).toBe("pensando");
  });

  it("en dictado también: el 2.º click del doble que paró no cancela", () => {
    const v = crearVentanita();
    v.click(0);
    v.click(600, false, true);
    expect(v.estado.modo).toBe("voz");
    // Pasados los 2 s del triple, el click es para parar.
    expect(v.click(MS_TRIPLE + 200).tipo).toBe("pararGrabacion");
    expect(v.click(MS_TRIPLE + 360).tipo).toBe("nada");
    expect(v.estado.estado).toBe("pensando");
  });

  it("mientras transcribe o manda, ningún click cancela: solo Escape", () => {
    const v = crearVentanita({ estado: "pensando" });
    expect(v.click(9000)).toMatchObject({ tipo: "nada" });
    expect(v.estado.estado).toBe("pensando");
  });
});

describe("tres clicks en menos de dos segundos", () => {
  it("a ritmo tranquilo (0, 700, 1600) entra en diálogo en vez de parar", () => {
    const v = crearVentanita();
    expect(v.click(0).tipo).toBe("abrirTexto");
    expect(v.click(650, false, true).tipo).toBe("grabarVoz");
    // 950 ms después del 2.º: fuera de MS_RACHA y fuera de la gracia. Antes
    // esto PARABA la grabación. Está a 1600 del 1.º: es el 3.º.
    expect(v.click(1600, false, true).tipo).toBe("pasarADialogo");
    expect(v.estado.modo).toBe("dialogo");
    expect(v.estado.grabando).toBe(true);
  });

  it("el 3.º justo antes de los 2 s cuenta; justo después, no", () => {
    const a = crearVentanita();
    a.click(0);
    a.click(600, false, true);
    expect(a.click(MS_TRIPLE - 50).tipo).toBe("pasarADialogo");

    const b = crearVentanita();
    b.click(0);
    b.click(600, false, true);
    // Racha nueva, fuera de la gracia: es un click para parar.
    expect(b.click(MS_TRIPLE + 50).tipo).toBe("pararGrabacion");
  });

  it("el doble click sigue estricto: el 2.º tiene que venir pegado al 1.º", () => {
    const v = crearVentanita();
    v.click(0);
    // A 1,5 s del 1.º no hay racha de dos: la ventana ancha es solo para el 3.º.
    expect(v.click(1500, false, true).tipo).not.toBe("grabarVoz");
    expect(v.estado.grabando).toBe(false);
  });
});

describe("clicks fantasma (log del 29/09)", () => {
  it("18:42:59: un click a 8 ms de enviar no cancela, y otro a 17 ms es fantasma", () => {
    // Remi acaba de mandar: está pensando. Antes: click → volverAReposo →
    // respuesta cancelada; 17 ms después otro click → abrirTexto.
    const v = crearVentanita({ estado: "pensando", modo: "dialogo" });
    expect(v.click(8)).toMatchObject({ tipo: "nada" });
    expect(v.estado.estado).toBe("pensando");
    // El de 17 ms después: además de estar pensando, es demasiado seguido.
    expect(v.click(25)).toMatchObject({ tipo: "nada" });
    expect(v.estado.estado).toBe("pensando");
  });

  it("18:44:01: tres clicks en 20 ms sobre el cuadro — solo el primero es un click", () => {
    const v = crearVentanita({ estado: "escuchando", modo: "voz" });
    expect(v.click(0, false, true)).toMatchObject({ tipo: "nada", razon: "dentro del cuadro (1.º de una racha)" });
    expect(v.click(16, false, true)).toMatchObject({ tipo: "nada", razon: "fantasma: muy seguido" });
    expect(v.click(20, false, true)).toMatchObject({ tipo: "nada", razon: "fantasma: muy seguido" });
    // Los fantasmas no tocan la racha: el 3.º no la convirtió en n=3.
    expect(v.estado.grabando).toBe(false);
  });

  it("un click a 14 ms de un cambio de tamaño es fantasma", () => {
    const v = crearVentanita({ estado: "reposo" });
    expect(v.click(0, false, false, 14)).toMatchObject({ tipo: "nada", razon: "fantasma: resize" });
    expect(v.estado.estado).toBe("reposo");
  });

  it("un doble click real sigue grabando aunque el 2.º caiga cerca del resize", () => {
    // El 1.º abre texto y la ventana crece ~20 ms después; el 2.º real más
    // rápido del día llegó a 125 ms del 1.º (≈105 del resize).
    const v = crearVentanita();
    expect(v.click(0).tipo).toBe("abrirTexto");
    expect(v.click(125, false, true, 105).tipo).toBe("grabarVoz");
    expect(MS_FANTASMA_RESIZE).toBeLessThan(105);
    expect(MS_FANTASMA_SEGUIDO).toBeLessThan(125);
  });
});

describe("la respuesta escrita se queda (3b)", () => {
  it("un click afuera la cierra", () => {
    const decision = decidir({
      estado: "hablando", modo: "texto", grabando: false, textoVacio: true,
      dentroDeControl: false, dentroDelCuadro: false, grabacionDesde: null,
      msDesdeCambioDeTamano: null, ahora: 5000, racha: RACHA_VACIA, respuestaQueda: true,
    });
    expect(decision.accion.tipo).toBe("volverAReposo");
  });

  it("un click sobre el texto de la respuesta no la cierra (para poder seleccionarlo)", () => {
    const decision = decidir({
      estado: "hablando", modo: "texto", grabando: false, textoVacio: true,
      dentroDeControl: true, dentroDelCuadro: false, grabacionDesde: null,
      msDesdeCambioDeTamano: null, ahora: 5000, racha: RACHA_VACIA, respuestaQueda: true,
    });
    expect(decision.accion.tipo).toBe("nada");
  });

  it("por voz, igual que antes: un click no la corta", () => {
    const decision = decidir({
      estado: "hablando", modo: "voz", grabando: false, textoVacio: true,
      dentroDeControl: false, dentroDelCuadro: false, grabacionDesde: null,
      msDesdeCambioDeTamano: null, ahora: 5000, racha: RACHA_VACIA, respuestaQueda: false,
    });
    expect(decision.accion.tipo).toBe("nada");
  });
});

describe("la bolita del chat", () => {
  const base = { estado: "escuchando" as const, modo: "texto" as const, grabando: false, toqueAnterior: null, grabacionDesde: null };

  it("un toque dicta; otro toque más tarde para y transcribe", async () => {
    const { decidirBolita } = await import("./gestos");
    expect(decidirBolita({ ...base, ahora: 1000 })).toEqual({ tipo: "dictar" });
    expect(
      decidirBolita({ ...base, modo: "voz", grabando: true, ahora: 4000, toqueAnterior: 1000, grabacionDesde: 1000 }),
    ).toEqual({ tipo: "pararDictado" });
  });

  it("dos toques pegados: conversación de voz sobre la misma grabación", async () => {
    const { decidirBolita } = await import("./gestos");
    expect(
      decidirBolita({ ...base, modo: "voz", grabando: true, ahora: 1300, toqueAnterior: 1000, grabacionDesde: 1000 }),
    ).toEqual({ tipo: "pasarADialogo" });
  });

  it("en conversación, un toque tardío la termina; uno pegado no", async () => {
    const { decidirBolita } = await import("./gestos");
    const dialogo = { ...base, modo: "dialogo" as const, grabando: true, grabacionDesde: 1000 };
    expect(decidirBolita({ ...dialogo, ahora: 1500, toqueAnterior: 1300 }).tipo).toBe("nada");
    expect(decidirBolita({ ...dialogo, ahora: 6000, toqueAnterior: 1300 })).toEqual({ tipo: "terminarDialogo" });
  });

  it("pensando no hace nada; hablando, calla; un fantasma se ignora", async () => {
    const { decidirBolita } = await import("./gestos");
    expect(decidirBolita({ ...base, estado: "pensando", ahora: 1000 }).tipo).toBe("nada");
    expect(decidirBolita({ ...base, estado: "hablando", ahora: 1000 })).toEqual({ tipo: "callar" });
    expect(decidirBolita({ ...base, ahora: 1030, toqueAnterior: 1000 }).tipo).toBe("nada");
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// voz.ts toca window, fetch, Audio y URL: acá se les da lo justo para que
// dos hablar() seguidas se puedan probar sin navegador ni núcleo.

type Oyente = () => void;

class AudioFalso {
  static creados: AudioFalso[] = [];
  static reproducidos: AudioFalso[] = [];
  preservesPitch = true;
  playbackRate = 1;
  src: string;
  private oyentes = new Map<string, Oyente[]>();

  constructor(src: string) {
    this.src = src;
    AudioFalso.creados.push(this);
  }
  addEventListener(evento: string, oyente: Oyente) {
    this.oyentes.set(evento, [...(this.oyentes.get(evento) ?? []), oyente]);
  }
  disparar(evento: string) {
    for (const oyente of this.oyentes.get(evento) ?? []) oyente();
  }
  play() {
    AudioFalso.reproducidos.push(this);
    return Promise.resolve();
  }
  pause() {
    /* nada */
  }
}

beforeEach(() => {
  AudioFalso.creados = [];
  AudioFalso.reproducidos = [];
  vi.stubGlobal("window", globalThis);
  vi.stubGlobal("Audio", AudioFalso);
  // No se reemplaza URL entera (vite la necesita como constructor): solo
  // los dos métodos que usa voz.ts para el blob.
  vi.spyOn(URL, "createObjectURL").mockImplementation(() => "blob:falso");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  // El núcleo contesta con un wav (vacío, da igual): lo que importa es que
  // contesta y que hay algo que reproducir.
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, blob: async () => new Blob(["wav"]) })),
  );
  vi.spyOn(console, "info").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("hablar() sin eco", () => {
  it("dos llamadas seguidas suenan una sola vez, y la primera queda cancelada", async () => {
    const { hablar } = await import("./voz");

    const primera = hablar("hola, soy Remi", 1, "auto");
    const segunda = hablar("y esto es lo segundo", 1, "auto");

    // Dejar que las dos pidan el audio y decidan.
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));

    // Solo la segunda llegó a reproducir; la primera vio que ya no era la
    // generación vigente y se fue callada.
    expect(AudioFalso.reproducidos).toHaveLength(1);
    await primera;

    // La segunda termina cuando termina el audio, no antes.
    let terminoLaSegunda = false;
    void segunda.then(() => {
      terminoLaSegunda = true;
    });
    await new Promise((r) => setTimeout(r, 0));
    expect(terminoLaSegunda).toBe(false);
    AudioFalso.reproducidos[0].disparar("ended");
    await segunda;
    expect(terminoLaSegunda).toBe(true);
  });

  it("callarse() cancela la que estaba y no cae a la voz del sistema", async () => {
    const { callarse, hablar } = await import("./voz");
    const llamada = hablar("una frase", 1, "auto");
    callarse();
    await llamada;
    // Se pidió el audio pero, al volver, ya no era la generación vigente.
    expect(AudioFalso.reproducidos).toHaveLength(0);
  });
});

describe("cuánto se espera a Kokoro", () => {
  it("crece con el largo y tiene techo", async () => {
    const { limiteDeVoz } = await import("./voz");
    expect(limiteDeVoz("Hola.")).toBe(4150);
    expect(limiteDeVoz(Array(28).fill("palabra").join(" "))).toBe(8200);
    expect(limiteDeVoz(Array(500).fill("palabra").join(" "))).toBe(20000);
  });
});

describe("empezarLocucion() en vivo (V3)", () => {
  it("dice las frases en el orden en que llegan y fin resuelve solo después de terminar()", async () => {
    const { empezarLocucion } = await import("./voz");
    const sonidos: number[] = [];
    const locucion = empezarLocucion(1, "auto", () => sonidos.push(AudioFalso.reproducidos.length));

    locucion.agregar("Parás ahora mismo, ya.");
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    // La primera frase suena sin esperar a que lleguen las demás.
    expect(AudioFalso.reproducidos).toHaveLength(1);
    expect(sonidos).toEqual([0]);

    locucion.agregar("Tomá agua y dormí temprano.");
    AudioFalso.reproducidos[0].disparar("ended");
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(AudioFalso.reproducidos).toHaveLength(2);
    // El primer sonido se avisa una sola vez.
    expect(sonidos).toEqual([0]);

    let termino = false;
    void locucion.fin.then(() => {
      termino = true;
    });
    AudioFalso.reproducidos[1].disparar("ended");
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    // Dijo todo lo que tenía, pero todavía pueden llegar más frases.
    expect(termino).toBe(false);

    locucion.terminar();
    await locucion.fin;
    expect(termino).toBe(true);
  });

  it("otra locución (o hablar) la pisa: lo pendiente no suena", async () => {
    const { empezarLocucion, hablar } = await import("./voz");
    const primera = empezarLocucion(1, "auto");
    primera.agregar("Una frase que iba a sonar.");
    const segunda = hablar("Y esto es lo segundo, que sí suena.", 1, "auto");
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(AudioFalso.reproducidos).toHaveLength(1);
    await primera.fin;
    AudioFalso.reproducidos[0].disparar("ended");
    await segunda;
  });
});

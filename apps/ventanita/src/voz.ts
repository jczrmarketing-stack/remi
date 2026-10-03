// La voz de Remi. Primero la del núcleo (local, sin clave): pide el wav
// por HTTP y lo reproduce. Si el núcleo no contesta o el motor falla, cae
// a la voz del sistema (speechSynthesis sobre AVSpeechSynthesizer) sin
// decir una palabra del error — ley 3: un fallo no se convierte en reto.
import type { PreferenciaVoz, Velocidad } from "./preferencias";
import { VOZ_AUTOMATICA } from "./preferencias";
import { URL_NUCLEO } from "./config";

export interface VozDisponible {
  id: string;
  lang: string;
  label: string;
}

// Generar una frase tarda ~1,5 s con el modelo ya cargado. Si pasa esto,
// algo anda mal (el núcleo recién arrancó, o está apagado): mejor la voz
// del sistema ya que esperar callada.
// Proporcional al largo: 30 palabras tardan ~3 s con la Mac tranquila y más
// de 5 cuando Whisper u Ollama acaban de usar la memoria (30/09, 22:13: se
// cortó a los 5 s y cayó a Paulina). Techo de 20 s.
const TIMEOUT_TTS_BASE_MS = 4000;
const TIMEOUT_TTS_POR_PALABRA_MS = 150;
const TIMEOUT_TTS_TECHO_MS = 20000;

export function limiteDeVoz(texto: string): number {
  const palabras = texto.trim() ? texto.trim().split(/\s+/).length : 0;
  return Math.min(TIMEOUT_TTS_TECHO_MS, TIMEOUT_TTS_BASE_MS + palabras * TIMEOUT_TTS_POR_PALABRA_MS);
}

let audioActual: HTMLAudioElement | null = null;
let urlActual: string | null = null;

// Contador de generación. Cada hablar() y cada callarse() lo suben; una
// llamada que vuelve de un await y ve que ya no es la generación vigente
// no reproduce nada. Sin esto, dos hablar() seguidas sonaban las dos: la
// primera volvía de pedir el audio cuando la segunda ya había arrancado.
let generacion = 0;

// Parte el texto en frases para generarlas y decirlas de a una. Corta en
// . ! ? … seguidos de espacio; una frase muy corta («Ajá.») se pega a la
// siguiente, porque un audio por cada dos palabras suena entrecortado.
const PALABRAS_MINIMAS_POR_FRASE = 4;

export function dividirEnFrases(texto: string): string[] {
  const limpio = texto.trim().replace(/\s+/g, " ");
  if (!limpio) return [];
  const crudas = limpio.split(/(?<=[.!?…])\s+/).filter((f) => f.length > 0);
  const frases: string[] = [];
  let pendiente = "";
  for (const cruda of crudas) {
    pendiente = pendiente ? `${pendiente} ${cruda}` : cruda;
    if (pendiente.split(" ").length >= PALABRAS_MINIMAS_POR_FRASE) {
      frases.push(pendiente);
      pendiente = "";
    }
  }
  if (pendiente) {
    if (frases.length > 0) frases[frases.length - 1] += ` ${pendiente}`;
    else frases.push(pendiente);
  }
  return frases;
}

export function haySoporteDeVoz(): boolean {
  return "speechSynthesis" in window;
}

// — La voz del núcleo —

export async function obtenerVoces(): Promise<VozDisponible[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/tts/voices`);
  if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
  return (await respuesta.json()) as VozDisponible[];
}

async function pedirAudio(texto: string, voz: PreferenciaVoz, velocidadModelo = 1): Promise<Blob | null> {
  const controlador = new AbortController();
  const limite = window.setTimeout(() => controlador.abort(), limiteDeVoz(texto));
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: texto,
        voice: voz === VOZ_AUTOMATICA ? null : voz,
        ...(velocidadModelo !== 1 ? { speed: velocidadModelo } : {}),
      }),
      signal: controlador.signal,
    });
    if (!respuesta.ok) {
      console.info(`[voz] el núcleo no dio audio (${respuesta.status}): uso la voz del sistema`);
      return null;
    }
    return await respuesta.blob();
  } catch (error) {
    console.info("[voz] no pude pedir el audio al núcleo:", error);
    return null;
  } finally {
    window.clearTimeout(limite);
  }
}

// La velocidad la hace el propio modelo hasta 1,5×: estirar el audio en el
// reproductor (WebKit) se come fonemas y a 1,5× se perdían palabras. Lo que
// pase de 1,5× (el 2×) sí se completa estirando, pero solo el resto.
const VELOCIDAD_MAXIMA_DEL_MODELO = 1.5;

export function repartirVelocidad(velocidad: Velocidad): { modelo: number; reproductor: number } {
  const modelo = Math.min(velocidad, VELOCIDAD_MAXIMA_DEL_MODELO);
  return { modelo, reproductor: velocidad / modelo };
}

// — El volumen de la voz, para que el punto lata con ella —
// Un AudioContext con un analizador entre el audio de Kokoro y los
// parlantes. Solo se engancha si el contexto ya corre: uno suspendido
// dejaría el audio mudo, y eso nunca vale una animación.
let contexto: AudioContext | null = null;
let analizador: AnalyserNode | null = null;
let muestras: Uint8Array<ArrayBuffer> | null = null;
let audioAnalizado: HTMLAudioElement | null = null;
// De hablar() a que termina: lo usa el click para no cortar a Remi.
let ocupadaHasta: number | null = null;

/** Crear o despertar el contexto de audio. Va en un gesto (click). */
export function despertarAudio(): void {
  try {
    if (!contexto) contexto = new AudioContext();
    if (contexto.state === "suspended") void contexto.resume();
  } catch {
    contexto = null;
  }
}

function engancharAnalizador(elemento: HTMLAudioElement): void {
  audioAnalizado = null;
  if (!contexto || contexto.state !== "running") return;
  try {
    if (!analizador) {
      analizador = contexto.createAnalyser();
      analizador.fftSize = 512;
      analizador.connect(contexto.destination);
      muestras = new Uint8Array(new ArrayBuffer(analizador.fftSize));
    }
    contexto.createMediaElementSource(elemento).connect(analizador);
    audioAnalizado = elemento;
  } catch (error) {
    console.info("[voz] sin analizador de volumen:", error);
  }
}

export interface EstadoDeVoz {
  // Suena algo ahora mismo (Kokoro o la voz del sistema).
  sonando: boolean;
  // 0..1 aprox. del audio de Kokoro; null si suena pero no se puede medir
  // (la voz del sistema) o si no suena.
  volumen: number | null;
}

export function estadoDeVoz(): EstadoDeVoz {
  const kokoro = audioActual !== null && !audioActual.paused && !audioActual.ended;
  const sistema = haySoporteDeVoz() && window.speechSynthesis.speaking;
  if (!kokoro && !sistema) return { sonando: false, volumen: null };
  if (!kokoro || audioAnalizado !== audioActual || !analizador || !muestras) {
    return { sonando: true, volumen: null };
  }
  analizador.getByteTimeDomainData(muestras);
  let suma = 0;
  for (const v of muestras) {
    const x = (v - 128) / 128;
    suma += x * x;
  }
  return { sonando: true, volumen: Math.sqrt(suma / muestras.length) };
}

/** Remi está diciendo algo (o preparando el audio para decirlo). */
export function vozOcupada(): boolean {
  return ocupadaHasta !== null;
}

function liberarAudio(): void {
  if (audioActual) {
    audioActual.pause();
    audioActual.src = "";
    audioActual = null;
  }
  if (urlActual) {
    URL.revokeObjectURL(urlActual);
    urlActual = null;
  }
}

type FinDeReproduccion = "terminó" | "cancelada" | "falló";

// Resuelve en el evento `ended`: App sale de "hablando" cuando la voz
// termina de verdad, no cuando lo adivina un temporizador. `mia` es la
// generación de quien llama: si otra la pisó, lo que pase con este audio
// es una cancelación, no un fallo.
function reproducir(audio: Blob, velocidad: number, mia: number): Promise<FinDeReproduccion> {
  return new Promise((resolve) => {
    liberarAudio();
    const url = URL.createObjectURL(audio);
    const elemento = new Audio(url);
    // Estirar el tiempo sin subir el tono: es el comportamiento por
    // defecto, pero en WebKit conviene pedirlo explícito.
    elemento.preservesPitch = true;
    elemento.playbackRate = velocidad;
    audioActual = elemento;
    urlActual = url;
    engancharAnalizador(elemento);

    let resuelto = false;
    const terminar = (fin: FinDeReproduccion) => {
      if (resuelto) return;
      resuelto = true;
      resolve(fin);
    };
    const cancelada = () => generacion !== mia;

    elemento.addEventListener("ended", () => terminar("terminó"), { once: true });
    elemento.addEventListener(
      "error",
      () => {
        // liberarAudio() pone src="" y eso dispara `error`: si fue por una
        // cancelación, no es un fallo del reproductor.
        if (cancelada()) return terminar("cancelada");
        console.info(`[voz] #${mia} no pude reproducir el audio del núcleo`);
        terminar("falló");
      },
      { once: true },
    );

    void elemento.play().catch((error: unknown) => {
      // AbortError es lo que tira play() cuando lo interrumpe una pausa o
      // un cambio de src: es una cancelación, nunca motivo para caer a la
      // voz del sistema.
      const nombre = error instanceof Error ? error.name : "";
      if (cancelada() || nombre === "AbortError") return terminar("cancelada");
      console.info(`[voz] #${mia} el reproductor no arrancó:`, error);
      terminar("falló");
    });
  });
}

// — La voz del sistema (respaldo) —

let vocesCache: SpeechSynthesisVoice[] = [];
let vozElegida: SpeechSynthesisVoice | undefined;

function cargarVoces(): Promise<SpeechSynthesisVoice[]> {
  const disponibles = window.speechSynthesis.getVoices();
  if (disponibles.length > 0) {
    return Promise.resolve(disponibles);
  }
  return new Promise((resolve) => {
    window.speechSynthesis.onvoiceschanged = () => {
      resolve(window.speechSynthesis.getVoices());
    };
  });
}

// La calidad de una voz de macOS no siempre está en el nombre: WebKit
// expone el identificador de AVSpeechSynthesisVoice en voiceURI, y ahí
// sí se lee — com.apple.voice.premium.es-ES.Monica, .enhanced., .compact.
// Las "eloquence" (Eddy, Flo, Grandma…) son voces de novedad, robóticas:
// van al final, solo si no hay otra cosa en español.
function puntajeCalidad(voz: SpeechSynthesisVoice): number {
  const pista = `${voz.name} ${voz.voiceURI}`.toLowerCase();
  if (/premium/.test(pista)) return 4;
  if (/enhanced|mejorada|neural/.test(pista)) return 3;
  if (/eloquence/.test(pista)) return 0;
  return 2; // compact: Mónica, Paulina
}

// A igual calidad, español de América antes que el de España: es el
// acento de quien la escucha.
function puntajeRegion(voz: SpeechSynthesisVoice): number {
  const lang = voz.lang.toLowerCase().replace("_", "-");
  if (/^es-(co|419|mx|ar|cl|pe|us)/.test(lang)) return 1;
  return 0;
}

export function elegirVoz(voces: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  const espanolas = voces.filter((v) => v.lang.toLowerCase().startsWith("es"));
  if (espanolas.length === 0) return voces[0];
  return [...espanolas].sort(
    (a, b) =>
      puntajeCalidad(b) - puntajeCalidad(a) || puntajeRegion(b) - puntajeRegion(a),
  )[0];
}

function describir(voz: SpeechSynthesisVoice): string {
  return `${voz.name} · ${voz.lang} · ${voz.voiceURI}`;
}

// Una sola vez por sesión: qué voz de respaldo eligió y entre cuáles.
function avisarEleccion(voces: SpeechSynthesisVoice[], elegida: SpeechSynthesisVoice | undefined): void {
  const espanolas = voces.filter((v) => v.lang.toLowerCase().startsWith("es"));
  const naturales = espanolas.filter((v) => puntajeCalidad(v) >= 3);
  console.info(
    `[voz] respaldo del sistema: ${voces.length} voces, ${espanolas.length} en español, ${naturales.length} premium/enhanced`,
  );
  if (elegida) {
    console.info(`[voz] respaldo elegido: ${describir(elegida)}`);
  }
}

async function asegurarVozDelSistema(): Promise<SpeechSynthesisVoice | undefined> {
  if (vocesCache.length === 0) {
    vocesCache = await cargarVoces();
    vozElegida = elegirVoz(vocesCache);
    avisarEleccion(vocesCache, vozElegida);
  }
  return vozElegida;
}

function hablarConElSistema(texto: string, velocidad: Velocidad): Promise<void> {
  if (!haySoporteDeVoz()) return Promise.resolve();
  return asegurarVozDelSistema().then(
    (voz) =>
      new Promise((resolve) => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(texto);
        if (voz) {
          utterance.voice = voz;
          utterance.lang = voz.lang;
        }
        utterance.rate = velocidad;
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
      }),
  );
}

// — Las muletillas —
// Lo primero que se oye al terminar de hablarle: «mmm, a ver…». Son audios
// cortos del propio núcleo, pedidos una vez y guardados, elegidos al azar:
// no hay IA ni datos en ellas, así que no pueden inventar nada. Tapan el
// silencio mientras Remi piensa; la respuesta espera a que terminen.
const MULETILLAS = ["Mmm, a ver…", "Ajá, déjame pensar.", "Ok, un momento.", "Mm, claro. A ver…", "A ver, déjame ver."];
const muletillasListas = new Map<string, Blob[]>();
let muletillasPidiendo = false;
let ultimaMuletilla = -1;
let muletillaAudio: HTMLAudioElement | null = null;
let muletillaFin: Promise<void> | null = null;
let muletillaTerminar: (() => void) | null = null;

export async function precalentarMuletillas(voz: PreferenciaVoz): Promise<void> {
  const clave = String(voz);
  if (muletillasListas.has(clave) || muletillasPidiendo) return;
  muletillasPidiendo = true;
  try {
    const blobs: Blob[] = [];
    for (const frase of MULETILLAS) {
      const audio = await pedirAudio(frase, voz);
      if (audio) blobs.push(audio);
    }
    if (blobs.length > 0) muletillasListas.set(clave, blobs);
  } finally {
    muletillasPidiendo = false;
  }
}

function pararMuletilla(): void {
  if (muletillaAudio) muletillaAudio.pause();
  muletillaTerminar?.();
}

/** Suena una muletilla ya guardada, sin esperar nada. Si no hay, no hace nada. */
export function decirMuletilla(voz: PreferenciaVoz = VOZ_AUTOMATICA): void {
  const blobs = muletillasListas.get(String(voz));
  if (!blobs || blobs.length === 0) {
    void precalentarMuletillas(voz);
    return;
  }
  pararMuletilla();
  let i = Math.floor(Math.random() * blobs.length);
  if (blobs.length > 1 && i === ultimaMuletilla) i = (i + 1) % blobs.length;
  ultimaMuletilla = i;
  const url = URL.createObjectURL(blobs[i]);
  const elemento = new Audio(url);
  elemento.preservesPitch = true;
  muletillaAudio = elemento; // siempre a 1×: son dos palabras y así no hay que guardarlas por velocidad
  console.info("[voz] muletilla");
  muletillaFin = new Promise<void>((resolver) => {
    const terminar = () => {
      URL.revokeObjectURL(url);
      if (muletillaAudio === elemento) {
        muletillaAudio = null;
        muletillaFin = null;
        muletillaTerminar = null;
      }
      resolver();
    };
    muletillaTerminar = terminar;
    elemento.addEventListener("ended", terminar, { once: true });
    elemento.addEventListener("error", terminar, { once: true });
    void elemento.play().catch(terminar);
  });
}

// — Lo que usa la ventanita —

/**
 * Una locución: frases que se dicen en orden, de a una, generando la
 * siguiente mientras suena la anterior. Las frases pueden ir llegando (V3:
 * el núcleo manda cada oración en cuanto el motor la termina) — por eso
 * `agregar` y `terminar` son dos cosas: `fin` resuelve cuando se dijo todo
 * lo agregado y ya no viene más, o cuando otra locución (o callarse) la pisó.
 */
export interface Locucion {
  agregar(frase: string): void;
  terminar(): void;
  fin: Promise<void>;
}

interface Cola {
  frases: string[];
  cerrada: boolean;
  despertar: (() => void) | null;
}

function esperarCola(cola: Cola): Promise<void> {
  return new Promise((resolve) => {
    cola.despertar = resolve;
  });
}

function avisarCola(cola: Cola): void {
  const despertar = cola.despertar;
  cola.despertar = null;
  despertar?.();
}

/**
 * Empieza a hablar. `alPrimerSonido` se llama justo cuando arranca el
 * primer audio (después de la muletilla, si la había): es el dato de
 * «→primer_sonido» del log de latencia.
 */
export function empezarLocucion(
  velocidad: Velocidad = 1,
  voz: PreferenciaVoz = VOZ_AUTOMATICA,
  alPrimerSonido?: () => void,
): Locucion {
  generacion += 1;
  const mia = generacion;
  ocupadaHasta = mia;
  despertarAudio();
  const cola: Cola = { frases: [], cerrada: false, despertar: null };
  const fin = locucionSinMarca(cola, velocidad, voz, mia, alPrimerSonido).finally(() => {
    if (ocupadaHasta === mia) ocupadaHasta = null;
  });
  return {
    agregar(frase: string) {
      if (cola.cerrada) return;
      const limpia = frase.trim();
      if (!limpia) return;
      cola.frases.push(limpia);
      avisarCola(cola);
    },
    terminar() {
      cola.cerrada = true;
      avisarCola(cola);
    },
    fin,
  };
}

/**
 * Resuelve cuando Remi terminó de hablar, por el camino que haya sido — o
 * cuando la pisó otra llamada. Cada llamada tiene un id que queda en el log
 * al empezar y al terminar, con cómo terminó.
 */
export async function hablar(
  texto: string,
  velocidad: Velocidad = 1,
  voz: PreferenciaVoz = VOZ_AUTOMATICA,
): Promise<void> {
  const palabras = texto.trim() ? texto.trim().split(/\s+/).length : 0;
  const locucion = empezarLocucion(velocidad, voz);
  console.info(`[voz] #${generacion} texto entero: ${palabras} palabras`);
  for (const frase of dividirEnFrases(texto)) locucion.agregar(frase);
  locucion.terminar();
  await locucion.fin;
}

async function locucionSinMarca(
  cola: Cola,
  velocidad: Velocidad,
  voz: PreferenciaVoz,
  mia: number,
  alPrimerSonido?: () => void,
): Promise<void> {
  console.info(`[voz] #${mia} empieza: ${velocidad}×, voz=${voz}`);

  liberarAudio();
  if (haySoporteDeVoz()) window.speechSynthesis.cancel();

  // En frases: la primera suena en cuanto está lista y las siguientes se
  // generan mientras tanto. Una respuesta de 30 palabras tardaba ~3 s en
  // generarse entera antes de que sonara nada; la primera frase, ~1 s.
  const { modelo: velocidadModelo, reproductor: velocidadReproductor } = repartirVelocidad(velocidad);
  const pedidos: Array<Promise<Blob | null> | undefined> = [];
  const pedir = (i: number) => {
    if (i < cola.frases.length && pedidos[i] === undefined) pedidos[i] = pedirAudio(cola.frases[i], voz, velocidadModelo);
  };
  const cancelada = () => generacion !== mia;
  // Sin audio del núcleo (no contestó, o el motor falló) o sin poder
  // reproducirlo: de ahí en adelante, la voz del sistema, en silencio
  // sobre el fallo.
  let conElSistema = false;
  let sono = false;
  let dichas = 0;
  for (let i = 0; ; i += 1) {
    while (i >= cola.frases.length && !cola.cerrada) {
      await esperarCola(cola);
      if (cancelada()) {
        console.info(`[voz] #${mia} cancelada esperando frases`);
        return;
      }
    }
    if (i >= cola.frases.length) break;
    if (conElSistema) {
      await hablarConElSistema(cola.frases[i], velocidad);
      if (cancelada()) {
        console.info(`[voz] #${mia} cancelada (sistema)`);
        return;
      }
      dichas = i + 1;
      continue;
    }
    pedir(i);
    pedir(i + 1);
    pedir(i + 2);
    const audio = await pedidos[i];
    if (cancelada()) {
      console.info(`[voz] #${mia} cancelada antes de reproducir`);
      return;
    }
    if (i === 0) console.info(`[voz] #${mia} primera frase lista`);
    // La muletilla no se corta: la respuesta suena cuando ella termina.
    if (muletillaFin) {
      await muletillaFin;
      if (cancelada()) {
        console.info(`[voz] #${mia} cancelada tras la muletilla`);
        return;
      }
    }
    let fin: FinDeReproduccion = "falló";
    if (audio) {
      if (!sono) {
        sono = true;
        alPrimerSonido?.();
      }
      fin = await reproducir(audio, velocidadReproductor, mia);
    }
    if (fin === "cancelada") {
      console.info(`[voz] #${mia} cancelada`);
      return;
    }
    if (fin === "falló") {
      console.info(`[voz] #${mia} cae a la voz del sistema`);
      conElSistema = true;
      if (!sono) {
        sono = true;
        alPrimerSonido?.();
      }
      await hablarConElSistema(cola.frases[i], velocidad);
      if (cancelada()) {
        console.info(`[voz] #${mia} cancelada (sistema)`);
        return;
      }
    }
    dichas = i + 1;
  }
  console.info(`[voz] #${mia} terminó${conElSistema ? " (sistema)" : ""}: ${dichas} frase(s)`);
}

export function callarse(): void {
  generacion += 1;
  ocupadaHasta = null;
  pararMuletilla();
  liberarAudio();
  if (haySoporteDeVoz()) {
    window.speechSynthesis.cancel();
  }
}

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

export function haySoporteDeVoz(): boolean {
  return "speechSynthesis" in window;
}

// — La voz del núcleo —

export async function obtenerVoces(): Promise<VozDisponible[]> {
  const respuesta = await fetch(`${URL_NUCLEO}/tts/voices`);
  if (!respuesta.ok) throw new Error(`El núcleo respondió ${respuesta.status}`);
  return (await respuesta.json()) as VozDisponible[];
}

async function pedirAudio(texto: string, voz: PreferenciaVoz): Promise<Blob | null> {
  const controlador = new AbortController();
  const limite = window.setTimeout(() => controlador.abort(), limiteDeVoz(texto));
  try {
    const respuesta = await fetch(`${URL_NUCLEO}/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // La velocidad NO va acá: el modelo generaría con otra prosodia. El
      // reproductor la estira conservando el tono.
      body: JSON.stringify({ text: texto, voice: voz === VOZ_AUTOMATICA ? null : voz }),
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
function reproducir(audio: Blob, velocidad: Velocidad, mia: number): Promise<FinDeReproduccion> {
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

// — Lo que usa la ventanita —

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
  generacion += 1;
  const mia = generacion;
  ocupadaHasta = mia;
  despertarAudio();
  try {
    await hablarSinMarca(texto, velocidad, voz, mia);
  } finally {
    if (ocupadaHasta === mia) ocupadaHasta = null;
  }
}

async function hablarSinMarca(
  texto: string,
  velocidad: Velocidad,
  voz: PreferenciaVoz,
  mia: number,
): Promise<void> {
  const palabras = texto.trim() ? texto.trim().split(/\s+/).length : 0;
  console.info(`[voz] #${mia} empieza: ${palabras} palabras, ${velocidad}×, voz=${voz}`);

  liberarAudio();
  if (haySoporteDeVoz()) window.speechSynthesis.cancel();

  const audio = await pedirAudio(texto, voz);
  if (generacion !== mia) {
    console.info(`[voz] #${mia} cancelada antes de reproducir`);
    return;
  }

  if (audio) {
    const fin = await reproducir(audio, velocidad, mia);
    if (fin === "terminó" || fin === "cancelada") {
      console.info(`[voz] #${mia} ${fin}`);
      return;
    }
    // "falló": el audio llegó pero no se pudo reproducir. Eso sí es motivo
    // para la voz del sistema.
  }
  if (generacion !== mia) {
    console.info(`[voz] #${mia} cancelada`);
    return;
  }

  // Sin audio del núcleo (no contestó, o el motor falló) o sin poder
  // reproducirlo: la voz del sistema, en silencio sobre el fallo.
  console.info(`[voz] #${mia} cae a la voz del sistema`);
  await hablarConElSistema(texto, velocidad);
  console.info(`[voz] #${mia} ${generacion === mia ? "terminó (sistema)" : "cancelada (sistema)"}`);
}

export function callarse(): void {
  generacion += 1;
  ocupadaHasta = null;
  liberarAudio();
  if (haySoporteDeVoz()) {
    window.speechSynthesis.cancel();
  }
}

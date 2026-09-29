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
const TIMEOUT_TTS_MS = 5000;

let audioActual: HTMLAudioElement | null = null;
let urlActual: string | null = null;

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
  const limite = window.setTimeout(() => controlador.abort(), TIMEOUT_TTS_MS);
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

// Resuelve en el evento `ended`: App sale de "hablando" cuando la voz
// termina de verdad, no cuando lo adivina un temporizador.
function reproducir(audio: Blob, velocidad: Velocidad): Promise<boolean> {
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

    let resuelto = false;
    const terminar = (bien: boolean) => {
      if (resuelto) return;
      resuelto = true;
      resolve(bien);
    };

    elemento.addEventListener("ended", () => terminar(true), { once: true });
    elemento.addEventListener(
      "error",
      () => {
        console.info("[voz] no pude reproducir el audio del núcleo");
        terminar(false);
      },
      { once: true },
    );

    void elemento.play().catch((error) => {
      console.info("[voz] el reproductor no arrancó:", error);
      terminar(false);
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

/** Resuelve cuando Remi terminó de hablar, por el camino que haya sido. */
export async function hablar(
  texto: string,
  velocidad: Velocidad = 1,
  voz: PreferenciaVoz = VOZ_AUTOMATICA,
): Promise<void> {
  callarse();

  const audio = await pedirAudio(texto, voz);
  if (audio && (await reproducir(audio, velocidad))) return;

  // Sin núcleo, sin motor o sin poder reproducir: la voz del sistema, en
  // silencio sobre el fallo.
  await hablarConElSistema(texto, velocidad);
}

export function callarse(): void {
  liberarAudio();
  if (haySoporteDeVoz()) {
    window.speechSynthesis.cancel();
  }
}

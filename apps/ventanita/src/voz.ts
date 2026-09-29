// Remi habla con las voces del sistema (macOS): WKWebView expone
// window.speechSynthesis sobre AVSpeechSynthesizer — nada sale del Mac.
import type { Velocidad } from "./preferencias";

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

// Una sola vez por sesión: qué voz eligió y entre cuáles. Si acá no
// aparece ninguna premium/enhanced, es que no hay ninguna descargada
// (Ajustes → Accesibilidad → Contenido hablado → Voces del sistema).
function avisarEleccion(voces: SpeechSynthesisVoice[], elegida: SpeechSynthesisVoice | undefined): void {
  const espanolas = voces.filter((v) => v.lang.toLowerCase().startsWith("es"));
  const naturales = espanolas.filter((v) => puntajeCalidad(v) >= 3);
  console.info(
    `[voz] ${voces.length} voces, ${espanolas.length} en español, ${naturales.length} premium/enhanced`,
  );
  if (elegida) {
    console.info(`[voz] elegida: ${describir(elegida)}`);
  } else {
    console.info("[voz] ninguna voz disponible: Remi no puede hablar");
  }
  if (naturales.length === 0) {
    console.info(
      "[voz] sin voces naturales en español: descargá una Premium/Enhanced en Ajustes → Accesibilidad → Contenido hablado",
    );
  }
}

export function haySoporteDeVoz(): boolean {
  return "speechSynthesis" in window;
}

async function asegurarVoz(): Promise<SpeechSynthesisVoice | undefined> {
  if (vocesCache.length === 0) {
    vocesCache = await cargarVoces();
    vozElegida = elegirVoz(vocesCache);
    avisarEleccion(vocesCache, vozElegida);
  }
  return vozElegida;
}

// Resuelve cuando termina de hablar (o de inmediato si el webview no
// soporta voz). `velocidad` es utterance.rate: 1 es la natural.
export async function hablar(texto: string, velocidad: Velocidad = 1): Promise<void> {
  if (!haySoporteDeVoz()) return;

  const voz = await asegurarVoz();

  window.speechSynthesis.cancel();

  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(texto);
    if (voz) {
      utterance.voice = voz;
      utterance.lang = voz.lang;
    }
    utterance.rate = velocidad;
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    window.speechSynthesis.speak(utterance);
  });
}

export function callarse(): void {
  if (haySoporteDeVoz()) {
    window.speechSynthesis.cancel();
  }
}

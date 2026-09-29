// Remi habla con las voces del sistema (macOS): WKWebView expone
// window.speechSynthesis sobre AVSpeechSynthesizer — nada sale del Mac.
let vocesCache: SpeechSynthesisVoice[] = [];

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

function elegirVoz(voces: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  const espanolas = voces.filter((v) => v.lang.toLowerCase().startsWith("es"));
  const natural = espanolas.find((v) => /premium|enhanced|neural/i.test(v.name));
  return natural ?? espanolas[0] ?? voces[0];
}

export function haySoporteDeVoz(): boolean {
  return "speechSynthesis" in window;
}

// Resuelve cuando termina de hablar (o de inmediato si el webview no soporta voz).
export async function hablar(texto: string): Promise<void> {
  if (!haySoporteDeVoz()) return;

  if (vocesCache.length === 0) {
    vocesCache = await cargarVoces();
  }

  window.speechSynthesis.cancel();

  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(texto);
    const voz = elegirVoz(vocesCache);
    if (voz) utterance.voice = voz;
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

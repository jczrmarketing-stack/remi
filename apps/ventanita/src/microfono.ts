import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

export const EVENTO_SILENCIO = "voz://silencio";

// cortarSolo: el núcleo avisa por EVENTO_SILENCIO cuando dejaste de hablar.
export function iniciarEscucha(cortarSolo: boolean): Promise<void> {
  return invoke("iniciar_escucha", { cortarSolo });
}

export function detenerEscuchaYTranscribir(): Promise<string> {
  return invoke("detener_escucha_y_transcribir");
}

// "fin": hablaste y te callaste → se transcribe. "sin_voz": pasaron 10 s
// sin que dijeras nada → Remi deja de esperar.
export type MotivoSilencio = "fin" | "sin_voz";

interface AvisoSilencio {
  motivo: MotivoSilencio;
}

export function alDetectarSilencio(accion: (motivo: MotivoSilencio) => void): Promise<() => void> {
  return listen<AvisoSilencio>(EVENTO_SILENCIO, (evento) => accion(evento.payload.motivo));
}

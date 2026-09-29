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

export function alDetectarSilencio(accion: () => void): Promise<() => void> {
  return listen(EVENTO_SILENCIO, accion);
}

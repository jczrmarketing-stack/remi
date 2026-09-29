import { invoke } from "@tauri-apps/api/core";

export function iniciarEscucha(): Promise<void> {
  return invoke("iniciar_escucha");
}

export function detenerEscuchaYTranscribir(): Promise<string> {
  return invoke("detener_escucha_y_transcribir");
}

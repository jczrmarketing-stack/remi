import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

export const EVENTO_SILENCIO = "voz://silencio";

// cortarSolo: el núcleo avisa por EVENTO_SILENCIO cuando dejaste de hablar.
export function iniciarEscucha(cortarSolo: boolean): Promise<void> {
  return invoke("iniciar_escucha", { cortarSolo });
}

// Quién cortó la grabación. Lo sabe la ventanita, no el micrófono, y sin
// eso el log no alcanza para entender un gesto que salió mal.
export type OrigenParada = "click" | "silencio:fin" | "silencio:sin_voz" | "escape" | "timeout";

// El 3.er click: la grabación sigue, solo se le prende el corte por silencio.
export function activarCortePorSilencio(): Promise<void> {
  return invoke("activar_corte_por_silencio");
}

export function detenerEscuchaYTranscribir(origen: OrigenParada): Promise<string> {
  return invoke("detener_escucha_y_transcribir", { origen });
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

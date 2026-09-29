export type Estado = "reposo" | "escuchando" | "pensando" | "hablando";

// Cómo entró ESTE mensaje: hoy solo existe "texto" (el PromptTerminal).
// "voz" queda listo para cuando haya micrófono — Remi solo habla si
// el origen fue voz, nunca cuando escribiste en silencio.
export type OrigenMensaje = "voz" | "texto";

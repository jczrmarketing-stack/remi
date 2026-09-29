export type Estado = "reposo" | "escuchando" | "pensando" | "hablando";

// Cómo entró ESTE mensaje: "voz" si activaste el micrófono, "texto" si
// lo escribiste a mano (o el micrófono falló). Remi solo habla si el
// origen fue voz, nunca cuando escribiste en silencio.
export type OrigenMensaje = "voz" | "texto";

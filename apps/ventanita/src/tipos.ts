export type Estado = "reposo" | "escuchando" | "pensando" | "hablando";

// Cómo entró ESTE mensaje: "voz" si activaste el micrófono, "texto" si
// lo escribiste a mano (o el micrófono falló). Remi solo habla si el
// origen fue voz, nunca cuando escribiste en silencio.
export type OrigenMensaje = "voz" | "texto";

// Cómo se abrió la ventanita, según cuántos clicks le diste:
// 1 = escribís, 2 = te escucha una vez (como Handy), 3 = dialogan.
export type Modo = "texto" | "voz" | "dialogo";

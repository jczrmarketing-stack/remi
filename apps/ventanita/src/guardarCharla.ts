// El 3-oct, 01:18, dos pegados seguidos (14875 y 1935 caracteres) dejaron
// la misma pregunta dos veces: cada pegado largo la agregaba sin mirar si
// ya estaba. Sí o No la quitan, y entonces un pegado posterior puede
// volver a preguntar.

export const PREGUNTA_GUARDAR = "¿Lo guardo como conversación?";

export function yaPreguntoSiGuarda(
  mensajes: readonly { texto: string; pregunta?: unknown }[],
): boolean {
  return mensajes.some((mensaje) => mensaje.pregunta != null && mensaje.texto === PREGUNTA_GUARDAR);
}

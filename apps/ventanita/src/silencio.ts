// Mute explícito de la voz de Remi, persistido entre sesiones (localStorage
// del webview: sobrevive a cerrar y volver a abrir la ventanita).
const CLAVE_SILENCIO = "remi.voz.silenciada";

export function estaSilenciado(): boolean {
  try {
    return localStorage.getItem(CLAVE_SILENCIO) === "1";
  } catch {
    return false;
  }
}

export function alternarSilencio(): boolean {
  const nuevo = !estaSilenciado();
  try {
    localStorage.setItem(CLAVE_SILENCIO, nuevo ? "1" : "0");
  } catch {
    // Sin localStorage el mute no persiste, pero tampoco rompe nada.
  }
  return nuevo;
}

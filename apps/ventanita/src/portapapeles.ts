// Copiar al portapapeles del sistema desde el webview. navigator.clipboard
// pide gesto del usuario y contexto seguro (tauri:// y localhost lo son);
// si el WKWebView lo niega, cae al execCommand clásico con un textarea
// invisible. Devuelve si pudo.
export async function copiarAlPortapapeles(texto: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch (error) {
    console.warn("[portapapeles] clipboard API falló, pruebo execCommand:", error);
  }

  const campo = document.createElement("textarea");
  campo.value = texto;
  campo.setAttribute("readonly", "");
  campo.style.position = "fixed";
  campo.style.opacity = "0";
  document.body.appendChild(campo);
  campo.select();
  let copiado = false;
  try {
    copiado = document.execCommand("copy");
  } catch {
    copiado = false;
  } finally {
    document.body.removeChild(campo);
  }
  return copiado;
}

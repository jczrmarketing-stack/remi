// Un solo lugar donde queda lo que pasa. La app instalada no tiene terminal
// donde mirar, así que todo lo que se escriba con console.* se reenvía al
// archivo (~/Library/Logs/Remi/ventanita.log) por el plugin de log, al lado
// del log del núcleo. La hora con milisegundos la pone el lado de Rust: para
// entender un gesto hace falta el orden y la distancia entre dos eventos.
import { error as aLogError, info as aLogInfo, warn as aLogWarn } from "@tauri-apps/plugin-log";

let enchufado = false;

function aTexto(partes: unknown[]): string {
  return partes
    .map((parte) => {
      if (typeof parte === "string") return parte;
      if (parte instanceof Error) return `${parte.name}: ${parte.message}`;
      try {
        return JSON.stringify(parte);
      } catch {
        return String(parte);
      }
    })
    .join(" ");
}

/** Reenvía console.* al archivo, sin dejar de escribir en la consola. */
export function enchufarConsola(): void {
  if (enchufado) return;
  enchufado = true;

  const original = {
    log: console.log.bind(console),
    info: console.info.bind(console),
    warn: console.warn.bind(console),
    error: console.error.bind(console),
  };

  // Si el reenvío falla (sin plugin, por ejemplo), la consola sigue andando:
  // un log roto no puede romper la app.
  const reenviar = (destino: (texto: string) => Promise<void>, partes: unknown[]) => {
    try {
      void destino(aTexto(partes)).catch(() => undefined);
    } catch {
      // nada: ya quedó en la consola
    }
  };

  console.log = (...partes: unknown[]) => {
    original.log(...partes);
    reenviar(aLogInfo, partes);
  };
  console.info = (...partes: unknown[]) => {
    original.info(...partes);
    reenviar(aLogInfo, partes);
  };
  console.warn = (...partes: unknown[]) => {
    original.warn(...partes);
    reenviar(aLogWarn, partes);
  };
  console.error = (...partes: unknown[]) => {
    original.error(...partes);
    reenviar(aLogError, partes);
  };
}

/**
 * Una línea por evento, siempre con la misma forma: `[gesto] nombre a=1 b=x`.
 * Se lee de corrido y se puede grepear por evento.
 */
export function registrar(evento: string, datos?: Record<string, unknown>): void {
  const detalle = datos
    ? " " +
      Object.entries(datos)
        .map(([clave, valor]) => `${clave}=${valor}`)
        .join(" ")
    : "";
  console.info(`[gesto] ${evento}${detalle}`);
}

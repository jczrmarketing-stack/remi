import { LogicalSize, type Window } from "@tauri-apps/api/window";

interface Tamano {
  width: number;
  height: number;
}

// Misma curva que el resto del sistema: cubic-bezier(0.2, 0.8, 0.2, 1).
const P1X = 0.2;
const P1Y = 0.8;
const P2X = 0.2;
const P2Y = 1;

function componenteBezier(t: number, p1: number, p2: number): number {
  const u = 1 - t;
  return 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t;
}

function resolverTParaX(x: number): number {
  let t = x;
  for (let i = 0; i < 8; i++) {
    const diferencia = componenteBezier(t, P1X, P2X) - x;
    if (Math.abs(diferencia) < 1e-4) break;
    const derivada =
      3 * (1 - t) * (1 - t) * P1X + 6 * (1 - t) * t * (P2X - P1X) + 3 * t * t * (1 - P2X);
    if (Math.abs(derivada) < 1e-6) break;
    t -= diferencia / derivada;
  }
  return t;
}

function curvaVentanita(x: number): number {
  return componenteBezier(resolverTParaX(x), P1Y, P2Y);
}

export function animarTamano(
  ventana: Window,
  desde: Tamano,
  hasta: Tamano,
  duracionMs: number,
): Promise<void> {
  const inicio = performance.now();
  return new Promise((resolve) => {
    // Con un temporizador y no con requestAnimationFrame: el webview deja de
    // dibujar cuadros cuando la ventana no está activa, y la animación se
    // quedaba a medias — el chat abierto dentro de una ventana de 72×72.
    // Una ventana flotante tiene que terminar de abrirse siempre.
    function paso() {
      const t = Math.min(1, (performance.now() - inicio) / duracionMs);
      const progreso = curvaVentanita(t);
      const ancho = desde.width + (hasta.width - desde.width) * progreso;
      const alto = desde.height + (hasta.height - desde.height) * progreso;
      void ventana.setSize(new LogicalSize(ancho, alto));
      if (t < 1) {
        window.setTimeout(paso, 16);
      } else {
        resolve();
      }
    }
    paso();
  });
}

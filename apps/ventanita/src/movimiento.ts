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
    function paso(ahora: number) {
      const t = Math.min(1, (ahora - inicio) / duracionMs);
      const progreso = curvaVentanita(t);
      const ancho = desde.width + (hasta.width - desde.width) * progreso;
      const alto = desde.height + (hasta.height - desde.height) * progreso;
      void ventana.setSize(new LogicalSize(ancho, alto));
      if (t < 1) {
        requestAnimationFrame(paso);
      } else {
        resolve();
      }
    }
    requestAnimationFrame(paso);
  });
}

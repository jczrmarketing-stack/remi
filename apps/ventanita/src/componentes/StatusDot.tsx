import { useEffect, useRef } from "react";
import type { Estado } from "../tipos";
import type { EstadoDeVoz } from "../voz";
import "./StatusDot.css";

interface Props {
  estado: Estado;
  // Mientras el micrófono está abierto el LED crece: que se vea que te escucha.
  escuchandoVoz?: boolean;
  // Hablando, el punto late con el volumen de la voz. Lo lee en cada cuadro.
  medirVoz?: () => EstadoDeVoz;
  // Piel dinero (3f · 3): el bloque abierto es de una entrega que paga.
  // Reemplaza `brasa` por `dinero` en `hablando`; no inventa un glow nuevo
  // (el DS solo tiene glow-luz/brasa/pensar).
  dinero?: boolean;
}

// Cuánto crece con la voz más fuerte, y cómo sigue al volumen: sube rápido
// (se ve la sílaba) y baja despacio (no tiembla).
const CRECE_HASTA = 0.45;
const GANANCIA = 4;
const SUBIDA = 0.5;
const BAJADA = 0.12;

export function StatusDot({ estado, escuchandoVoz = false, medirVoz, dinero = false }: Props) {
  const punto = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (estado !== "hablando" || !medirVoz) return;
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cuadro = 0;
    let suave = 0;
    const paso = () => {
      const el = punto.current;
      if (el) {
        const { sonando, volumen } = medirVoz();
        el.dataset.sonando = sonando ? "si" : "no";
        el.dataset.medida = volumen === null ? "no" : "si";
        const meta = sonando && volumen !== null && !reducido ? Math.min(1, volumen * GANANCIA) : 0;
        suave += (meta - suave) * (meta > suave ? SUBIDA : BAJADA);
        el.style.setProperty("--volumen", (suave * CRECE_HASTA).toFixed(3));
      }
      cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => {
      cancelAnimationFrame(cuadro);
      const el = punto.current;
      if (el) {
        el.style.removeProperty("--volumen");
        delete el.dataset.sonando;
        delete el.dataset.medida;
      }
    };
  }, [estado, medirVoz]);

  return (
    <div
      ref={punto}
      className="status-dot"
      data-estado={estado}
      data-voz={escuchandoVoz ? "si" : "no"}
      data-dinero={dinero ? "si" : "no"}
      aria-hidden="true"
    />
  );
}

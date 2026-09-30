// Íconos de los modos, dibujados acá en SVG: trazo de 1.75 en
// currentColor, así toman el color del texto (tokens del DS) y no traen
// una librería por cuatro dibujos.
import type { ModoPensar } from "../preferencias";

const COMUN = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function IconoModo({ modo }: { modo: ModoPensar }) {
  switch (modo) {
    case "rapido":
      // Un rayo: rápido.
      return (
        <svg {...COMUN}>
          <path d="M9 1.5 3.5 9h4l-1 5.5L12.5 7h-4z" />
        </svg>
      );
    case "equilibrio":
      // Un círculo partido al medio: la mitad y la mitad.
      return (
        <svg {...COMUN}>
          <circle cx="8" cy="8" r="5.5" />
          <path d="M8 2.5v11" />
        </svg>
      );
    case "inteligente":
      // Una chispa de cuatro puntas: piensa antes de contestar.
      return (
        <svg {...COMUN}>
          <path d="M8 1.5c.6 3.4 1.9 4.9 5.5 6.5-3.6 1.6-4.9 3.1-5.5 6.5-.6-3.4-1.9-4.9-5.5-6.5 3.6-1.6 4.9-3.1 5.5-6.5z" />
        </svg>
      );
    case "prompt":
      // Un prompt de terminal: «>_». Es para Claude Code.
      return (
        <svg {...COMUN}>
          <path d="M3 4.5 6.5 8 3 11.5M8.5 12h4.5" />
        </svg>
      );
  }
}

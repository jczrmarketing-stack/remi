import type { Estado } from "../tipos";
import "./StatusDot.css";

interface Props {
  estado: Estado;
  // Mientras el micrófono está abierto el LED crece: que se vea que te escucha.
  escuchandoVoz?: boolean;
}

export function StatusDot({ estado, escuchandoVoz = false }: Props) {
  return (
    <div
      className="status-dot"
      data-estado={estado}
      data-voz={escuchandoVoz ? "si" : "no"}
      aria-hidden="true"
    />
  );
}

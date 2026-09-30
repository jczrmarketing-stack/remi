import { X } from "lucide-react";
import "./BotonCancelar.css";

interface Props {
  onCancelar: () => void;
}

/**
 * La X de la esquina superior derecha: cancela lo que esté pasando —
 * escuchando, pensando o hablando, en cualquier modo— sin transcribir ni
 * mandar, y vuelve a reposo. Lo mismo que Escape, para cuando la mano
 * está en el mouse. Ícono de 16 px (Lucide 1.75) en ink-muted; el área
 * que se toca es de 44×44.
 */
export function BotonCancelar({ onCancelar }: Props) {
  return (
    <button
      type="button"
      className="boton-cancelar"
      aria-label="Cancelar"
      title="Cancelar (Esc)"
      onClick={(evento) => {
        evento.stopPropagation();
        onCancelar();
      }}
    >
      <X size={16} strokeWidth={1.75} aria-hidden="true" />
    </button>
  );
}

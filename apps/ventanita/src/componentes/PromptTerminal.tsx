import { useEffect, useRef } from "react";
import "./PromptTerminal.css";

interface Props {
  valor: string;
  deshabilitado: boolean;
  enfocar: boolean;
  onCambio: (texto: string) => void;
  onEnviar: () => void;
}

export function PromptTerminal({ valor, deshabilitado, enfocar, onCambio, onEnviar }: Props) {
  const campoRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (enfocar) {
      campoRef.current?.focus();
    }
  }, [enfocar]);

  return (
    <div className="prompt-terminal">
      <textarea
        ref={campoRef}
        className="code prompt-terminal__campo"
        aria-label="Escribile a Remi"
        value={valor}
        disabled={deshabilitado}
        placeholder="Cmd+Enter para enviar"
        onChange={(evento) => onCambio(evento.target.value)}
        onKeyDown={(evento) => {
          if (evento.key === "Enter" && (evento.metaKey || evento.ctrlKey)) {
            evento.preventDefault();
            onEnviar();
          }
        }}
      />
    </div>
  );
}

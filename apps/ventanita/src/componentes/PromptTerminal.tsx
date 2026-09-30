import { type ReactNode, useEffect, useRef } from "react";
import { registrar } from "../registro";
import "./PromptTerminal.css";

interface Props {
  valor: string;
  deshabilitado: boolean;
  enfocar: boolean;
  onCambio: (texto: string) => void;
  onEnviar: () => void;
  // El chip de modelo, debajo del cuadro.
  chip: ReactNode;
}

export function PromptTerminal({
  valor,
  deshabilitado,
  enfocar,
  onCambio,
  onEnviar,
  chip,
}: Props) {
  const campoRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (enfocar) {
      campoRef.current?.focus();
    }
  }, [enfocar]);

  return (
    <div className="prompt-terminal">
      <div className="prompt-terminal__cuadro">
        <textarea
        ref={campoRef}
        className="code prompt-terminal__campo"
        aria-label="Escribile a Remi"
        value={valor}
        disabled={deshabilitado}
        placeholder="Contame."
        onChange={(evento) => onCambio(evento.target.value)}
        onKeyDown={(evento) => {
          if (evento.key !== "Enter") return;
          // Shift+Enter: salto de línea, como en cualquier chat. Enter solo o
          // con ⌘/Ctrl: envía. Los tres quedan en el log para ver cuál cayó.
          if (evento.shiftKey) {
            registrar("tecla", { tecla: "Shift+Enter", accion: "salto de línea" });
            return;
          }
          const combo = evento.metaKey ? "⌘↵" : evento.ctrlKey ? "Ctrl+Enter" : "Enter";
          registrar("tecla", { tecla: combo, accion: "enviar" });
          evento.preventDefault();
          onEnviar();
        }}
        />
      </div>
      <div className="prompt-terminal__pie">
        {/* El chip «Opus 5.5 · Medio»: con qué piensa Remi (maqueta de
            Juan Camilo). Lo arma el padre. */}
        {chip}
        <div className="prompt-terminal__atajos" aria-hidden="true">
          <span>↵ enviar</span>
          <span>·· hablar</span>
          <span>··· dialogar</span>
          <span>esc cancelar</span>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useRef } from "react";
import { registrar } from "../registro";
import "./PromptTerminal.css";

interface Props {
  valor: string;
  deshabilitado: boolean;
  enfocar: boolean;
  onCambio: (texto: string) => void;
  onEnviar: () => void;
  // Pensar con Claude: opt-in por mensaje, apagado por defecto.
  pensarConClaude: boolean;
  onAlternarPensar: () => void;
}

export function PromptTerminal({
  valor,
  deshabilitado,
  enfocar,
  onCambio,
  onEnviar,
  pensarConClaude,
  onAlternarPensar,
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
        {/* El único control del cuadro: la lavanda `pensar` prendida es
            Remi trabajando (con Claude). Apagado es texto en ink-muted. */}
        <button
          type="button"
          role="switch"
          aria-checked={pensarConClaude}
          className="prompt-terminal__pensar"
          data-activo={pensarConClaude ? "si" : "no"}
          disabled={deshabilitado}
          title="Solo este mensaje: Claude ordena el paso mínimo"
          onClick={onAlternarPensar}
        >
          <span className="prompt-terminal__pensar-punto" aria-hidden="true" />
          pensar con Claude
        </button>
        {/* Los gestos también se cuentan acá: dos clicks = hablar, tres =
            dialogar. Antes había que adivinarlos. */}
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

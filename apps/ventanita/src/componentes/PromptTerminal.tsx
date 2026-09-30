import { useEffect, useRef } from "react";
import { registrar } from "../registro";
import type { MotorDePensar } from "../servidor";
import "./PromptTerminal.css";

interface Props {
  valor: string;
  deshabilitado: boolean;
  enfocar: boolean;
  onCambio: (texto: string) => void;
  onEnviar: () => void;
  // Remi piensa siempre; «sin pensar» apaga el envío y queda puesto.
  sinPensar: boolean;
  onAlternarSinPensar: () => void;
  // Con qué motor, elegido a conciencia. Vacío mientras el núcleo no conteste.
  motores: MotorDePensar[];
  motor: string;
  onMotor: (motor: string) => void;
}

export function PromptTerminal({
  valor,
  deshabilitado,
  enfocar,
  onCambio,
  onEnviar,
  sinPensar,
  onAlternarSinPensar,
  motores,
  motor,
  onMotor,
}: Props) {
  const elegido = motores.find((m) => m.id === motor);
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
        {/* Remi piensa siempre con el motor del dropdown. «sin pensar» es
            la excepción y queda puesta hasta que la saques: nada sale del
            Mac. El punto `pensar` prendido = piensa; apagado = no. */}
        <span className="prompt-terminal__pensar" data-activo={sinPensar ? "no" : "si"} aria-hidden="true">
          <span className="prompt-terminal__pensar-punto" />
          piensa con
        </span>
        {/* El motor se elige a conciencia, acá, no en un .env. Un motor al
            que le falta algo se ve igual, apagado, y el título dice qué. */}
        <select
          className="prompt-terminal__motor"
          aria-label="Con qué motor pensar"
          title={elegido?.detalle ?? "El núcleo no contestó qué motores hay"}
          value={motor}
          disabled={deshabilitado}
          onChange={(evento) => {
            registrar("motor", { elegido: evento.target.value });
            onMotor(evento.target.value);
          }}
        >
          {motores.length === 0 && <option value={motor}>{motor}</option>}
          {motores.map((m) => (
            <option key={m.id} value={m.id} disabled={!m.disponible} title={m.detalle}>
              {m.label}
            </option>
          ))}
        </select>
        {/* Los gestos también se cuentan acá: dos clicks = hablar, tres =
            dialogar. Antes había que adivinarlos. */}
        <button
          type="button"
          role="switch"
          aria-checked={sinPensar}
          className="prompt-terminal__sin-pensar"
          data-activo={sinPensar ? "si" : "no"}
          disabled={deshabilitado}
          title="Sin pensar: no se manda nada al modelo; Remi solo guarda. Queda puesto."
          onClick={onAlternarSinPensar}
        >
          sin pensar
        </button>
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

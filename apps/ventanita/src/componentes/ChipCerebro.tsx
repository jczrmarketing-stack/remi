import { ChevronDown } from "lucide-react";
import {
  deValor,
  type EleccionCerebro,
  etiquetaDe,
  MODELOS_CLAUDE,
  NIVELES,
  valorDe,
} from "../preferencias";
import { registrar } from "../registro";
import type { MotorDePensar } from "../servidor";
import "./Chips.css";

interface Props {
  eleccion: EleccionCerebro;
  // Lo que dice el núcleo de cada motor (Venice sin clave, Ollama apagado).
  motores: MotorDePensar[];
  // `ollama list`, por el núcleo. Vacío si Ollama no está.
  modelosOllama: string[];
  onElegir: (eleccion: EleccionCerebro) => void;
}

/**
 * Abajo a la izquierda: con qué piensa Remi. Un solo menú nativo (se abre
 * fuera de la ventana, nunca lo corta): Claude modelo × nivel, los modelos
 * reales de Ollama y Venice (pago). El chip muestra «Sonnet · medio».
 */
export function ChipCerebro({ eleccion, motores, modelosOllama, onElegir }: Props) {
  const motor = (id: string) => motores.find((m) => m.id === id);
  const claudeOk = motor("claude")?.disponible ?? true;
  const veniceOk = motor("venice")?.disponible ?? false;
  const valor = valorDe(eleccion);
  // Si el guardado es un modelo de Ollama que ya no está, igual se muestra.
  const ollama = eleccion.motor === "ollama" && !modelosOllama.includes(eleccion.modelo)
    ? [...modelosOllama, eleccion.modelo]
    : modelosOllama;

  return (
    <label className="chip" title={motor(eleccion.motor)?.detalle ?? "Con qué piensa Remi"}>
      <span className="body-sm chip__texto">{etiquetaDe(eleccion)}</span>
      <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" className="chip__flecha" />
      <select
        aria-label="Con qué piensa Remi"
        value={valor}
        onChange={(evento) => {
          const nueva = deValor(evento.target.value);
          if (!nueva) return;
          registrar("cerebro", { elegido: evento.target.value });
          onElegir(nueva);
        }}
      >
        <optgroup label={claudeOk ? "Claude · Max" : "Claude · Max (no disponible)"}>
          {MODELOS_CLAUDE.flatMap((modelo) =>
            NIVELES.map((nivel) => {
              const opcion: EleccionCerebro = { motor: "claude", modelo, nivel };
              return (
                <option key={valorDe(opcion)} value={valorDe(opcion)} disabled={!claudeOk}>
                  {etiquetaDe(opcion)}
                </option>
              );
            }),
          )}
        </optgroup>
        <optgroup label={ollama.length > 0 ? "Ollama · gratis, local" : "Ollama (no está corriendo)"}>
          {ollama.map((modelo) => (
            <option key={modelo} value={valorDe({ motor: "ollama", modelo })}>
              {modelo}
            </option>
          ))}
        </optgroup>
        <optgroup label="Venice">
          <option value="venice" disabled={!veniceOk}>
            {veniceOk ? "Venice (pago)" : `Venice (pago) — ${motor("venice")?.detalle ?? "no disponible"}`}
          </option>
        </optgroup>
      </select>
    </label>
  );
}

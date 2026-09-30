import { Volume2 } from "lucide-react";
import { VELOCIDADES, VOZ_AUTOMATICA, type PreferenciaVoz, type Velocidad } from "../preferencias";
import { registrar } from "../registro";
import type { VozDisponible } from "../voz";
import "./ChipModelo.css";

// «em_alex» → «Alex», por si la lista del núcleo todavía no llegó.
export function nombreLegible(id: string): string {
  const sinPrefijo = id.replace(/^[a-z]{2}_/, "");
  return sinPrefijo.charAt(0).toUpperCase() + sinPrefijo.slice(1);
}

interface Props {
  velocidad: Velocidad;
  onVelocidad: (velocidad: Velocidad) => void;
  voces: VozDisponible[];
  voz: PreferenciaVoz;
  onVoz: (voz: PreferenciaVoz) => void;
}

/**
 * Al lado del chip de modelo: con qué voz y a qué velocidad lee Remi.
 * Un click en la velocidad pasa a la siguiente (1× → 1,5× → 2×).
 */
export function AjustesVoz({ velocidad, onVelocidad, voces, voz, onVoz }: Props) {
  const nombre = voz === VOZ_AUTOMATICA ? "Auto" : (voces.find((v) => v.id === voz)?.label ?? nombreLegible(voz));
  const siguiente = VELOCIDADES[(VELOCIDADES.indexOf(velocidad) + 1) % VELOCIDADES.length];
  return (
    <div className="chip-modelo ajustes-voz">
      <label className="chip-modelo__parte chip-modelo__modelo" title="Voz de Remi">
        <Volume2 size={14} strokeWidth={1.75} aria-hidden="true" />
        <span className="body-sm">{nombre}</span>
        <select
          aria-label="Voz de Remi"
          value={voz}
          onChange={(evento) => {
            registrar("voz", { elegida: evento.target.value });
            onVoz(evento.target.value);
          }}
        >
          <option value={VOZ_AUTOMATICA}>Auto</option>
          {voces.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="chip-modelo__parte chip-modelo__nivel ajustes-voz__velocidad"
        title={`Velocidad de la voz: ${velocidad}×. Click: ${siguiente}×`}
        aria-label={`Velocidad de la voz ${velocidad}×, cambiar a ${siguiente}×`}
        onClick={() => {
          registrar("velocidad", { elegida: siguiente });
          onVelocidad(siguiente);
        }}
      >
        <span className="num">{`${velocidad}×`}</span>
      </button>
    </div>
  );
}

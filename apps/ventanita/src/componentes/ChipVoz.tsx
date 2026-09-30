import { ChevronDown } from "lucide-react";
import { VELOCIDADES, type PreferenciaVoz, type Velocidad } from "../preferencias";
import { registrar } from "../registro";
import type { VozDisponible } from "../voz";
import "./Chips.css";

interface Props {
  voz: PreferenciaVoz;
  velocidad: Velocidad;
  voces: VozDisponible[];
  onElegir: (voz: PreferenciaVoz, velocidad: Velocidad) => void;
}

// «em_alex» → «Alex», por si la lista del núcleo todavía no llegó.
export function nombreLegible(id: string): string {
  const sinPrefijo = id.replace(/^[a-z]{2}_/, "");
  return sinPrefijo.charAt(0).toUpperCase() + sinPrefijo.slice(1);
}

// «Alex (ES)» → «Alex».
function nombreCorto(voz: VozDisponible): string {
  return voz.label.replace(/\s*\(.*\)\s*$/, "") || nombreLegible(voz.id);
}

const formatear = (v: Velocidad) => `${String(v).replace(".", ",")}×`;

/**
 * Abajo a la derecha: la voz de Remi y su velocidad, en un solo menú. El
 * chip muestra «Alex · 1,5×».
 */
export function ChipVoz({ voz, velocidad, voces, onElegir }: Props) {
  const actual = voces.find((v) => v.id === voz);
  const nombre = actual ? nombreCorto(actual) : nombreLegible(voz);
  const lista = actual || voces.length === 0 ? voces : [...voces, { id: voz, lang: "", label: nombreLegible(voz) }];

  return (
    <label className="chip" title="Voz de Remi y velocidad">
      <span className="body-sm chip__texto">{`${nombre} · ${formatear(velocidad)}`}</span>
      <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" className="chip__flecha" />
      <select
        aria-label="Voz de Remi y velocidad"
        value={`${voz}|${velocidad}`}
        onChange={(evento) => {
          const [nuevaVoz, nuevaVelocidad] = evento.target.value.split("|");
          registrar("voz", { voz: nuevaVoz, velocidad: nuevaVelocidad });
          onElegir(nuevaVoz, Number(nuevaVelocidad) as Velocidad);
        }}
      >
        {lista.length === 0 && <option value={`${voz}|${velocidad}`}>{`${nombre} · ${formatear(velocidad)}`}</option>}
        {lista.map((v) => (
          <optgroup key={v.id} label={nombreCorto(v)}>
            {VELOCIDADES.map((vel) => (
              <option key={vel} value={`${v.id}|${vel}`}>
                {`${nombreCorto(v)} · ${formatear(vel)}`}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  );
}

import { Check, Copy, Volume2 } from "lucide-react";
import { VELOCIDADES, VOZ_AUTOMATICA, type PreferenciaVoz, type Velocidad } from "../preferencias";
import type { VozDisponible } from "../voz";
import "./ControlesVoz.css";

interface Props {
  velocidad: Velocidad;
  onVelocidad: (velocidad: Velocidad) => void;
  // Leer en voz alta a demanda: solo cuando escribiste (si hablaste,
  // Remi ya contestó en voz).
  puedeLeer: boolean;
  onLeer: () => void;
  onCopiar: () => void;
  copiado: boolean;
  // true mientras el puntero está encima: App no cierra la respuesta.
  onSostener: (sostenido: boolean) => void;
  // Con quién habla Remi. Vacío mientras el núcleo no conteste: ahí solo
  // queda "Auto", que es lo que hace igual.
  voces: VozDisponible[];
  voz: PreferenciaVoz;
  onVoz: (voz: PreferenciaVoz) => void;
}

const ICONO = { size: 16, strokeWidth: 1.75 } as const;

function etiqueta(velocidad: Velocidad): string {
  return `${velocidad}×`;
}

/**
 * Controles chicos debajo de la respuesta de Remi. Viven en `num`, en
 * ink-muted salvo el activo: la locura de la pantalla es la frase, no
 * esto (ley 4). Los clicks acá no cierran la ventanita: el contenedor
 * lleva la clase `controles-voz` y App los deja pasar.
 */
export function ControlesVoz({
  velocidad,
  onVelocidad,
  puedeLeer,
  onLeer,
  onCopiar,
  copiado,
  onSostener,
  voces,
  voz,
  onVoz,
}: Props) {
  return (
    <div
      className="controles-voz"
      onClick={(evento) => evento.stopPropagation()}
      onMouseEnter={() => onSostener(true)}
      onMouseLeave={() => onSostener(false)}
    >
      {puedeLeer && (
        <button
          type="button"
          className="controles-voz__icono"
          aria-label="Leer en voz alta"
          title="Leer en voz alta"
          onClick={onLeer}
        >
          <Volume2 {...ICONO} />
        </button>
      )}
      <button
        type="button"
        className="controles-voz__icono"
        data-hecho={copiado ? "si" : "no"}
        aria-label={copiado ? "Copiado" : "Copiar lo que dijiste y la respuesta"}
        title={copiado ? "Copiado" : "Copiar lo que dijiste y la respuesta"}
        onClick={onCopiar}
      >
        {copiado ? <Check {...ICONO} /> : <Copy {...ICONO} />}
      </button>
      <select
        className="num controles-voz__voz"
        aria-label="Voz de Remi"
        title="Voz de Remi"
        value={voz}
        onChange={(evento) => onVoz(evento.target.value)}
      >
        <option value={VOZ_AUTOMATICA}>Auto</option>
        {voces.map((disponible) => (
          <option key={disponible.id} value={disponible.id}>
            {disponible.label}
          </option>
        ))}
      </select>
      <div className="controles-voz__velocidad" role="radiogroup" aria-label="Velocidad de la voz">
        {VELOCIDADES.map((opcion) => (
          <button
            key={opcion}
            type="button"
            role="radio"
            aria-checked={opcion === velocidad}
            className="num controles-voz__opcion"
            data-activa={opcion === velocidad ? "si" : "no"}
            title={`Leer a ${etiqueta(opcion)}`}
            onClick={() => onVelocidad(opcion)}
          >
            {etiqueta(opcion)}
          </button>
        ))}
      </div>
    </div>
  );
}

import { VELOCIDADES, type Velocidad } from "../preferencias";
import "./ControlesVoz.css";

interface Props {
  velocidad: Velocidad;
  onVelocidad: (velocidad: Velocidad) => void;
}

function etiqueta(velocidad: Velocidad): string {
  return `${velocidad}×`;
}

/**
 * Controles chicos debajo de la respuesta de Remi. Viven en `num`, en
 * ink-faint salvo el activo: la locura de la pantalla es la frase, no
 * esto (ley 4). Los clicks acá no cierran la ventanita: el contenedor
 * lleva la clase `controles-voz` y App los deja pasar.
 */
export function ControlesVoz({ velocidad, onVelocidad }: Props) {
  return (
    <div className="controles-voz" onClick={(evento) => evento.stopPropagation()}>
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

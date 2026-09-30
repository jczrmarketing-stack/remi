import { useEffect, useState } from "react";
import { Check, Copy, RotateCw, Square, Volume2 } from "lucide-react";
import { vozOcupada } from "../voz";
import "./AccionesRespuesta.css";

interface Props {
  texto: string;
  onEscuchar: () => void;
  onCallar: () => void;
  // true si se pudo copiar: el ícono pasa a ✓.
  onCopiar: () => Promise<boolean>;
  // Solo la última respuesta se puede pedir de nuevo.
  onReintentar?: () => void;
}

const ICONO = { size: 16, strokeWidth: 1.75 } as const;
// Cada cuánto se mira si Remi sigue hablando, para cambiar escuchar ↔ parar.
const MS_MIRAR_VOZ = 200;

/**
 * Debajo de cada respuesta, como en Claude: escucharla (o pararla), copiarla
 * y pedir otra. Íconos chicos en ink-muted: la respuesta manda (ley 4).
 */
export function AccionesRespuesta({ texto, onEscuchar, onCallar, onCopiar, onReintentar }: Props) {
  const [hablando, setHablando] = useState(() => vozOcupada());
  const [copiado, setCopiado] = useState(false);
  useEffect(() => setCopiado(false), [texto]);

  useEffect(() => {
    const id = window.setInterval(() => setHablando(vozOcupada()), MS_MIRAR_VOZ);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="acciones-respuesta" onClick={(evento) => evento.stopPropagation()}>
      <button
        type="button"
        className="acciones-respuesta__boton"
        aria-label={hablando ? "Parar la voz" : "Escuchar la respuesta"}
        title={hablando ? "Parar" : "Escuchar"}
        onClick={hablando ? onCallar : onEscuchar}
      >
        {hablando ? <Square {...ICONO} /> : <Volume2 {...ICONO} />}
      </button>
      <button
        type="button"
        className="acciones-respuesta__boton"
        data-hecho={copiado ? "si" : "no"}
        aria-label={copiado ? "Copiada" : "Copiar la respuesta"}
        title={copiado ? "Copiada" : "Copiar"}
        onClick={() => void onCopiar().then(setCopiado)}
      >
        {copiado ? <Check {...ICONO} /> : <Copy {...ICONO} />}
      </button>
      {onReintentar && (
        <button
          type="button"
          className="acciones-respuesta__boton"
          aria-label="Pedir otra respuesta"
          title="Otra respuesta"
          onClick={onReintentar}
        >
          <RotateCw {...ICONO} />
        </button>
      )}
    </div>
  );
}

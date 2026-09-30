import { useEffect, useState } from "react";
import { Check, Copy, RotateCw, Square, Volume2 } from "lucide-react";
import { vozOcupada } from "../voz";
import "./AccionesRespuesta.css";

interface Props {
  onEscuchar: () => void;
  onCallar: () => void;
  onCopiar: () => void;
  copiado: boolean;
  onReintentar: () => void;
}

const ICONO = { size: 16, strokeWidth: 1.75 } as const;
// Cada cuánto se mira si Remi sigue hablando, para cambiar escuchar ↔ parar.
const MS_MIRAR_VOZ = 200;

/**
 * Debajo de cada respuesta, como en Claude: escucharla (o pararla), copiarla
 * y pedir otra. Íconos chicos en ink-muted: la respuesta manda (ley 4).
 */
export function AccionesRespuesta({ onEscuchar, onCallar, onCopiar, copiado, onReintentar }: Props) {
  const [hablando, setHablando] = useState(() => vozOcupada());

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
        onClick={onCopiar}
      >
        {copiado ? <Check {...ICONO} /> : <Copy {...ICONO} />}
      </button>
      <button
        type="button"
        className="acciones-respuesta__boton"
        aria-label="Pedir otra respuesta"
        title="Otra respuesta"
        onClick={onReintentar}
      >
        <RotateCw {...ICONO} />
      </button>
    </div>
  );
}

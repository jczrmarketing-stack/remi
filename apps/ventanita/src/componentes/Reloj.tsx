import "./Reloj.css";

interface Props {
  minutosTranscurridos: number;
  ultimaVezMin: number;
}

/**
 * Reloj, piel brasa: la única que usa Fase 1. Existe solo mientras corre
 * un bloque — brasa es "el bloque en curso" (design/tokens.json). El
 * relleno es tiempo real de la sesión en curso sobre ultima_vez_min
 * (ley 1 hecha visible) — nunca un número inventado. El padre decide
 * cuándo montarlo (solo si hay ultima_vez_min) y no lo hace por menos.
 */
export function Reloj({ minutosTranscurridos, ultimaVezMin }: Props) {
  const porcentaje = Math.min(
    100,
    Math.max(0, (minutosTranscurridos / Math.max(1, ultimaVezMin)) * 100),
  );
  return (
    <div
      className="reloj reloj--brasa"
      role="img"
      aria-label={`Llevas ${Math.round(minutosTranscurridos)} minutos; la última vez tardaste ${ultimaVezMin}`}
    >
      <div className="reloj__relleno" style={{ width: `${porcentaje}%` }} />
    </div>
  );
}

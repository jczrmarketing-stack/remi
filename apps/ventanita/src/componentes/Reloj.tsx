import "./Reloj.css";

/**
 * Reloj, piel brasa: la única que usa Fase 1. Existe solo mientras corre
 * un bloque — brasa es "el bloque en curso" (design/tokens.json). El padre
 * decide cuándo montarlo; este componente no conoce estados.
 */
export function Reloj() {
  return (
    <div className="reloj reloj--brasa" role="img" aria-label="Bloque en curso">
      <div className="reloj__relleno" />
    </div>
  );
}

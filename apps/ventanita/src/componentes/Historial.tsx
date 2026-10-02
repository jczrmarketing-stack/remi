import { etiquetaDeFecha } from "../historial";
import type { ConversacionDeAntes } from "../servidor";
import "./Historial.css";

interface Props {
  abierto: boolean;
  conversaciones: ConversacionDeAntes[];
  ahoraMs: number;
  onAbrir: () => void;
  onCerrar: () => void;
  onElegir: (id: string) => void;
  onNueva: () => void;
}

// Un triángulo en el borde izquierdo y nada más. Abierto, el cajón sale por
// la izquierda con una sola lista: la más reciente arriba, sin carpetas.
export function Historial({ abierto, conversaciones, ahoraMs, onAbrir, onCerrar, onElegir, onNueva }: Props) {
  return (
    <>
      {!abierto && (
        <button type="button" className="historial__triangulo" aria-label="Conversaciones de antes" onClick={onAbrir}>
          <svg width="8" height="12" viewBox="0 0 8 12" aria-hidden="true">
            <path d="M1 1 L7 6 L1 11 Z" fill="currentColor" />
          </svg>
        </button>
      )}
      <aside className={`historial${abierto ? " historial--abierto" : ""}`} aria-hidden={!abierto} inert={!abierto}>
        <div className="historial__cabeza">
          <span className="label">Antes</span>
          <button type="button" className="historial__nueva" onClick={onNueva}>
            Empezar de cero
          </button>
        </div>
        <ul className="historial__lista">
          {conversaciones.length === 0 && <li className="historial__vacio">Aquí van a quedar tus conversaciones.</li>}
          {conversaciones.map((c) => (
            <li key={c.id}>
              <button type="button" className="historial__fila" onClick={() => onElegir(c.id)}>
                <span className="historial__titulo">{c.titulo}</span>
                <span className="num historial__fecha">
                  {etiquetaDeFecha(c.ultimo, ahoraMs)}
                  {c.tema ? ` · ${c.tema}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
        <button type="button" className="historial__cerrar" onClick={onCerrar} aria-label="Cerrar el historial">
          <svg width="8" height="12" viewBox="0 0 8 12" aria-hidden="true">
            <path d="M7 1 L1 6 L7 11 Z" fill="currentColor" />
          </svg>
        </button>
      </aside>
    </>
  );
}

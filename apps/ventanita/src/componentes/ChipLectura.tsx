import { useEffect, useRef, useState } from "react";
import type { Lectura } from "../lectura";
import { registrar } from "../registro";
import "./Chips.css";
import "./ChipLectura.css";

interface Props {
  lectura: Lectura;
  onCambiar: (cambio: Partial<Lectura>) => void;
}

/**
 * «Aa»: cómo se lee Remi. Un panel chico, arriba del pie: tema Noche o
 * Claro, lectura biónica sí o no, y su intensidad (suave ↔ fuerte). Un
 * deslizador no entra en un menú nativo; por eso este sí es un panel.
 */
export function ChipLectura({ lectura, onCambiar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    const afuera = (evento: MouseEvent) => {
      if (!raiz.current?.contains(evento.target as Node)) setAbierto(false);
    };
    const tecla = (evento: KeyboardEvent) => {
      if (evento.key !== "Escape") return;
      // Escape cierra el panel y no llega a cancelar a Remi.
      evento.stopPropagation();
      setAbierto(false);
    };
    window.addEventListener("mousedown", afuera, true);
    window.addEventListener("keydown", tecla, true);
    return () => {
      window.removeEventListener("mousedown", afuera, true);
      window.removeEventListener("keydown", tecla, true);
    };
  }, [abierto]);

  const cambiar = (cambio: Partial<Lectura>) => {
    registrar("lectura", cambio);
    onCambiar(cambio);
  };

  return (
    <div className="lectura" ref={raiz}>
      <button
        type="button"
        className="chip lectura__chip"
        aria-haspopup="dialog"
        aria-expanded={abierto}
        title="Lectura: tema y lectura biónica"
        onClick={() => setAbierto((v) => !v)}
      >
        <span className="body-sm chip__texto">Aa</span>
      </button>
      {abierto && (
        <div className="lectura__panel" role="dialog" aria-label="Lectura">
          <div className="lectura__fila">
            <span className="body-sm">Tema</span>
            <div className="lectura__segmentos" role="radiogroup" aria-label="Tema">
              {(["noche", "claro"] as const).map((tema) => (
                <button
                  key={tema}
                  type="button"
                  role="radio"
                  aria-checked={lectura.tema === tema}
                  className="body-sm lectura__segmento"
                  data-activo={lectura.tema === tema ? "si" : "no"}
                  onClick={() => cambiar({ tema })}
                >
                  {tema === "noche" ? "Noche" : "Claro"}
                </button>
              ))}
            </div>
          </div>
          <label className="lectura__fila">
            <span className="body-sm">Lectura biónica</span>
            <input
              type="checkbox"
              className="lectura__interruptor"
              checked={lectura.bionica}
              onChange={(evento) => cambiar({ bionica: evento.target.checked })}
            />
          </label>
          <label className="lectura__fila lectura__fila--columna" data-apagada={lectura.bionica ? "no" : "si"}>
            <span className="body-sm lectura__etiqueta">
              <span>Suave</span>
              <span>Fuerte</span>
            </span>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              disabled={!lectura.bionica}
              aria-label="Intensidad de la lectura biónica"
              value={Math.round(lectura.intensidad * 100)}
              onChange={(evento) => cambiar({ intensidad: Number(evento.target.value) / 100 })}
            />
          </label>
        </div>
      )}
    </div>
  );
}

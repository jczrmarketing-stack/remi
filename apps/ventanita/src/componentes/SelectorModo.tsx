import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { MODOS, type ModoPensar } from "../preferencias";
import { registrar } from "../registro";
import { IconoModo } from "./IconosModo";
import "./SelectorModo.css";

const ETIQUETA: Record<ModoPensar, string> = {
  rapido: "Rápido",
  equilibrio: "Equilibrio",
  inteligente: "Inteligente",
};

const DETALLE: Record<ModoPensar, string> = {
  rapido: "Haiku · 1–3 s",
  equilibrio: "Sonnet · el de siempre",
  inteligente: "Opus · piensa antes",
};

interface Props {
  modo: ModoPensar;
  onModo: (modo: ModoPensar) => void;
}

/**
 * La flechita junto al punto (ARQUITECTURA-CEREBRO §11, 3b). Aparece al
 * acercar el mouse al punto; despliega los modos, cada uno con su ícono.
 * Es un control: un click acá nunca es un gesto de Remi.
 */
export function SelectorModo({ modo, onModo }: Props) {
  const [abierto, setAbierto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);

  // Click afuera o Escape cierran el menú (Escape no llega a cancelar a
  // Remi: se lo come el menú mientras está abierto).
  useEffect(() => {
    if (!abierto) return;
    const alClickAfuera = (evento: MouseEvent) => {
      if (!raiz.current?.contains(evento.target as Node)) setAbierto(false);
    };
    const alTeclado = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") {
        evento.stopPropagation();
        setAbierto(false);
      }
    };
    window.addEventListener("mousedown", alClickAfuera, true);
    window.addEventListener("keydown", alTeclado, true);
    return () => {
      window.removeEventListener("mousedown", alClickAfuera, true);
      window.removeEventListener("keydown", alTeclado, true);
    };
  }, [abierto]);

  return (
    <div className="selector-modo" ref={raiz} data-abierto={abierto ? "si" : "no"}>
      <button
        type="button"
        className="selector-modo__flecha"
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-label={`Modo: ${ETIQUETA[modo]}. Cambiar`}
        title={`Modo: ${ETIQUETA[modo]}`}
        onClick={(evento) => {
          evento.stopPropagation();
          setAbierto((valor) => !valor);
        }}
      >
        <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" />
      </button>
      {abierto && (
        <div className="selector-modo__menu" role="menu" aria-label="Modo de pensar">
          {MODOS.map((opcion) => (
            <button
              key={opcion}
              type="button"
              role="menuitemradio"
              aria-checked={opcion === modo}
              className="selector-modo__opcion"
              data-activa={opcion === modo ? "si" : "no"}
              onClick={(evento) => {
                evento.stopPropagation();
                registrar("modo", { elegido: opcion, desde: "flecha" });
                onModo(opcion);
                setAbierto(false);
              }}
            >
              <IconoModo modo={opcion} />
              <span className="body-sm">{ETIQUETA[opcion]}</span>
              <span className="num selector-modo__detalle">{DETALLE[opcion]}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

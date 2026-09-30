import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { copiarAlPortapapeles } from "../portapapeles";
import { registrar } from "../registro";
import "./Encargo.css";

interface Props {
  texto: string;
}

/**
 * El modo Prompt: lo dicho vuelve ordenado como un encargo de UNA tarea
 * para Claude Code. Se lee línea a línea, así que va en Geist Mono (`code`,
 * el único sitio del DS donde se lee así) sobre `surface`, con un botón
 * que lo copia. No se cierra solo: se copia y se sigue.
 */
export function Encargo({ texto }: Props) {
  const [copiado, setCopiado] = useState(false);
  return (
    <div className="encargo">
      <pre className="code encargo__texto">{texto}</pre>
      <button
        type="button"
        className="body-sm encargo__copiar"
        data-hecho={copiado ? "si" : "no"}
        onClick={async (evento) => {
          evento.stopPropagation();
          const pudo = await copiarAlPortapapeles(texto);
          registrar("encargo:copiar", { pudo, caracteres: texto.length });
          if (pudo) setCopiado(true);
        }}
      >
        {copiado ? <Check size={16} strokeWidth={1.75} aria-hidden="true" /> : <Copy size={16} strokeWidth={1.75} aria-hidden="true" />}
        {copiado ? "Copiado" : "Copiar"}
      </button>
    </div>
  );
}

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { registrar } from "../registro";
import "./Campo.css";

interface Props {
  valor: string;
  onCambio: (texto: string) => void;
  onEnviar: () => void;
  // Lo que se pegó, si fue largo (el padre decide qué preguntar).
  onPegarLargo: (texto: string) => void;
  deshabilitado?: boolean;
}

export interface CampoRef {
  enfocar: () => void;
}

// Pegar más que esto pregunta si se guarda como conversación (3c · 7).
export const LARGO_PARA_EPISODIO = 1500;
// Crece con el texto hasta este alto; después se desplaza adentro.
const ALTO_MAXIMO_PX = 140;

/**
 * El campo de escribir no es una caja: es el borde de abajo de la misma
 * superficie, sin marco ni fondo propio. Enter envía; Shift+Enter, salto.
 */
export const Campo = forwardRef<CampoRef, Props>(function Campo(
  { valor, onCambio, onEnviar, onPegarLargo, deshabilitado = false },
  ref,
) {
  const area = useRef<HTMLTextAreaElement>(null);
  useImperativeHandle(ref, () => ({ enfocar: () => area.current?.focus() }), []);

  // Alto automático: se mide el contenido cada vez que cambia.
  useEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(ALTO_MAXIMO_PX, el.scrollHeight)}px`;
  }, [valor]);

  return (
    <textarea
      ref={area}
      className="body-sm campo"
      aria-label="Escribile a Remi"
      placeholder="Contame."
      rows={1}
      value={valor}
      disabled={deshabilitado}
      onChange={(evento) => onCambio(evento.target.value)}
      onPaste={(evento) => {
        const pegado = evento.clipboardData.getData("text");
        if (pegado.length > LARGO_PARA_EPISODIO) {
          registrar("pegar", { caracteres: pegado.length });
          onPegarLargo(pegado);
        }
      }}
      onKeyDown={(evento) => {
        if (evento.key !== "Enter" || evento.nativeEvent.isComposing) return;
        if (evento.shiftKey) return; // salto de línea
        evento.preventDefault();
        registrar("tecla", { tecla: "Enter", accion: "enviar" });
        onEnviar();
      }}
    />
  );
});

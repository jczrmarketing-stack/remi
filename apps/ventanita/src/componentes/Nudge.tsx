import { Fragment, useEffect } from "react";
import { partirBionica } from "../bionica";
import { respuestaDeTecla, type RespuestaNudge } from "../nudges";
import "./Nudge.css";

interface Props {
  voz: string;
  onResponder: (respuesta: RespuestaNudge) => void;
  // Lectura biónica (3f · 9): también en el nudge, nunca en el código.
  bionica?: number | null;
}

/**
 * Nudge (componente canónico del DS): un mensaje de Remi con dos píldoras,
 * «Listo» / «Ahora no». Ley 5: la salida es siempre amable y no cuenta como
 * fallo — «Ahora no» no queda registrado en ningún lado como un incumplido.
 * Sin sonido: el nudge se ve, no suena.
 */
function campoConTexto(objetivo: EventTarget | null): boolean {
  return (
    (objetivo instanceof HTMLTextAreaElement || objetivo instanceof HTMLInputElement) && objetivo.value.trim() !== ""
  );
}

export function Nudge({ voz, onResponder, bionica }: Props) {
  useEffect(() => {
    function alTeclado(evento: KeyboardEvent) {
      const respuesta = respuestaDeTecla(evento.key, campoConTexto(evento.target));
      if (!respuesta) return;
      evento.preventDefault();
      onResponder(respuesta);
    }
    window.addEventListener("keydown", alTeclado);
    return () => window.removeEventListener("keydown", alTeclado);
  }, [onResponder]);

  return (
    <div className="nudge" role="status">
      <p className="display-it nudge__voz">
        {bionica != null
          ? partirBionica(voz).map((trozo, i) =>
              trozo.tipo === "ancla" ? (
                <b key={i} className="bio-ancla">
                  {trozo.texto}
                </b>
              ) : (
                <Fragment key={i}>{trozo.texto}</Fragment>
              ),
            )
          : voz}
      </p>
      <div className="nudge__pildoras">
        <button type="button" className="body-sm nudge__pildora" onClick={() => onResponder("listo")}>
          Listo
        </button>
        <button type="button" className="body-sm nudge__pildora nudge__pildora--suave" onClick={() => onResponder("ahora_no")}>
          Ahora no
        </button>
      </div>
    </div>
  );
}

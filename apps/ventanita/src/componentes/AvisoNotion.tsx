import { bloquesDelAviso, type AvisoDeNotion, type RespuestaAvisoNotion } from "../avisoNotion";
import "./Nudge.css";
import "./AvisoNotion.css";

interface Props {
  aviso: AvisoDeNotion;
  saliendo: boolean;
  onResponder: (respuesta: RespuestaAvisoNotion) => void;
}

/**
 * Aviso de Notion: el «Qué» y su paso mínimo, con las dos píldoras del Nudge
 * («Listo» / «Ahora no», que nunca cuenta como fallo — ley 5). Entra
 * deslizándose desde el borde derecho de la pantalla. Solo se contesta con el
 * mouse: sin Enter ni Escape, para que una tecla que ibas a darle a otra cosa
 * no marque una tarea como hecha.
 */
export function AvisoNotion({ aviso, saliendo, onResponder }: Props) {
  return (
    <div className={`aviso-notion${saliendo ? " aviso-notion--sale" : ""}`}>
      <div className="nudge aviso-notion__tarjeta" data-tipo="ritual" role="status" aria-live="polite">
        <div className="aviso-notion__textos">
          {bloquesDelAviso(aviso).map((bloque, i) => (
            <div key={i} className="aviso-notion__bloque">
              {bloque.rotulo && <p className="body-sm aviso-notion__rotulo">{bloque.rotulo}</p>}
              <p className={bloque.fuerte ? "display-it aviso-notion__fuerte" : "body-sm aviso-notion__suave"}>
                {bloque.texto}
              </p>
            </div>
          ))}
        </div>
        <div className="nudge__pildoras">
          <button type="button" className="body-sm nudge__pildora" onClick={() => onResponder("listo")}>
            Listo
          </button>
          <button type="button" className="body-sm nudge__pildora nudge__pildora--suave" onClick={() => onResponder("ahora_no")}>
            Ahora no
          </button>
        </div>
      </div>
    </div>
  );
}

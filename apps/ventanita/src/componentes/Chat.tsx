import { useEffect, useRef } from "react";
import { partirRespuesta, type Parte } from "../markdown";
import { Encargo } from "./Encargo";
import { AccionesRespuesta } from "./AccionesRespuesta";
import "./Chat.css";

export interface Mensaje {
  id: string;
  rol: "juan" | "remi";
  texto: string;
  // Una pregunta de Remi con Sí/No (pegar una charla larga).
  pregunta?: { onSi: () => void; onNo: () => void };
}

interface Props {
  mensajes: Mensaje[];
  onEscuchar: (texto: string) => void;
  onCallar: () => void;
  onCopiar: (texto: string) => Promise<boolean>;
  onReintentar: () => void;
  onEnlace: (url: string) => void;
}

function Partes({ partes, onEnlace }: { partes: Parte[]; onEnlace: (url: string) => void }) {
  return (
    <>
      {partes.map((parte, i) =>
        parte.tipo === "texto" ? (
          <span key={i}>{parte.texto}</span>
        ) : (
          <a
            key={i}
            className="chat__enlace"
            href={parte.url}
            title={parte.url}
            onClick={(evento) => {
              evento.preventDefault();
              evento.stopPropagation();
              onEnlace(parte.url);
            }}
          >
            {parte.texto}
          </a>
        ),
      )}
    </>
  );
}

function MensajeDeRemi({ mensaje, ultimo, ...acciones }: Omit<Props, "mensajes"> & { mensaje: Mensaje; ultimo: boolean }) {
  const bloques = partirRespuesta(mensaje.texto);
  return (
    <div className="chat__mensaje chat__mensaje--remi" data-ultimo={ultimo ? "si" : "no"}>
      {bloques.map((bloque, i) =>
        bloque.tipo === "encargo" ? (
          <Encargo key={i} texto={bloque.texto} />
        ) : (
          <p key={i} className="display-it chat__remi">
            <Partes partes={bloque.partes} onEnlace={acciones.onEnlace} />
          </p>
        ),
      )}
      {mensaje.pregunta ? (
        <div className="chat__pregunta">
          <button type="button" className="body-sm chat__opcion" onClick={mensaje.pregunta.onSi}>
            Sí
          </button>
          <button type="button" className="body-sm chat__opcion" onClick={mensaje.pregunta.onNo}>
            No
          </button>
        </div>
      ) : (
        <AccionesRespuesta
          texto={mensaje.texto}
          onEscuchar={() => acciones.onEscuchar(mensaje.texto)}
          onCallar={acciones.onCallar}
          onCopiar={() => acciones.onCopiar(mensaje.texto)}
          onReintentar={ultimo ? acciones.onReintentar : undefined}
        />
      )}
    </div>
  );
}

/**
 * La conversación como chat: Remi a la izquierda en su voz (Instrument Serif
 * itálica), Juan Camilo a la derecha en Geist. Baja sola al último mensaje.
 */
export function Chat({ mensajes, ...acciones }: Props) {
  const fondo = useRef<HTMLDivElement>(null);
  useEffect(() => {
    fondo.current?.scrollIntoView({ block: "end" });
  }, [mensajes]);

  return (
    <div className="chat" aria-live="polite">
      {mensajes.map((mensaje, i) =>
        mensaje.rol === "juan" ? (
          <div key={mensaje.id} className="chat__mensaje chat__mensaje--juan">
            <p className="body-sm chat__juan">{mensaje.texto}</p>
          </div>
        ) : (
          <MensajeDeRemi key={mensaje.id} mensaje={mensaje} ultimo={i === mensajes.length - 1} {...acciones} />
        ),
      )}
      <div ref={fondo} />
    </div>
  );
}

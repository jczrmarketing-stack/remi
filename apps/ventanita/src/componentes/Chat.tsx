import { type CSSProperties, Fragment, useEffect, useRef } from "react";
import { partirBionica, perillasBionica } from "../bionica";
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
  // Lectura biónica: la intensidad (0–1), o null si está apagada. Solo en lo
  // que escribe Remi; nunca en botones, campos ni en la tarjeta de código.
  bionica?: number | null;
}

function Bionico({ texto }: { texto: string }) {
  return (
    <>
      {partirBionica(texto).map((trozo, i) =>
        trozo.tipo === "ancla" ? (
          <b key={i} className="bio-ancla">
            {trozo.texto}
          </b>
        ) : trozo.tipo === "resto" ? (
          <span key={i} className="bio-resto">
            {trozo.texto}
          </span>
        ) : (
          <Fragment key={i}>{trozo.texto}</Fragment>
        ),
      )}
    </>
  );
}

function Partes({ partes, onEnlace, bionica }: { partes: Parte[]; onEnlace: (url: string) => void; bionica: boolean }) {
  return (
    <>
      {partes.map((parte, i) =>
        parte.tipo === "texto" ? (
          <span key={i}>{bionica ? <Bionico texto={parte.texto} /> : parte.texto}</span>
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
            <Partes partes={bloque.partes} onEnlace={acciones.onEnlace} bionica={acciones.bionica != null} />
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

  const perillas = acciones.bionica != null ? perillasBionica(acciones.bionica) : null;
  const estilo = perillas
    ? ({
        "--bio-peso": perillas.pesoAncla,
        "--bio-tinta": `${perillas.tintaResto}%`,
        "--bio-interlineado": perillas.interlineado,
      } as CSSProperties)
    : undefined;

  return (
    <div className="chat" aria-live="polite" data-bionica={perillas ? "si" : "no"} style={estilo}>
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

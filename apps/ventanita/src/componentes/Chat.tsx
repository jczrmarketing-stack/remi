import { type CSSProperties, Fragment, useEffect, useRef, useState } from "react";
import { partirBionica, perillasBionica } from "../bionica";
import { partirRespuesta, type Parte } from "../markdown";
import { Encargo } from "./Encargo";
import { AccionesRespuesta } from "./AccionesRespuesta";
import { formatearReloj } from "../tiempo";
import { debeMostrarReloj } from "../bloqueAbierto";
import type { Sesion, Tarea } from "../contratos";
import "./Chat.css";

// Cada cuánto se refresca el reloj de una línea (3f · 4): minutos, no
// segundos — la ley 1 mide sola, no hace falta un segundero.
const MS_REFRESCO_RELOJ = 30000;

// 900 ms, el DS (movimiento) y el playground de la celebración: una sola vez,
// nunca se repite en el mismo mensaje.
const DURACION_CELEBRACION_MS = 900;

export interface Mensaje {
  id: string;
  rol: "juan" | "remi";
  texto: string;
  // Una pregunta de Remi con Sí/No (pegar una charla larga).
  pregunta?: { onSi: () => void; onNo: () => void };
  // Presentes solo cuando esta respuesta abrió un bloque (tipo "hoy"): con
  // eso el chat sabe que hay algo abierto y muestra «Hecha» debajo.
  tarea?: Tarea | null;
  sesion?: Sesion | null;
  // Retomar (3f · 7): los últimos 3 mensajes de la conversación vigente al
  // abrir, antes de que digas nada nuevo — se ven, pero en ink-muted.
  historial?: boolean;
}

interface Props {
  mensajes: Mensaje[];
  onEscuchar: (texto: string) => void;
  onCallar: () => void;
  onCopiar: (texto: string) => Promise<boolean>;
  onReintentar: () => void;
  onEnlace: (url: string) => void;
  // «Hecha»: cierra el bloque abierto. Devuelve los minutos reales, o null
  // si no se pudo cerrar — entonces no se celebra (ley 3: nada de fallar
  // en silencio con una fiesta que no pasó).
  onCerrarBloque: (tareaId: string) => Promise<number | null>;
  // Lectura biónica: la intensidad (0–1), o null si está apagada. Solo en lo
  // que escribe Remi; nunca en botones, campos ni en la tarjeta de código.
  bionica?: number | null;
  // Reloj de una línea (3f · 4), bajo el bloque abierto. null: sin dato
  // todavía (ley 1, nunca se inventa) — el reloj igual muestra lo que corre.
  ultimaVezMin?: number | null;
  // Piel dinero (3f · 3): esta sesión es de una entrega que paga.
  dinero?: boolean;
}

function RelojLinea({ inicio, ultimaVezMin, dinero }: { inicio: string; ultimaVezMin: number | null; dinero: boolean }) {
  const [ahoraMs, setAhoraMs] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setAhoraMs(Date.now()), MS_REFRESCO_RELOJ);
    return () => window.clearInterval(id);
  }, []);
  const transcurridos = Math.max(0, (ahoraMs - new Date(inicio).getTime()) / 60000);
  return (
    <p className={`num chat__reloj chat__reloj--${dinero ? "dinero" : "brasa"}`}>
      {formatearReloj(transcurridos)}
      {ultimaVezMin !== null && ultimaVezMin !== undefined && <> · la última vez {formatearReloj(ultimaVezMin)}</>}
    </p>
  );
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

// Ocho chispas de ámbar (dinero), como en el playground de la Biblia. Con
// prefers-reduced-motion la keyframe de subir no corre (Chat.css) y solo
// queda el cambio de color de la tarjeta.
const CHISPAS = [
  { dx: "-26px", dy: "-58px", retraso: "0s" },
  { dx: "-10px", dy: "-72px", retraso: ".06s" },
  { dx: "8px", dy: "-64px", retraso: ".12s" },
  { dx: "24px", dy: "-52px", retraso: ".05s" },
  { dx: "-38px", dy: "-40px", retraso: ".14s" },
  { dx: "38px", dy: "-42px", retraso: ".1s" },
  { dx: "-18px", dy: "-84px", retraso: ".18s" },
  { dx: "16px", dy: "-88px", retraso: ".2s" },
];

function formatearMinutos(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`;
}

function MensajeDeRemi({ mensaje, ultimo, ...acciones }: Omit<Props, "mensajes"> & { mensaje: Mensaje; ultimo: boolean }) {
  const [celebrando, setCelebrando] = useState(false);
  const [cerrado, setCerrado] = useState<string | null>(null);

  const hayBloqueAbierto = ultimo && mensaje.tarea != null && mensaje.tarea.estado === "hoy" && !cerrado;

  const cerrarAhora = () => {
    if (!mensaje.tarea || celebrando || cerrado) return;
    const tareaId = mensaje.tarea.id;
    void acciones.onCerrarBloque(tareaId).then((minutos) => {
      if (minutos == null) return; // no se pudo cerrar: no hay fiesta que no pasó (ley 3)
      setCelebrando(true);
      window.setTimeout(() => {
        setCelebrando(false);
        setCerrado(`Cerrado. ${formatearMinutos(minutos)}.`);
      }, DURACION_CELEBRACION_MS);
    });
  };

  const bloques = partirRespuesta(cerrado ?? mensaje.texto);

  return (
    <div
      className="chat__mensaje chat__mensaje--remi"
      data-ultimo={ultimo ? "si" : "no"}
      data-celebrando={celebrando ? "si" : "no"}
    >
      {celebrando &&
        CHISPAS.map((chispa, i) => (
          <i
            key={i}
            className="chat__chispa"
            style={{ "--dx": chispa.dx, "--dy": chispa.dy, animationDelay: chispa.retraso } as CSSProperties}
          />
        ))}
      {bloques.map((bloque, i) =>
        bloque.tipo === "encargo" ? (
          <Encargo key={i} texto={bloque.texto} />
        ) : (
          <p key={i} className={`display-it chat__remi${mensaje.historial ? " ink-muted" : ""}`}>
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
      ) : !cerrado ? (
        <AccionesRespuesta
          texto={mensaje.texto}
          onEscuchar={() => acciones.onEscuchar(mensaje.texto)}
          onCallar={acciones.onCallar}
          onCopiar={() => acciones.onCopiar(mensaje.texto)}
          onReintentar={ultimo ? acciones.onReintentar : undefined}
        />
      ) : null}
      {hayBloqueAbierto && debeMostrarReloj(mensaje.tarea, mensaje.sesion) && (
        <RelojLinea
          inicio={mensaje.sesion!.inicio}
          ultimaVezMin={acciones.ultimaVezMin ?? null}
          dinero={Boolean(acciones.dinero)}
        />
      )}
      {hayBloqueAbierto && (
        <button type="button" className="chat__hecha" onClick={cerrarAhora} disabled={celebrando}>
          Hecha
        </button>
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
            <p className={`body-sm chat__juan${mensaje.historial ? " ink-muted" : ""}`}>{mensaje.texto}</p>
          </div>
        ) : (
          <MensajeDeRemi key={mensaje.id} mensaje={mensaje} ultimo={i === mensajes.length - 1} {...acciones} />
        ),
      )}
      <div ref={fondo} />
    </div>
  );
}

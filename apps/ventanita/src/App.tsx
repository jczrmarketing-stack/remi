import { useCallback, useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Reloj } from "./componentes/Reloj";
import { PromptTerminal } from "./componentes/PromptTerminal";
import { enviarMensaje } from "./servidor";
import { animarTamano } from "./movimiento";
import { callarse, hablar } from "./voz";
import { alternarSilencio, estaSilenciado } from "./silencio";
import { detenerEscuchaYTranscribir, iniciarEscucha } from "./microfono";
import type { Estado, OrigenMensaje } from "./tipos";
import "./estilos.css";
import "./App.css";

const TAMANO_REPOSO = { width: 320, height: 180 };
const TAMANO_EXPANDIDO = { width: 420, height: 520 };
const DURACION_APARECER = 250;
// Tiempo propio de "hablando": no depende de cuánto tarde la locución
// (que puede no existir, si el mensaje fue escrito o está silenciado).
const DURACION_HABLANDO = 4000;
const MAX_PALABRAS_VOZ = 20;

function recortarPalabras(frase: string): string {
  const palabras = frase.trim().split(/\s+/);
  if (palabras.length <= MAX_PALABRAS_VOZ) return frase;
  return palabras.slice(0, MAX_PALABRAS_VOZ - 1).join(" ") + "…";
}

// Ley 3: sin cadena de culpa. Si el núcleo no responde, Remi lo dice
// con calma y vuelve a reposo — nunca regaña ni cuenta el fallo.
function fraseDeFallo(): string {
  return "No pude guardarlo. Lo intento más tarde.";
}

export default function App() {
  const [estado, setEstado] = useState<Estado>("reposo");
  const [texto, setTexto] = useState("");
  const [voz, setVoz] = useState("");
  const [origenMensaje, setOrigenMensaje] = useState<OrigenMensaje>("texto");
  const [grabando, setGrabando] = useState(false);
  const [silenciado, setSilenciado] = useState(() => estaSilenciado());

  const expandido = estado !== "reposo";
  const expandidoAnteriorRef = useRef(expandido);

  useEffect(() => {
    if (expandidoAnteriorRef.current === expandido) return;
    expandidoAnteriorRef.current = expandido;
    const ventana = getCurrentWindow();
    const desde = expandido ? TAMANO_REPOSO : TAMANO_EXPANDIDO;
    const hasta = expandido ? TAMANO_EXPANDIDO : TAMANO_REPOSO;
    void animarTamano(ventana, desde, hasta, DURACION_APARECER);
  }, [expandido]);

  // Mute local a la ventana (no global de sistema): Cmd+Shift+M funciona
  // aunque estés escribiendo, porque los navegadores/webviews no meten
  // combos con Cmd en el campo de texto.
  useEffect(() => {
    function alTeclado(evento: KeyboardEvent) {
      if (evento.key.toLowerCase() !== "m" || !evento.metaKey || !evento.shiftKey) return;
      evento.preventDefault();
      setSilenciado(alternarSilencio());
    }
    window.addEventListener("keydown", alTeclado);
    return () => window.removeEventListener("keydown", alTeclado);
  }, []);

  // Ley 3/4 aparte: Remi habla solo si ESTE mensaje llegó por voz (mic
  // activado y no silenciada). Si lo escribiste a mano, contesta en
  // silencio. "hablando" dura lo mismo la diga en voz alta o no.
  useEffect(() => {
    if (estado !== "hablando") return;

    if (origenMensaje === "voz" && !silenciado) {
      void hablar(voz);
    }

    const id = window.setTimeout(() => {
      setEstado("reposo");
      setTexto("");
      setVoz("");
    }, DURACION_HABLANDO);

    return () => {
      window.clearTimeout(id);
      callarse();
    };
  }, [estado, voz, origenMensaje, silenciado]);

  // Reemplaza a Handy: primer click prende el micrófono (reposo→escuchando),
  // segundo click lo apaga y transcribe. El texto queda editable en el
  // PromptTerminal antes de mandarlo — nunca se envía a ciegas.
  const alTocarVentanita = useCallback(async () => {
    if (estado === "reposo") {
      setOrigenMensaje("voz");
      setEstado("escuchando");
      setGrabando(true);
      try {
        await iniciarEscucha();
      } catch {
        // Sin micrófono disponible: cae a escritura manual, sin culpa (ley 3).
        setGrabando(false);
        setOrigenMensaje("texto");
      }
      return;
    }

    if (estado === "escuchando" && grabando) {
      setGrabando(false);
      setEstado("pensando");
      try {
        const transcripcion = await detenerEscuchaYTranscribir();
        setTexto(transcripcion);
      } catch {
        // No se pudo transcribir: el cuadro queda vacío, se escribe a mano.
      } finally {
        setEstado("escuchando");
      }
    }
  }, [estado, grabando]);

  // Se arrastra desde cualquier parte de la ventanita, en cualquier estado,
  // salvo dentro del PromptTerminal (ahí hay que poder hacer click y
  // seleccionar texto, no mover la ventana). Un click sin arrastre
  // igual dispara alTocarVentanita: startDragging no lo bloquea.
  const alPresionar = useCallback((evento: React.MouseEvent<HTMLDivElement>) => {
    if (evento.button !== 0) return;
    if ((evento.target as HTMLElement).closest(".prompt-terminal")) return;
    void getCurrentWindow().startDragging();
  }, []);

  const alEnviar = useCallback(async () => {
    const mensaje = texto.trim();
    if (!mensaje || estado !== "escuchando") return;
    // origenMensaje ya quedó decidido al activar (o no) el micrófono.
    setEstado("pensando");
    try {
      const respuesta = await enviarMensaje(mensaje);
      setVoz(respuesta.voz);
    } catch {
      setVoz(fraseDeFallo());
    } finally {
      setEstado("hablando");
    }
  }, [texto, estado]);

  return (
    <div
      className={`ventanita ventanita--${estado}`}
      onClick={alTocarVentanita}
      onMouseDown={alPresionar}
    >
      <StatusDot estado={estado} />

      {estado === "hablando" && <p className="display-it voz">{recortarPalabras(voz)}</p>}
      {estado === "hablando" && <Reloj />}

      {expandido && (
        <PromptTerminal
          valor={texto}
          deshabilitado={estado !== "escuchando"}
          enfocar={estado === "escuchando"}
          onCambio={setTexto}
          onEnviar={() => void alEnviar()}
        />
      )}
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Reloj } from "./componentes/Reloj";
import { PromptTerminal } from "./componentes/PromptTerminal";
import { enviarMensaje } from "./servidor";
import { animarTamano } from "./movimiento";
import { callarse, hablar, haySoporteDeVoz } from "./voz";
import type { Estado } from "./tipos";
import "./estilos.css";
import "./App.css";

const TAMANO_REPOSO = { width: 320, height: 180 };
const TAMANO_EXPANDIDO = { width: 420, height: 520 };
const DURACION_APARECER = 250;
// Piso mínimo para leer la frase cuando el webview no tiene voces instaladas.
const DURACION_VOZ_SIN_SONIDO = 4000;
const PAUSA_TRAS_HABLAR = 700;
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

  useEffect(() => {
    if (estado !== "hablando") return;

    let cancelado = false;
    const volverAReposo = () => {
      if (cancelado) return;
      setEstado("reposo");
      setTexto("");
      setVoz("");
    };

    if (haySoporteDeVoz()) {
      void hablar(voz).then(() => {
        if (cancelado) return;
        window.setTimeout(volverAReposo, PAUSA_TRAS_HABLAR);
      });
    } else {
      window.setTimeout(volverAReposo, DURACION_VOZ_SIN_SONIDO);
    }

    return () => {
      cancelado = true;
      callarse();
    };
  }, [estado, voz]);

  const alTocarVentanita = useCallback(() => {
    if (estado !== "reposo") return;
    setEstado("escuchando");
  }, [estado]);

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

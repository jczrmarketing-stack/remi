import { useCallback, useEffect, useRef, useState } from "react";
import { LogicalSize, getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Reloj } from "./componentes/Reloj";
import { PromptTerminal } from "./componentes/PromptTerminal";
import { enviarMensaje } from "./servidor";
import { animarTamano } from "./movimiento";
import { callarse, hablar } from "./voz";
import { alternarSilencio, estaSilenciado } from "./silencio";
import { alDetectarSilencio, detenerEscuchaYTranscribir, iniciarEscucha } from "./microfono";
import type { Estado, Modo, OrigenMensaje } from "./tipos";
import "./estilos.css";
import "./App.css";

const TAMANO_REPOSO = { width: 320, height: 180 };
const TAMANO_EXPANDIDO = { width: 420, height: 520 };
const DURACION_APARECER = 250;
// Tiempo propio de "hablando": no depende de si la locución existe o
// termina antes/después (puede estar silenciada) — pero si depende del
// largo del texto. Es un techo, no una espera obligada: un click la
// cierra antes en cualquier momento.
const MS_POR_PALABRA_HABLANDO = 260;
const DURACION_HABLANDO_MINIMA = 2500;
const DURACION_HABLANDO_MAXIMA = 7000;
const MAX_PALABRAS_VOZ = 20;

function duracionHablando(frase: string): number {
  const palabras = frase.trim() ? frase.trim().split(/\s+/).length : 0;
  const calculada = DURACION_HABLANDO_MINIMA + palabras * MS_POR_PALABRA_HABLANDO;
  return Math.min(DURACION_HABLANDO_MAXIMA, calculada);
}
// Ventana para contar 1, 2 o 3 clicks antes de decidir qué hacer.
const ESPERA_CLICS = 350;
// Por debajo de esto es un click; por encima, arrastrás la ventana.
const UMBRAL_ARRASTRE_PX = 4;

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
  const [modo, setModo] = useState<Modo>("texto");
  const [texto, setTexto] = useState("");
  const [voz, setVoz] = useState("");
  const [origenMensaje, setOrigenMensaje] = useState<OrigenMensaje>("texto");
  const [grabando, setGrabando] = useState(false);
  const [silenciado, setSilenciado] = useState(() => estaSilenciado());

  const esperaClicsRef = useRef<number | undefined>(undefined);
  const clicsRef = useRef(0);
  // Los handlers viven en efectos y listeners; el ref evita re-suscribir.
  const accionesRef = useRef({ grabando, modo, estado, silenciado });
  accionesRef.current = { grabando, modo, estado, silenciado };

  const expandido = estado !== "reposo";
  const expandidoAnteriorRef = useRef(expandido);

  // macOS restaura el tamaño de la última sesión (la app siempre arranca
  // en reposo, la ventana no debería): forzar el tamaño real al montar.
  useEffect(() => {
    const { width, height } = TAMANO_REPOSO;
    void getCurrentWindow().setSize(new LogicalSize(width, height));
  }, []);

  useEffect(() => {
    if (expandidoAnteriorRef.current === expandido) return;
    expandidoAnteriorRef.current = expandido;
    const ventana = getCurrentWindow();
    const desde = expandido ? TAMANO_REPOSO : TAMANO_EXPANDIDO;
    const hasta = expandido ? TAMANO_EXPANDIDO : TAMANO_REPOSO;
    void animarTamano(ventana, desde, hasta, DURACION_APARECER);
  }, [expandido]);

  useEffect(() => {
    return () => {
      if (esperaClicsRef.current !== undefined) {
        window.clearTimeout(esperaClicsRef.current);
      }
    };
  }, []);

  const volverAReposo = useCallback(() => {
    setEstado("reposo");
    setModo("texto");
    setGrabando(false);
    setTexto("");
    setVoz("");
    callarse();
  }, []);

  const enviar = useCallback(
    async (mensaje: string) => {
      const limpio = mensaje.trim();
      if (!limpio) return;
      // Un doble Cmd+Enter (u onEnviar disparado dos veces) no manda dos
      // tareas: si ya está pensando o hablando, este envío no cuenta.
      if (accionesRef.current.estado === "pensando" || accionesRef.current.estado === "hablando") {
        return;
      }
      setEstado("pensando");
      try {
        const respuesta = await enviarMensaje(limpio);
        setVoz(respuesta.voz);
      } catch (error) {
        console.error("no se pudo mandar el mensaje:", error);
        setVoz(fraseDeFallo());
      } finally {
        setEstado("hablando");
      }
    },
    [],
  );

  const empezarATipear = useCallback(() => {
    setModo("texto");
    setOrigenMensaje("texto");
    setEstado("escuchando");
  }, []);

  const empezarAEscuchar = useCallback(async (modoNuevo: Modo) => {
    setModo(modoNuevo);
    setOrigenMensaje("voz");
    setEstado("escuchando");
    setGrabando(true);
    try {
      // En diálogo corta sola cuando dejás de hablar; en modo voz,
      // como Handy: vos la cortás con otro click.
      await iniciarEscucha(modoNuevo === "dialogo");
    } catch (error) {
      // Sin micrófono disponible: cae a escritura manual, sin culpa (ley 3).
      console.error("no se pudo prender el micrófono:", error);
      setGrabando(false);
      setModo("texto");
      setOrigenMensaje("texto");
    }
  }, []);

  const detenerYTranscribir = useCallback(async () => {
    if (!accionesRef.current.grabando) return;
    const enDialogo = accionesRef.current.modo === "dialogo";
    setGrabando(false);
    setEstado("pensando");
    try {
      const transcripcion = await detenerEscuchaYTranscribir();
      setTexto(transcripcion);
      if (enDialogo) {
        // En diálogo no se edita: lo dicho se manda solo.
        await enviar(transcripcion);
        return;
      }
      setEstado("escuchando");
    } catch (error) {
      // No escuchó nada (o no se entendió): sin culpa (ley 3).
      console.error("no se pudo transcribir:", error);
      if (enDialogo) {
        // En diálogo no hay cuadro para escribir: si no la dejamos
        // escuchando de nuevo, queda muda y trabada.
        void empezarAEscuchar("dialogo");
      } else {
        setEstado("escuchando");
      }
    }
  }, [enviar, empezarAEscuchar]);

  // El núcleo avisa cuando dejaste de hablar (solo en modo diálogo).
  useEffect(() => {
    const suscripcion = alDetectarSilencio(() => {
      void detenerYTranscribir();
    });
    return () => {
      void suscripcion.then((desuscribir) => desuscribir());
    };
  }, [detenerYTranscribir]);

  // Mute local a la ventana (no global de sistema): Cmd+Shift+M funciona
  // aunque estés escribiendo, porque los navegadores/webviews no meten
  // combos con Cmd en el campo de texto. Escape cancela todo.
  useEffect(() => {
    function alTeclado(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        evento.preventDefault();
        if (accionesRef.current.grabando) {
          void detenerEscuchaYTranscribir().catch(() => undefined);
        }
        volverAReposo();
        return;
      }
      if (evento.key.toLowerCase() === "m" && evento.metaKey && evento.shiftKey) {
        evento.preventDefault();
        setSilenciado(alternarSilencio());
      }
    }
    window.addEventListener("keydown", alTeclado);
    return () => window.removeEventListener("keydown", alTeclado);
  }, [volverAReposo]);

  // Remi habla solo si ESTE mensaje llegó por voz y no está silenciada —
  // mirado una sola vez al entrar; si silenciás a mitad de la locución
  // no hay que reiniciar el temporizador de "hablando" por eso. Dura lo
  // mismo la diga en voz alta o no; en diálogo, al terminar vuelve a
  // escucharte sola. Un click la cierra antes (ver alClick).
  useEffect(() => {
    if (estado !== "hablando") return;

    if (origenMensaje === "voz" && !accionesRef.current.silenciado) {
      void hablar(voz);
    }

    const id = window.setTimeout(() => {
      if (accionesRef.current.modo === "dialogo") {
        setTexto("");
        setVoz("");
        void empezarAEscuchar("dialogo");
        return;
      }
      volverAReposo();
    }, duracionHablando(voz));

    return () => {
      window.clearTimeout(id);
      callarse();
    };
  }, [estado, voz, origenMensaje, empezarAEscuchar, volverAReposo]);

  // 1 click escribís (al toque, sin esperar) · 2 clicks te escucha (como
  // Handy) · 3 clicks dialogan. La acción más común (escribir) no paga la
  // espera de las menos comunes: el primer click ya abrió el cuadro: los
  // clicks de más, dentro de la ventana, solo suben de modo.
  const alClick = useCallback(
    (evento: React.MouseEvent<HTMLDivElement>) => {
      // Un click más mientras ya estamos en la ventana de espera: cuenta
      // para subir de modo, no abre nada de nuevo — SIEMPRE, así caiga
      // arriba del cuadro que el primer click recién abrió (el segundo
      // y tercer click de un multi-click suelen caer en el mismo lugar
      // que el primero). El filtro de .prompt-terminal es solo para
      // cuando ya no se está decidiendo el modo.
      if (esperaClicsRef.current !== undefined) {
        clicsRef.current += 1;
        return;
      }

      if ((evento.target as HTMLElement).closest(".prompt-terminal")) return;

      if (estado === "reposo") {
        empezarATipear();
        clicsRef.current = 1;
        esperaClicsRef.current = window.setTimeout(() => {
          const clics = clicsRef.current;
          clicsRef.current = 0;
          esperaClicsRef.current = undefined;
          if (clics === 2) {
            void empezarAEscuchar("voz");
          } else if (clics >= 3) {
            void empezarAEscuchar("dialogo");
          }
        }, ESPERA_CLICS);
        return;
      }

      if (estado === "escuchando" && grabando) {
        void detenerYTranscribir();
        return;
      }

      // Un click en "hablando" cierra ahí mismo: el techo de duracionHablando
      // es un máximo, no una espera obligada.
      if (estado === "hablando") {
        volverAReposo();
      }
    },
    [estado, grabando, empezarATipear, empezarAEscuchar, detenerYTranscribir, volverAReposo],
  );

  // Se arrastra desde cualquier parte de la ventanita, en cualquier estado,
  // salvo dentro del PromptTerminal (ahí hay que poder hacer click y
  // seleccionar texto, no mover la ventana). startDragging() llamado en
  // mousedown se come el evento click en macOS — por eso medimos el
  // movimiento nosotros y solo arrastramos pasado el umbral; por debajo,
  // es un click de verdad y llega a alClick.
  const alPresionar = useCallback((evento: React.MouseEvent<HTMLDivElement>) => {
    if (evento.button !== 0) return;
    if ((evento.target as HTMLElement).closest(".prompt-terminal")) return;

    const inicio = { x: evento.clientX, y: evento.clientY };

    function alMover(e: MouseEvent) {
      const dx = e.clientX - inicio.x;
      const dy = e.clientY - inicio.y;
      if (Math.hypot(dx, dy) < UMBRAL_ARRASTRE_PX) return;
      limpiar();
      void getCurrentWindow().startDragging();
    }

    function limpiar() {
      window.removeEventListener("mousemove", alMover);
      window.removeEventListener("mouseup", limpiar);
    }

    window.addEventListener("mousemove", alMover);
    window.addEventListener("mouseup", limpiar);
  }, []);

  return (
    <div
      className={`ventanita ventanita--${estado}`}
      onClick={alClick}
      onMouseDown={alPresionar}
    >
      <StatusDot estado={estado} escuchandoVoz={grabando} />

      {estado === "hablando" && <p className="display-it voz">{recortarPalabras(voz)}</p>}
      {estado === "hablando" && <Reloj />}

      {/* Mientras el micrófono está abierto, o mientras Remi habla, no hay
          cuadro — una sola locura por pantalla (ley 4): se ve que escucha o
          que contesta, no un textarea deshabilitado de fondo. */}
      {expandido && !grabando && estado !== "hablando" && modo !== "dialogo" && (
        <PromptTerminal
          valor={texto}
          deshabilitado={estado !== "escuchando"}
          enfocar={estado === "escuchando" && !grabando}
          onCambio={setTexto}
          onEnviar={() => void enviar(texto)}
        />
      )}
    </div>
  );
}

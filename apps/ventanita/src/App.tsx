import { useCallback, useEffect, useRef, useState } from "react";
import { LogicalSize, getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Reloj } from "./componentes/Reloj";
import { PromptTerminal } from "./componentes/PromptTerminal";
import { ControlesVoz } from "./componentes/ControlesVoz";
import { enviarMensaje, obtenerUltimaVezMin } from "./servidor";
import { animarTamano } from "./movimiento";
import { callarse, hablar } from "./voz";
import {
  alternarSilencio,
  estaSilenciado,
  fijarVelocidad,
  obtenerVelocidad,
  type Velocidad,
} from "./preferencias";
import { alDetectarSilencio, detenerEscuchaYTranscribir, iniciarEscucha } from "./microfono";
import type { Estado, Modo, OrigenMensaje } from "./tipos";
import "./estilos.css";
import "./App.css";

const TAMANO_REPOSO = { width: 120, height: 44 };
const TAMANO_EXPANDIDO = { width: 420, height: 520 };
const DURACION_APARECER = 250;
// Tiempo de "hablando" cuando Remi NO dice la frase en voz alta (mensaje
// escrito, o voz silenciada): depende del largo del texto, para leerla.
// Un click la cierra antes en cualquier momento. Cuando sí habla, dura lo
// que dure la locución real (a la velocidad elegida), con un techo por si
// el sintetizador nunca avisa que terminó.
const MS_POR_PALABRA_HABLANDO = 260;
const DURACION_HABLANDO_MINIMA = 2500;
const DURACION_HABLANDO_MAXIMA = 7000;
const TECHO_LOCUCION_MS = 15000;
const MAX_PALABRAS_VOZ = 20;

function duracionHablando(frase: string): number {
  const palabras = frase.trim() ? frase.trim().split(/\s+/).length : 0;
  const calculada = DURACION_HABLANDO_MINIMA + palabras * MS_POR_PALABRA_HABLANDO;
  return Math.min(DURACION_HABLANDO_MAXIMA, calculada);
}
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
  const [velocidad, setVelocidad] = useState<Velocidad>(() => obtenerVelocidad());
  // Ley 1 hecha visible en el Reloj: null hasta que sepamos si hay dato
  // real, y se queda null si no lo hay (nunca un número inventado).
  const [sesionInicio, setSesionInicio] = useState<string | null>(null);
  const [ultimaVezMin, setUltimaVezMin] = useState<number | null>(null);

  // Los handlers viven en efectos y listeners; el ref evita re-suscribir.
  const accionesRef = useRef({ grabando, modo, estado, silenciado });
  accionesRef.current = { grabando, modo, estado, silenciado };

  // Cada vez que se vuelve a reposo a mano (click o Escape), esto sube:
  // si un fetch/invoke que ya estaba en vuelo resuelve DESPUÉS, se nota
  // que quedó viejo y no pisa el estado — si no, una respuesta tardía
  // podía saltar a "hablando" de la nada después de haber cancelado.
  const generacionRef = useRef(0);

  const expandido = estado !== "reposo";
  const expandidoAnteriorRef = useRef(expandido);

  // macOS restaura el tamaño de la última sesión (la app siempre arranca
  // en reposo, la ventana no debería): forzar el tamaño real al montar.
  useEffect(() => {
    const ventana = getCurrentWindow();
    const { width, height } = TAMANO_REPOSO;
    // Los límites min/max vienen compilados desde tauri.conf.json, y un
    // binario que no se recompiló trae los viejos (320×180): macOS clampea
    // el setSize a ese mínimo y la ventana no encoge. Fijarlos en tiempo de
    // ejecución ANTES de pedir el tamaño hace que el reposo real entre por
    // hot reload sin depender de que Rust se vuelva a construir.
    void (async () => {
      await ventana.setMinSize(new LogicalSize(width, height));
      await ventana.setMaxSize(
        new LogicalSize(TAMANO_EXPANDIDO.width, TAMANO_EXPANDIDO.height),
      );
      await ventana.setSize(new LogicalSize(width, height));
    })();
  }, []);

  useEffect(() => {
    if (expandidoAnteriorRef.current === expandido) return;
    expandidoAnteriorRef.current = expandido;
    const ventana = getCurrentWindow();
    const desde = expandido ? TAMANO_REPOSO : TAMANO_EXPANDIDO;
    const hasta = expandido ? TAMANO_EXPANDIDO : TAMANO_REPOSO;
    void animarTamano(ventana, desde, hasta, DURACION_APARECER);
  }, [expandido]);

  const volverAReposo = useCallback(() => {
    generacionRef.current += 1;
    setEstado("reposo");
    setModo("texto");
    setGrabando(false);
    setTexto("");
    setVoz("");
    setSesionInicio(null);
    setUltimaVezMin(null);
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
      const miGeneracion = generacionRef.current;
      setEstado("pensando");
      try {
        const respuesta = await enviarMensaje(limpio);
        if (generacionRef.current !== miGeneracion) return; // cancelado mientras esperaba
        setVoz(respuesta.voz);
        setSesionInicio(respuesta.sesion.inicio);
        // Si esto falla, el Reloj simplemente no se renderiza — no es
        // motivo para no poder contestar (ley 3, sin culpa).
        obtenerUltimaVezMin(respuesta.tarea.id)
          .then((valor) => {
            if (generacionRef.current === miGeneracion) setUltimaVezMin(valor);
          })
          .catch(() => {
            if (generacionRef.current === miGeneracion) setUltimaVezMin(null);
          });
      } catch (error) {
        if (generacionRef.current !== miGeneracion) return;
        console.error("no se pudo mandar el mensaje:", error);
        setVoz(fraseDeFallo());
      } finally {
        if (generacionRef.current === miGeneracion) setEstado("hablando");
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
    const miGeneracion = generacionRef.current;
    setGrabando(false);
    setEstado("pensando");
    try {
      const transcripcion = await detenerEscuchaYTranscribir();
      if (generacionRef.current !== miGeneracion) return; // cancelado mientras transcribía
      setTexto(transcripcion);
      if (enDialogo) {
        // En diálogo no se edita: lo dicho se manda solo.
        await enviar(transcripcion);
        return;
      }
      setEstado("escuchando");
    } catch (error) {
      if (generacionRef.current !== miGeneracion) return;
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

  const cambiarVelocidad = useCallback((nueva: Velocidad) => {
    fijarVelocidad(nueva);
    setVelocidad(nueva);
  }, []);

  // Remi habla solo si ESTE mensaje llegó por voz y no está silenciada —
  // mirado una sola vez al entrar. Si habla, "hablando" dura hasta que la
  // locución termina de verdad (cambiar la velocidad la reinicia a la
  // nueva); si no, un tiempo proporcional al texto. Al terminar, en
  // diálogo vuelve a escucharte sola; si no, reposo. Un click la cierra
  // antes (ver alClick).
  useEffect(() => {
    if (estado !== "hablando") return;

    let vigente = true;
    const terminar = () => {
      if (!vigente) return;
      vigente = false;
      if (accionesRef.current.modo === "dialogo") {
        setTexto("");
        setVoz("");
        void empezarAEscuchar("dialogo");
        return;
      }
      volverAReposo();
    };

    const habla = origenMensaje === "voz" && !accionesRef.current.silenciado;
    let techo: number;
    if (habla) {
      void hablar(voz, velocidad).then(terminar);
      techo = window.setTimeout(terminar, TECHO_LOCUCION_MS);
    } else {
      techo = window.setTimeout(terminar, duracionHablando(voz));
    }

    return () => {
      vigente = false;
      window.clearTimeout(techo);
      callarse();
    };
  }, [estado, voz, origenMensaje, velocidad, empezarAEscuchar, volverAReposo]);

  // Click: escribís · Option+click: te escucha una vez (como Handy) ·
  // Option+Shift+click: dialogan. Nada de contar clicks rápidos — eso
  // dependía de una ventana de tiempo y de dónde caía cada click, y
  // encontramos dos bugs distintos ahí. Un modificador se lee en el
  // mismo evento, sin ambigüedad posible.
  // Click: escribís · doble click: te escucha (micrófono) · triple
  // click: dialogan (voz a voz). Contamos nosotros, por tiempo: el
  // evento.detail del navegador se reinicia si cambia lo que hay bajo el
  // cursor, y justo después del 1er click la ventana crece y aparece el
  // cuadro — por eso el doble era intermitente y el triple casi nunca.
  // El 1er click abre texto AL INSTANTE (la acción más común no espera);
  // el 2do arma un temporizador corto por si viene el 3ro, y recién ahí
  // arranca voz o diálogo. Leemos el estado por ref, no por closure.
  const rachaRef = useRef({ n: 0, t: 0, timer: 0 as number });

  const alClick = useCallback(
    (evento: React.MouseEvent<HTMLDivElement>) => {
      const ahora = performance.now();
      const racha = rachaRef.current;
      const { estado: estadoActual, grabando: grabandoActual } = accionesRef.current;

      // Racha de clicks: cuenta si vienen seguidos (< 400 ms) y la ventana
      // está en reposo o recién abierta en texto sin nada escrito.
      const encadenable =
        estadoActual === "reposo" ||
        (estadoActual === "escuchando" && !grabandoActual && texto === "");
      if (encadenable && ahora - racha.t < 550) {
        racha.n += 1;
      } else {
        racha.n = 1;
      }
      racha.t = ahora;

      if (racha.n >= 2 && encadenable) {
        // 2do o 3er click: decidir voz vs diálogo cuando pare la racha.
        window.clearTimeout(racha.timer);
        racha.timer = window.setTimeout(() => {
          const modoNuevo: Modo = rachaRef.current.n >= 3 ? "dialogo" : "voz";
          rachaRef.current.n = 0;
          void empezarAEscuchar(modoNuevo);
        }, 520);
        return;
      }

      if ((evento.target as HTMLElement).closest(".prompt-terminal, .controles-voz")) return;

      if (estadoActual === "reposo") {
        empezarATipear();
        return;
      }

      if (estadoActual === "escuchando" && grabandoActual) {
        void detenerYTranscribir();
        return;
      }

      // Con texto escrito o dictado, un click fuera del cuadro lo MANDA —
      // antes borraba todo y volvía a reposo, que perdía el dictado.
      if (estadoActual === "escuchando" && texto.trim() !== "") {
        void enviar(texto);
        return;
      }

      // Cualquier otro estado no-reposo: un click fuera del cuadro vuelve
      // a reposo. Ningún estado se queda sin salida.
      volverAReposo();
    },
    [texto, enviar, empezarATipear, empezarAEscuchar, detenerYTranscribir, volverAReposo],
  );

  // Se arrastra desde cualquier parte de la ventanita, en cualquier estado,
  // salvo dentro del PromptTerminal (ahí hay que poder hacer click y
  // seleccionar texto, no mover la ventana). startDragging() llamado en
  // mousedown se come el evento click en macOS — por eso medimos el
  // movimiento nosotros y solo arrastramos pasado el umbral; por debajo,
  // es un click de verdad y llega a alClick.
  const alPresionar = useCallback((evento: React.MouseEvent<HTMLDivElement>) => {
    if (evento.button !== 0) return;
    if ((evento.target as HTMLElement).closest(".prompt-terminal, .controles-voz")) return;

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
      {estado === "hablando" && (
        <ControlesVoz velocidad={velocidad} onVelocidad={cambiarVelocidad} />
      )}
      {estado === "hablando" && ultimaVezMin !== null && sesionInicio !== null && (
        <Reloj
          minutosTranscurridos={(Date.now() - new Date(sesionInicio).getTime()) / 60000}
          ultimaVezMin={ultimaVezMin}
        />
      )}

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

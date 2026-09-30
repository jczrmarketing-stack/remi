import { useCallback, useEffect, useRef, useState } from "react";
import { LogicalPosition, LogicalSize, currentMonitor, getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Semaforo } from "./componentes/Semaforo";
import { BotonCancelar } from "./componentes/BotonCancelar";
import { Chat, type Mensaje } from "./componentes/Chat";
import { Campo, type CampoRef } from "./componentes/Campo";
import { ChipCerebro } from "./componentes/ChipCerebro";
import { ChipVoz } from "./componentes/ChipVoz";
import {
  enviarMensaje,
  guardarEpisodio,
  obtenerConversacion,
  obtenerModelosOllama,
  obtenerMotores,
  obtenerUltimaVezDeHoy,
  type MotorDePensar,
} from "./servidor";
import { MS_RECORDATORIO_VISIBLE, tocaRecordar } from "./recordatorio";
import { animarTamano } from "./movimiento";
import {
  callarse,
  despertarAudio,
  estadoDeVoz,
  hablar,
  obtenerVoces,
  type VozDisponible,
} from "./voz";
import { copiarAlPortapapeles } from "./portapapeles";
import { formatearDuracion, formatearHace, registrarInteraccion, ultimaInteraccion } from "./tiempo";
import {
  alternarSilencio,
  CEREBRO_POR_DEFECTO,
  type EleccionCerebro,
  estaSilenciado,
  estaSinPensar,
  etiquetaDe,
  fijarCerebro,
  fijarSinPensar,
  fijarVelocidad,
  fijarVoz,
  obtenerCerebro,
  obtenerVelocidad,
  obtenerVoz,
  paraEnviar,
  type PreferenciaVoz,
  type Velocidad,
} from "./preferencias";
import {
  activarCortePorSilencio,
  alDetectarSilencio,
  alPalanca,
  cancelarEscucha,
  detenerEscuchaYTranscribir,
  iniciarEscucha,
  transcribirParcial,
  type OrigenParada,
} from "./microfono";
import {
  cortePorSilencioAplica,
  decidir,
  decidirBolita,
  decidirPalanca,
  decidirTrasVacia,
  RACHA_VACIA,
  rachaSigueViva,
  type Accion,
  type Racha,
} from "./gestos";
import { enchufarConsola, registrar } from "./registro";
import {
  fijarPosicion,
  fijarTamanoChat,
  limitarTamano,
  obtenerPosicion,
  obtenerTamanoChat,
  posicionQueEntra,
  TAMANO_MINIMO,
  tamanoMaximo,
  type Pantalla,
  type Tamano,
} from "./ventana";
import type { Estado, Modo, OrigenMensaje } from "./tipos";
import "./estilos.css";
import "./App.css";

// — Tamaños —
// Reposo es una píldora. Sin historia, 120×44: solo el punto. Con «hace 6
// min» debajo, 120×64; con el dato medido de la ley 1, más ancha.
const TAMANO_REPOSO_MINIMO = { width: 120, height: 44 };
const TAMANO_REPOSO_CON_HACE = { width: 120, height: 64 };
const TAMANO_REPOSO_ULTIMA_VEZ = { width: 210, height: 64 };
// Abierta es el chat (3c): una sola pantalla, del tamaño que la dejaste
// (ventana.ts). Guardar tamaño y lugar espera a que dejes de mover.
const MS_GUARDAR_VENTANA = 400;
const REFRESCO_HACE_MS = 30000;
const DURACION_APARECER = 250;
// Techo de una locución, por si el sintetizador nunca avisa que terminó.
const TECHO_LOCUCION_MS = 60000;
// Mientras dictás, cada cuánto se pide lo que vas diciendo.
const MS_PARCIAL = 1500;
// Por debajo de esto es un click; por encima, arrastrás la ventana.
const UMBRAL_ARRASTRE_PX = 4;

// La pantalla donde está la ventana, en puntos (el área sin menú ni Dock).
async function pantallaActual(): Promise<Pantalla | null> {
  try {
    const monitor = await currentMonitor();
    if (!monitor) return null;
    const f = monitor.scaleFactor;
    const { position, size } = monitor.workArea;
    return { x: position.x / f, y: position.y / f, width: size.width / f, height: size.height / f };
  } catch {
    return null;
  }
}

async function tamanoActual(): Promise<Tamano> {
  const ventana = getCurrentWindow();
  const [fisico, f] = await Promise.all([ventana.innerSize(), ventana.scaleFactor()]);
  return { width: fisico.width / f, height: fisico.height / f };
}

function tamanoReposo(hayHace: boolean, hayUltimaVez: boolean) {
  if (hayUltimaVez) return TAMANO_REPOSO_ULTIMA_VEZ;
  return hayHace ? TAMANO_REPOSO_CON_HACE : TAMANO_REPOSO_MINIMO;
}

// Qué es un control (nunca un gesto de la píldora) y qué es el campo.
const SELECTOR_CONTROLES = ".chat, .pie, .semaforo, .boton-cancelar, .bolita, .asa, button, select, a";
const SELECTOR_CUADRO = ".campo";
// Desde dónde NO se arrastra la ventana: donde hay texto o controles.
const SELECTOR_SIN_ARRASTRE = ".chat__mensaje, .campo, .pie, .semaforo, .boton-cancelar, .bolita, .asa";

function clasificarObjetivo(objetivo: EventTarget | null) {
  const elemento = objetivo instanceof HTMLElement ? objetivo : null;
  const dentroDeControl = Boolean(elemento?.closest(SELECTOR_CONTROLES));
  const dentroDelCuadro = !dentroDeControl && Boolean(elemento?.closest(SELECTOR_CUADRO));
  const enBolita = Boolean(elemento?.closest(".bolita"));
  return { dentroDeControl, dentroDelCuadro, enBolita };
}

// Ley 3: sin cadena de culpa. Si el núcleo no responde, Remi lo dice con calma.
const FRASE_DE_FALLO = "No pude contestarte ahora. Probá de nuevo en un rato.";

let contadorMensajes = 0;
function nuevoId(): string {
  contadorMensajes += 1;
  return `m${Date.now()}-${contadorMensajes}`;
}

enchufarConsola();

export default function App() {
  const [estado, setEstado] = useState<Estado>("reposo");
  const [modo, setModo] = useState<Modo>("texto");
  // Lo que está en el campo de abajo.
  const [texto, setTexto] = useState("");
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [grabando, setGrabando] = useState(false);
  const [transcribiendo, setTranscribiendo] = useState(false);
  const [silenciado, setSilenciado] = useState(() => estaSilenciado());
  const [velocidad, setVelocidad] = useState<Velocidad>(() => obtenerVelocidad());
  const [vozElegida, setVozElegida] = useState<PreferenciaVoz>(() => obtenerVoz());
  const [vocesDisponibles, setVocesDisponibles] = useState<VozDisponible[]>([]);
  // Con qué piensa: el chip de cerebro (motor, modelo y nivel). «sin
  // pensar» ya no se elige: si quedó puesto de antes, se apaga.
  const [cerebro, setCerebro] = useState<EleccionCerebro>(() => {
    if (estaSinPensar()) fijarSinPensar(false);
    return obtenerCerebro();
  });
  const [motores, setMotores] = useState<MotorDePensar[]>([]);
  const [modelosOllama, setModelosOllama] = useState<string[]>([]);
  const [recordatorio, setRecordatorio] = useState<string | null>(null);
  const ultimoRecordatorioRef = useRef(Date.now());
  const [ultimaInteraccionMs, setUltimaInteraccionMs] = useState<number | null>(() => ultimaInteraccion());
  const [ahoraMs, setAhoraMs] = useState(() => Date.now());
  const [ultimaVezDeHoy, setUltimaVezDeHoy] = useState<number | null>(null);

  const campoRef = useRef<CampoRef>(null);
  // Lo que había en el campo antes de dictar: lo dictado se suma detrás.
  const baseDictadoRef = useRef("");
  // El último mensaje que mandaste, para «otra respuesta».
  const ultimoEnviadoRef = useRef<{ texto: string; origen: OrigenMensaje } | null>(null);

  const accionesRef = useRef({ grabando, modo, estado, silenciado, texto, cerebro, velocidad, vozElegida });
  accionesRef.current = { grabando, modo, estado, silenciado, texto, cerebro, velocidad, vozElegida };

  // Cada vuelta a reposo (o cancelación) sube esto: lo que estaba en vuelo
  // y vuelve después queda viejo y no pisa nada.
  const generacionRef = useRef(0);
  const enviandoRef = useRef(false);
  const cambioDeTamanoRef = useRef<number | null>(null);
  const grabacionDesdeRef = useRef<number | null>(null);
  const vaciasSeguidasRef = useRef(0);
  const rearmeRef = useRef(0);
  const locucionRef = useRef(0);
  const toqueBolitaRef = useRef<number | null>(null);
  const rachaRef = useRef<Racha>(RACHA_VACIA);

  useEffect(() => {
    registrar("estado", { a: estado });
  }, [estado]);

  // — Tamaño de la ventana —

  const expandido = estado !== "reposo";
  const expandidoAnteriorRef = useRef(expandido);
  const hayHace = ultimaInteraccionMs !== null || recordatorio !== null;
  const hayUltimaVez = ultimaVezDeHoy !== null;
  const reposoRef = useRef({ hayHace, hayUltimaVez });
  reposoRef.current = { hayHace, hayUltimaVez };

  // Mientras la animamos nosotros, los cambios de tamaño no son tuyos: no
  // se guardan.
  const animandoRef = useRef(false);

  // Al arrancar: la píldora del tamaño justo y en el lugar donde la dejaste.
  useEffect(() => {
    const ventana = getCurrentWindow();
    const reposo = tamanoReposo(reposoRef.current.hayHace, reposoRef.current.hayUltimaVez);
    registrar("tamaño", { motivo: "montar", w: reposo.width, h: reposo.height });
    cambioDeTamanoRef.current = performance.now();
    void (async () => {
      await ventana.setResizable(false);
      await ventana.setMinSize(new LogicalSize(TAMANO_REPOSO_MINIMO.width, TAMANO_REPOSO_MINIMO.height));
      await ventana.setMaxSize(null);
      await ventana.setSize(new LogicalSize(reposo.width, reposo.height));
      const guardada = obtenerPosicion();
      if (guardada) {
        const lugar = posicionQueEntra(guardada, reposo, await pantallaActual());
        registrar("posición", { motivo: "montar", x: lugar.x, y: lugar.y });
        await ventana.setPosition(new LogicalPosition(lugar.x, lugar.y));
      }
    })();
  }, []);

  // Abrir: del tamaño que la dejaste (entre 360×240 y el 90 % de la
  // pantalla), corrida si hace falta para que entre entera. Cerrar: vuelve
  // a la píldora desde el tamaño que tenga.
  useEffect(() => {
    if (expandidoAnteriorRef.current === expandido) return;
    expandidoAnteriorRef.current = expandido;
    const ventana = getCurrentWindow();
    const reposo = tamanoReposo(reposoRef.current.hayHace, reposoRef.current.hayUltimaVez);
    void (async () => {
      animandoRef.current = true;
      cambioDeTamanoRef.current = performance.now();
      if (expandido) {
        const pantalla = await pantallaActual();
        const hasta = limitarTamano(obtenerTamanoChat(), pantalla);
        if (pantalla) {
          const maximo = tamanoMaximo(pantalla);
          await ventana.setMaxSize(new LogicalSize(maximo.width, maximo.height));
          const [fisica, f] = await Promise.all([ventana.outerPosition(), ventana.scaleFactor()]);
          const ahora = { x: fisica.x / f, y: fisica.y / f };
          const lugar = posicionQueEntra(ahora, hasta, pantalla);
          if (lugar.x !== Math.round(ahora.x) || lugar.y !== Math.round(ahora.y)) {
            await ventana.setPosition(new LogicalPosition(lugar.x, lugar.y));
          }
        }
        registrar("tamaño", { motivo: "expandir", w: hasta.width, h: hasta.height });
        await animarTamano(ventana, reposo, hasta, DURACION_APARECER);
        await ventana.setMinSize(new LogicalSize(TAMANO_MINIMO.width, TAMANO_MINIMO.height));
        await ventana.setResizable(true);
      } else {
        await ventana.setResizable(false);
        await ventana.setMinSize(new LogicalSize(TAMANO_REPOSO_MINIMO.width, TAMANO_REPOSO_MINIMO.height));
        const desde = await tamanoActual();
        registrar("tamaño", { motivo: "encoger", w: reposo.width, h: reposo.height });
        await animarTamano(ventana, desde, reposo, DURACION_APARECER);
      }
      cambioDeTamanoRef.current = performance.now();
      animandoRef.current = false;
    })();
  }, [expandido]);

  // Lo que muevas o agrandes a mano se guarda, cuando dejás de moverlo.
  useEffect(() => {
    const ventana = getCurrentWindow();
    let reloj = 0;
    const tamano = ventana.onResized(() => {
      if (animandoRef.current || accionesRef.current.estado === "reposo") return;
      window.clearTimeout(reloj);
      reloj = window.setTimeout(() => {
        void tamanoActual().then((t) => {
          if (animandoRef.current || accionesRef.current.estado === "reposo") return;
          fijarTamanoChat(t);
          registrar("tamaño", { motivo: "a mano", w: Math.round(t.width), h: Math.round(t.height) });
        });
      }, MS_GUARDAR_VENTANA);
    });
    let relojLugar = 0;
    const lugar = ventana.onMoved(({ payload }) => {
      window.clearTimeout(relojLugar);
      relojLugar = window.setTimeout(() => {
        void ventana.scaleFactor().then((f) => fijarPosicion({ x: payload.x / f, y: payload.y / f }));
      }, MS_GUARDAR_VENTANA);
    });
    return () => {
      window.clearTimeout(reloj);
      window.clearTimeout(relojLugar);
      void tamano.then((dejar) => dejar());
      void lugar.then((dejar) => dejar());
    };
  }, []);

  useEffect(() => {
    // Durante la animación de cerrar, el tamaño lo pone ella.
    if (expandido || animandoRef.current) return;
    const { width, height } = tamanoReposo(hayHace, hayUltimaVez);
    cambioDeTamanoRef.current = performance.now();
    void getCurrentWindow().setSize(new LogicalSize(width, height));
  }, [expandido, hayHace, hayUltimaVez]);

  useEffect(() => {
    if (expandido || !hayHace) return;
    setAhoraMs(Date.now());
    const id = window.setInterval(() => setAhoraMs(Date.now()), REFRESCO_HACE_MS);
    return () => window.clearInterval(id);
  }, [expandido, hayHace]);

  useEffect(() => {
    if (expandido) return;
    obtenerUltimaVezDeHoy()
      .then(setUltimaVezDeHoy)
      .catch(() => setUltimaVezDeHoy(null));
  }, [expandido, ultimaInteraccionMs]);

  // Al abrir: el chat de la conversación vigente (la de la última hora).
  useEffect(() => {
    if (!expandido) return;
    const miGeneracion = generacionRef.current;
    obtenerConversacion()
      .then((turnos) => {
        if (generacionRef.current !== miGeneracion) return;
        setMensajes((actuales) =>
          // Si ya hay mensajes de esta apertura (llegaron antes que la
          // historia), la historia va antes y no se duplica nada.
          actuales.length > 0 ? actuales : turnos.map((t) => ({ id: nuevoId(), rol: t.rol, texto: t.texto })),
        );
      })
      .catch(() => undefined);
  }, [expandido]);

  // — La voz de Remi —

  // Dice un texto. Mientras suena, el estado es «hablando» (la bolita late
  // con el volumen). Al terminar: en conversación de voz vuelve a
  // escucharte; si no, queda el chat abierto esperando.
  const decir = useCallback(async (frase: string, alTerminar?: () => void) => {
    const mia = ++locucionRef.current;
    setEstado("hablando");
    const { velocidad: vel, vozElegida: v } = accionesRef.current;
    await Promise.race([hablar(frase, vel, v), new Promise((r) => window.setTimeout(r, TECHO_LOCUCION_MS))]);
    if (locucionRef.current !== mia || accionesRef.current.estado !== "hablando") return;
    if (alTerminar) {
      alTerminar();
      return;
    }
    setEstado("escuchando");
  }, []);

  const callar = useCallback(() => {
    locucionRef.current += 1;
    callarse();
    if (accionesRef.current.estado === "hablando") setEstado("escuchando");
  }, []);

  const volverAReposo = useCallback(() => {
    generacionRef.current += 1;
    locucionRef.current += 1;
    setEstado("reposo");
    setModo("texto");
    setGrabando(false);
    setTranscribiendo(false);
    window.clearTimeout(rearmeRef.current);
    vaciasSeguidasRef.current = 0;
    grabacionDesdeRef.current = null;
    // El chat se vuelve a pedir al abrir: la historia vive en el núcleo.
    setMensajes([]);
    callarse();
  }, []);

  // — Mandar —

  const agregar = useCallback((mensaje: Omit<Mensaje, "id">) => {
    setMensajes((actuales) => [...actuales, { ...mensaje, id: nuevoId() }]);
  }, []);

  const empezarAEscucharRef = useRef<(modo: Modo) => Promise<void>>(async () => undefined);

  const enviar = useCallback(
    async (mensaje: string, origen: OrigenMensaje, reintento = false) => {
      const limpio = mensaje.trim();
      if (!limpio) return;
      if (enviandoRef.current) {
        registrar("enviar:ignorado", { motivo: "ya hay un envío en curso" });
        return;
      }
      enviandoRef.current = true;
      const miGeneracion = generacionRef.current;
      callarse();
      locucionRef.current += 1;
      if (!reintento) {
        agregar({ rol: "juan", texto: limpio });
        setTexto("");
      }
      ultimoEnviadoRef.current = { texto: limpio, origen };
      setEstado("pensando");
      const elegido = paraEnviar(accionesRef.current.cerebro);
      const arranque = performance.now();
      registrar("enviar", {
        palabras: limpio.split(/\s+/).length,
        origen,
        cerebro: etiquetaDe(accionesRef.current.cerebro),
        reintento,
      });
      let respuesta: Awaited<ReturnType<typeof enviarMensaje>> | null = null;
      try {
        respuesta = await enviarMensaje(limpio, { think: true, ...elegido, origen });
      } catch (error) {
        console.error("no se pudo mandar el mensaje:", error);
      } finally {
        enviandoRef.current = false;
      }
      if (generacionRef.current !== miGeneracion) return;
      registrar(respuesta ? "respuesta" : "enviar:falló", {
        tipo: respuesta?.tipo ?? "-",
        ms: Math.round(performance.now() - arranque),
      });
      const ahora = Date.now();
      registrarInteraccion(ahora);
      setUltimaInteraccionMs(ahora);
      if (respuesta?.tokens) {
        const { modelo, entrada, salida } = respuesta.tokens;
        console.info(`[claude] ${modelo} · tokens entrada=${entrada} salida=${salida}`);
      }
      const visible = respuesta ? respuesta.texto || respuesta.voz : FRASE_DE_FALLO;
      const dicho = respuesta ? respuesta.voz : FRASE_DE_FALLO;
      agregar({ rol: "remi", texto: visible });
      // Habla si le hablaste (y la voz no está silenciada). Escrito, calla:
      // para oírla está el ícono de escuchar.
      const enDialogo = accionesRef.current.modo === "dialogo";
      if (origen === "voz" && !accionesRef.current.silenciado) {
        void decir(dicho, enDialogo ? () => void empezarAEscucharRef.current("dialogo") : undefined);
        return;
      }
      if (enDialogo) {
        void empezarAEscucharRef.current("dialogo");
        return;
      }
      setEstado("escuchando");
      campoRef.current?.enfocar();
    },
    [agregar, decir],
  );

  // — Escuchar —

  const abrirChat = useCallback(() => {
    setModo("texto");
    setEstado("escuchando");
    window.setTimeout(() => campoRef.current?.enfocar(), DURACION_APARECER);
  }, []);

  const empezarAEscuchar = useCallback(async (modoNuevo: Modo) => {
    setModo(modoNuevo);
    setEstado("escuchando");
    setGrabando(true);
    baseDictadoRef.current = accionesRef.current.texto;
    const cortarSolo = modoNuevo === "dialogo";
    grabacionDesdeRef.current = performance.now();
    registrar("iniciarEscucha", { modo: modoNuevo, cortarSolo });
    try {
      await iniciarEscucha(cortarSolo);
    } catch (error) {
      console.error("no se pudo prender el micrófono:", error);
      registrar("iniciarEscucha:falló", { modo: modoNuevo });
      grabacionDesdeRef.current = null;
      setGrabando(false);
      setModo("texto");
    }
  }, []);
  empezarAEscucharRef.current = empezarAEscuchar;

  const pasarADialogo = useCallback((ahora: number) => {
    setModo("dialogo");
    grabacionDesdeRef.current = ahora;
    registrar("pasarADialogo");
    void activarCortePorSilencio().catch((error) => {
      console.error("no pude activar el corte por silencio:", error);
    });
  }, []);

  const detenerYTranscribir = useCallback(
    async (origen: OrigenParada) => {
      if (!accionesRef.current.grabando) {
        registrar("parada:ignorada", { origen, motivo: "no estaba grabando" });
        return;
      }
      const enDialogo = accionesRef.current.modo === "dialogo";
      const miGeneracion = generacionRef.current;
      registrar("parada", { origen, modo: accionesRef.current.modo });
      grabacionDesdeRef.current = null;
      setGrabando(false);
      setTranscribiendo(true);
      setEstado("pensando");
      try {
        const transcripcion = await detenerEscuchaYTranscribir(origen);
        if (generacionRef.current !== miGeneracion) return;
        setTranscribiendo(false);
        registrar("transcrito", { origen, caracteres: transcripcion.length });
        vaciasSeguidasRef.current = 0;
        if (enDialogo) {
          setTexto(baseDictadoRef.current);
          await enviar(transcripcion, "voz");
          return;
        }
        // Dictado: el texto queda en el campo, para leerlo o corregirlo.
        const base = baseDictadoRef.current.trim();
        setTexto(base ? `${base} ${transcripcion}` : transcripcion);
        setModo("texto");
        setEstado("escuchando");
        campoRef.current?.enfocar();
      } catch (error) {
        if (generacionRef.current !== miGeneracion) return;
        setTranscribiendo(false);
        setTexto(baseDictadoRef.current);
        registrar("sinTranscripcion", { origen, enDialogo });
        console.error("no se pudo transcribir:", error);
        if (!enDialogo) {
          setModo("texto");
          setEstado("escuchando");
          return;
        }
        // En conversación, dos vacías seguidas: no era el momento. Queda el
        // chat abierto, sin escuchar.
        vaciasSeguidasRef.current += 1;
        const tras = decidirTrasVacia(vaciasSeguidasRef.current);
        if (tras.tipo === "reposo") {
          registrar("dialogo:meVoy", { vacias: vaciasSeguidasRef.current });
          vaciasSeguidasRef.current = 0;
          setModo("texto");
          setEstado("escuchando");
          return;
        }
        window.clearTimeout(rearmeRef.current);
        rearmeRef.current = window.setTimeout(() => {
          if (generacionRef.current !== miGeneracion) return;
          void empezarAEscuchar("dialogo");
        }, tras.enMs);
      }
    },
    [enviar, empezarAEscuchar],
  );

  // Mientras dictás, lo que vas diciendo aparece en el campo (Whisper
  // residente, cada 1,5 s). Si no hay servidor, no pasa nada: el texto
  // llega entero al parar.
  useEffect(() => {
    if (!grabando) return;
    let vivo = true;
    let enVuelo = false;
    const id = window.setInterval(() => {
      if (enVuelo) return;
      enVuelo = true;
      transcribirParcial()
        .then((parcial) => {
          if (!vivo || !parcial || !accionesRef.current.grabando) return;
          const base = baseDictadoRef.current.trim();
          setTexto(base ? `${base} ${parcial}` : parcial);
        })
        .catch(() => undefined)
        .finally(() => {
          enVuelo = false;
        });
    }, MS_PARCIAL);
    return () => {
      vivo = false;
      window.clearInterval(id);
    };
  }, [grabando]);

  const cancelar = useCallback(
    (origen: "escape" | "x") => {
      const { grabando: grabandoActual, estado: estadoActual } = accionesRef.current;
      registrar("cancelar", { origen, estado: estadoActual, grabando: grabandoActual });
      if (grabandoActual) {
        void cancelarEscucha(origen).catch(() => undefined);
      }
      // Escape con algo en curso corta eso y deja el chat abierto; sin nada
      // en curso (o con la X), vuelve a la píldora.
      const enCurso = grabandoActual || estadoActual === "pensando" || estadoActual === "hablando";
      if (origen === "escape" && enCurso) {
        generacionRef.current += 1;
        enviandoRef.current = false;
        locucionRef.current += 1;
        callarse();
        grabacionDesdeRef.current = null;
        window.clearTimeout(rearmeRef.current);
        setGrabando(false);
        setTranscribiendo(false);
        setTexto(baseDictadoRef.current);
        setModo("texto");
        setEstado("escuchando");
        return;
      }
      volverAReposo();
    },
    [volverAReposo],
  );

  useEffect(() => {
    const suscripcion = alDetectarSilencio((motivo) => {
      const { grabando: grabandoActual, modo: modoActual } = accionesRef.current;
      registrar("silencio", { motivo, grabando: grabandoActual, modo: modoActual });
      if (!grabandoActual) return;
      if (!cortePorSilencioAplica(modoActual)) {
        registrar("silencio:ignorado", { motivo: "el dictado no corta por silencio" });
        return;
      }
      if (motivo === "sin_voz") {
        void cancelarEscucha("silencio:sin_voz").catch(() => undefined);
        grabacionDesdeRef.current = null;
        setGrabando(false);
        setTexto(baseDictadoRef.current);
        setModo("texto");
        setEstado("escuchando");
        return;
      }
      void detenerYTranscribir("silencio:fin");
    });
    return () => {
      void suscripcion.then((desuscribir) => desuscribir());
    };
  }, [detenerYTranscribir]);

  useEffect(() => {
    function alTeclado(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        evento.preventDefault();
        cancelar("escape");
        return;
      }
      if (evento.key.toLowerCase() === "m" && evento.metaKey && evento.shiftKey) {
        evento.preventDefault();
        setSilenciado(alternarSilencio());
      }
    }
    window.addEventListener("keydown", alTeclado);
    return () => window.removeEventListener("keydown", alTeclado);
  }, [cancelar]);

  // — Preferencias —

  const cambiarVelocidad = useCallback((nueva: Velocidad) => {
    fijarVelocidad(nueva);
    setVelocidad(nueva);
  }, []);

  const cambiarVoz = useCallback((nueva: PreferenciaVoz) => {
    fijarVoz(nueva);
    setVozElegida(nueva);
  }, []);

  const elegirCerebro = useCallback((nueva: EleccionCerebro) => {
    fijarCerebro(nueva);
    setCerebro(nueva);
  }, []);

  // Qué motores hay y qué modelos tiene Ollama: se pide al abrir. Si el
  // elegido hoy no está (Ollama apagado, Venice sin clave), no se manda a
  // ciegas para fallar: vuelve a Claude, y queda dicho.
  useEffect(() => {
    if (!expandido) return;
    obtenerMotores()
      .then((lista) => {
        setMotores(lista);
        const actual = lista.find((m) => m.id === accionesRef.current.cerebro.motor);
        if (actual && !actual.disponible) {
          registrar("motor:noDisponible", { motor: actual.id, detalle: actual.detalle });
          setCerebro(CEREBRO_POR_DEFECTO);
        }
      })
      .catch(() => setMotores([]));
    obtenerModelosOllama()
      .then(setModelosOllama)
      .catch(() => setModelosOllama([]));
  }, [expandido]);

  useEffect(() => {
    if (vocesDisponibles.length > 0) return;
    obtenerVoces()
      .then(setVocesDisponibles)
      .catch(() => setVocesDisponibles([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandido]);

  // Cada media hora, en reposo: «pensás con X», y se va a los 4 s.
  useEffect(() => {
    const id = window.setInterval(() => {
      const ahora = Date.now();
      if (!tocaRecordar(ultimoRecordatorioRef.current, ahora, accionesRef.current.estado === "reposo")) return;
      ultimoRecordatorioRef.current = ahora;
      const etiqueta = etiquetaDe(accionesRef.current.cerebro);
      registrar("recordatorio:motor", { cerebro: etiqueta });
      setRecordatorio(`pensás con ${etiqueta}`);
      window.setTimeout(() => setRecordatorio(null), MS_RECORDATORIO_VISIBLE);
    }, 60 * 1000);
    return () => window.clearInterval(id);
  }, []);

  // — Gestos —

  const ejecutar = useCallback(
    (accion: Accion, origen: OrigenParada, ahora: number) => {
      switch (accion.tipo) {
        case "nada":
          return;
        case "abrirTexto":
          abrirChat();
          return;
        case "grabarVoz":
          if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
          void empezarAEscuchar("voz");
          return;
        case "pasarADialogo":
          pasarADialogo(ahora);
          return;
        case "pararGrabacion":
          void detenerYTranscribir(origen);
          return;
        case "mandarTexto":
          void enviar(accionesRef.current.texto, "texto");
          return;
        case "volverAReposo":
          volverAReposo();
          return;
      }
    },
    [abrirChat, empezarAEscuchar, pasarADialogo, detenerYTranscribir, enviar, volverAReposo],
  );

  // La bolita, con el chat abierto: un toque dicta, dos conversan.
  const tocarBolita = useCallback(
    (ahora: number) => {
      const { estado: estadoActual, modo: modoActual, grabando: grabandoActual } = accionesRef.current;
      const accion = decidirBolita({
        estado: estadoActual,
        modo: modoActual,
        grabando: grabandoActual,
        ahora,
        toqueAnterior: toqueBolitaRef.current,
        grabacionDesde: grabacionDesdeRef.current,
      });
      toqueBolitaRef.current = ahora;
      registrar("bolita", { estado: estadoActual, modo: modoActual, grabando: grabandoActual, accion: accion.tipo });
      switch (accion.tipo) {
        case "dictar":
          void empezarAEscuchar("voz");
          return;
        case "pasarADialogo":
          pasarADialogo(ahora);
          return;
        case "pararDictado":
          void detenerYTranscribir("click");
          return;
        case "terminarDialogo":
          // Lo dicho se manda igual; con el modo en voz, después no se re-arma.
          setModo("voz");
          accionesRef.current.modo = "voz";
          void detenerYTranscribir("click");
          return;
        case "callar":
          if (accionesRef.current.modo === "dialogo") setModo("texto");
          callar();
          return;
        case "nada":
          return;
      }
    },
    [empezarAEscuchar, pasarADialogo, detenerYTranscribir, callar],
  );

  const alClick = useCallback(
    (evento: MouseEvent) => {
      if (evento.button !== 0) return;
      const ahora = performance.now();
      const { estado: estadoActual, grabando: grabandoActual, modo: modoActual, texto: textoActual } =
        accionesRef.current;
      const rachaAnterior = rachaRef.current;
      const { dentroDeControl, dentroDelCuadro, enBolita } = clasificarObjetivo(evento.target);

      // Con el chat abierto y sin racha de la píldora en curso, solo la
      // bolita es un gesto: el resto de los clicks son para leer, elegir
      // texto o usar los controles.
      if (estadoActual !== "reposo" && !rachaSigueViva(rachaAnterior, ahora)) {
        rachaRef.current = RACHA_VACIA;
        if (enBolita) tocarBolita(ahora);
        return;
      }

      const msDesdeCambioDeTamano =
        cambioDeTamanoRef.current === null ? null : Math.round(ahora - cambioDeTamanoRef.current);
      const { accion, racha } = decidir({
        estado: estadoActual,
        modo: modoActual,
        grabando: grabandoActual,
        textoVacio: textoActual.trim() === "",
        dentroDeControl: dentroDeControl && !enBolita,
        dentroDelCuadro,
        grabacionDesde: grabacionDesdeRef.current,
        msDesdeCambioDeTamano,
        respuestaQueda: true,
        ahora,
        racha: rachaAnterior,
      });
      rachaRef.current = racha;
      registrar("click", {
        n: racha.n,
        estado: estadoActual,
        modo: modoActual,
        grabando: grabandoActual,
        msDesdeAnterior: rachaAnterior.n === 0 ? -1 : Math.round(ahora - rachaAnterior.ultimo),
        msDesdeResize: msDesdeCambioDeTamano ?? -1,
        accion: accion.tipo,
        ...(accion.tipo === "nada" ? { razon: accion.razon } : {}),
      });
      // Una racha que empezó en la píldora no cierra el chat ni manda texto:
      // solo abre, dicta o conversa.
      if (estadoActual !== "reposo" && (accion.tipo === "volverAReposo" || accion.tipo === "mandarTexto")) return;
      ejecutar(accion, "click", ahora);
    },
    [ejecutar, tocarBolita],
  );

  useEffect(() => {
    const alPresionarEnCaptura = (evento: MouseEvent) => {
      if (evento.button !== 0) return;
      const { dentroDelCuadro } = clasificarObjetivo(evento.target);
      if (!dentroDelCuadro) return;
      if (accionesRef.current.texto.trim() === "" && rachaSigueViva(rachaRef.current, performance.now())) {
        evento.preventDefault();
      }
    };
    window.addEventListener("mousedown", alPresionarEnCaptura, { capture: true });
    window.addEventListener("click", alClick, { capture: true });
    return () => {
      window.removeEventListener("mousedown", alPresionarEnCaptura, { capture: true });
      window.removeEventListener("click", alClick, { capture: true });
    };
  }, [alClick]);

  // ⌃⌥R: la palanca de siempre.
  useEffect(() => {
    const suscripcion = alPalanca(() => {
      const { estado: estadoActual, modo: modoActual, grabando: grabandoActual } = accionesRef.current;
      const accion = decidirPalanca({ estado: estadoActual, modo: modoActual, grabando: grabandoActual });
      registrar("palanca", { estado: estadoActual, modo: modoActual, grabando: grabandoActual, accion: accion.tipo });
      if (accion.tipo === "terminarDialogo") {
        setModo("voz");
        accionesRef.current.modo = "voz";
        void detenerYTranscribir("atajo");
        return;
      }
      ejecutar(accion, "atajo", performance.now());
    });
    return () => {
      void suscripcion.then((desuscribir) => desuscribir());
    };
  }, [ejecutar, detenerYTranscribir]);

  // Se arrastra desde cualquier zona sin texto ni controles.
  const alPresionar = useCallback((evento: React.MouseEvent<HTMLDivElement>) => {
    if (evento.button !== 0) return;
    despertarAudio();
    if ((evento.target as HTMLElement).closest(SELECTOR_SIN_ARRASTRE)) return;
    const inicio = { x: evento.clientX, y: evento.clientY };
    function alMover(e: MouseEvent) {
      if (Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) < UMBRAL_ARRASTRE_PX) return;
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

  // — Acciones del chat —

  const copiar = useCallback(async (contenido: string) => {
    const pudo = await copiarAlPortapapeles(contenido);
    if (!pudo) console.warn("[portapapeles] no se pudo copiar");
    return pudo;
  }, []);

  const reintentar = useCallback(() => {
    const ultimo = ultimoEnviadoRef.current;
    if (!ultimo) return;
    registrar("reintentar", { palabras: ultimo.texto.split(/\s+/).length });
    // La respuesta vieja se va: la nueva ocupa su lugar.
    setMensajes((actuales) =>
      actuales.length > 0 && actuales[actuales.length - 1].rol === "remi" ? actuales.slice(0, -1) : actuales,
    );
    void enviar(ultimo.texto, "texto", true);
  }, [enviar]);

  // Pegar una charla larga (3c · 7): Remi pregunta en una línea si la
  // guarda. Con Sí, se resume (Ollama, o Haiku) y queda como episodio en la
  // bóveda y en memoria; con No, sigue en el campo como cualquier texto.
  const guardarPegado = useCallback(
    async (pegado: string) => {
      const miGeneracion = generacionRef.current;
      setTexto((actual) => actual.replace(pegado, "").trim());
      setEstado("pensando");
      registrar("episodio", { caracteres: pegado.length });
      try {
        const episodio = await guardarEpisodio(pegado);
        if (generacionRef.current !== miGeneracion) return;
        registrar("episodio:guardado", { archivo: episodio.archivo, por: episodio.resumido_por });
        agregar({ rol: "remi", texto: `Guardada: «${episodio.titulo}». Quedó en episodios/${episodio.archivo}.` });
      } catch (error) {
        if (generacionRef.current !== miGeneracion) return;
        console.error("no se pudo guardar la charla:", error);
        setTexto(pegado);
        agregar({ rol: "remi", texto: "No pude guardarla ahora. La dejé en el campo." });
      }
      setEstado("escuchando");
    },
    [agregar],
  );

  const preguntarSiGuardo = useCallback(
    (pegado: string) => {
      const id = nuevoId();
      const quitar = () => setMensajes((actuales) => actuales.filter((m) => m.id !== id));
      setMensajes((actuales) => [
        ...actuales,
        {
          id,
          rol: "remi",
          texto: "¿Lo guardo como conversación?",
          pregunta: {
            onSi: () => {
              quitar();
              void guardarPegado(pegado);
            },
            onNo: () => {
              quitar();
              campoRef.current?.enfocar();
            },
          },
        },
      ]);
    },
    [guardarPegado],
  );

  const escuchar = useCallback(
    (frase: string) => {
      registrar("escuchar", { palabras: frase.split(/\s+/).length });
      void decir(frase);
    },
    [decir],
  );

  if (estado === "reposo") {
    return (
      <div className="ventanita ventanita--reposo" onMouseDown={alPresionar}>
        <Semaforo />
        <div className="punto-zona">
          <StatusDot estado="reposo" />
        </div>
        {recordatorio !== null && <p className="num hace recordatorio-motor">{recordatorio}</p>}
        {recordatorio === null && ultimaVezDeHoy !== null && (
          <p className="num hace">la última vez: {formatearDuracion(ultimaVezDeHoy)}</p>
        )}
        {recordatorio === null && ultimaVezDeHoy === null && ultimaInteraccionMs !== null && (
          <p className="num hace">{formatearHace(ultimaInteraccionMs, ahoraMs)}</p>
        )}
      </div>
    );
  }

  return (
    <div className={`ventanita ventanita--chat ventanita--${estado}`} onMouseDown={alPresionar}>
      <Semaforo />
      <BotonCancelar onCancelar={() => cancelar("x")} />
      <div
        className="bolita"
        role="button"
        tabIndex={0}
        aria-label={grabando ? "Parar de escuchar" : "Hablarle a Remi (dos toques: conversación)"}
        title={grabando ? (modo === "dialogo" ? "Terminar la conversación" : "Parar y ver el texto") : "Un toque: dictar · dos: conversar"}
      >
        <StatusDot estado={estado} escuchandoVoz={grabando} medirVoz={estadoDeVoz} />
        {grabando && modo === "dialogo" && <p className="num modo-escucha">conversación</p>}
        {transcribiendo && <p className="num trabajando">transcribiendo</p>}
      </div>

      <Chat
        mensajes={mensajes}
        onEscuchar={escuchar}
        onCallar={callar}
        onCopiar={copiar}
        onReintentar={reintentar}
        onEnlace={(url) => registrar("enlace", { url })}
      />

      <Campo
        ref={campoRef}
        valor={texto}
        onCambio={setTexto}
        onEnviar={() => void enviar(texto, "texto")}
        onPegarLargo={preguntarSiGuardo}
      />

      <div
        className="asa"
        aria-hidden="true"
        title="Arrastrá para cambiar el tamaño"
        onMouseDown={(evento) => {
          if (evento.button !== 0) return;
          evento.preventDefault();
          evento.stopPropagation();
          void getCurrentWindow().startResizeDragging("SouthEast");
        }}
      >
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <path d="M9 1 L1 9 M9 5 L5 9" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
        </svg>
      </div>

      <div className="pie">
        <ChipCerebro eleccion={cerebro} motores={motores} modelosOllama={modelosOllama} onElegir={elegirCerebro} />
        <ChipVoz
          voz={vozElegida}
          velocidad={velocidad}
          voces={vocesDisponibles}
          onElegir={(nuevaVoz, nuevaVelocidad) => {
            cambiarVoz(nuevaVoz);
            cambiarVelocidad(nuevaVelocidad);
          }}
        />
      </div>
    </div>
  );
}

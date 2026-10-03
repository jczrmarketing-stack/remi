import { useCallback, useEffect, useRef, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { LogicalPosition, LogicalSize, currentMonitor, getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Semaforo } from "./componentes/Semaforo";
import { Chat, type Mensaje } from "./componentes/Chat";
import { chatAlVolver } from "./historial";
import { Nudge } from "./componentes/Nudge";
import { Campo, type CampoRef } from "./componentes/Campo";
import { ChipCerebro } from "./componentes/ChipCerebro";
import { ChipVoz } from "./componentes/ChipVoz";
import { ChipLectura } from "./componentes/ChipLectura";
import { Historial } from "./componentes/Historial";
import { useLectura } from "./lectura";
import {
  cerrarTarea,
  dondeQuede,
  enviarMensaje,
  enviarMensajeEnVivo,
  guardarEpisodio,
  empezarDeCero,
  obtenerConversacion,
  obtenerConversaciones,
  retomarConversacion,
  type ConversacionDeAntes,
  obtenerEntregaDeProyecto,
  obtenerModelosOllama,
  obtenerMotores,
  obtenerNudgePendiente,
  obtenerUltimaVezDeHoy,
  obtenerUltimaVezMin,
  responderNudge,
  type MotorDePensar,
} from "./servidor";
import type { Entrega, Nudge as NudgeContrato } from "./contratos";
import { MS_RECORDATORIO_VISIBLE, tocaRecordar } from "./recordatorio";
import { MS_ENTRE_CONSULTAS_NUDGE, type RespuestaNudge } from "./nudges";
import { animarTamano } from "./movimiento";
import {
  callarse,
  decirMuletilla,
  empezarLocucion,
  despertarAudio,
  estadoDeVoz,
  hablar,
  obtenerVoces,
  precalentarMuletillas,
  type VozDisponible,
} from "./voz";
import { copiarAlPortapapeles } from "./portapapeles";
import { partirRespuesta } from "./markdown";
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
import { mostrarTextoIsla, MS_NUDGE_VISIBLE, MS_ISLA_ENCOGER, MS_ISLA_VISIBLE, tamanoIsla, TAMANO_ISLA_MINIMA } from "./reposo";
import "./estilos.css";
import "./App.css";

// — Tamaños —
// Reposo es un cuadradito. Sin nada que decir, 72×72: solo el punto (3f · 1).
const TAMANO_REPOSO_MINIMO = TAMANO_ISLA_MINIMA;
// Abierta es el chat (3c): una sola pantalla, del tamaño que la dejaste
// (ventana.ts). Guardar tamaño y lugar espera a que dejes de mover.
const MS_GUARDAR_VENTANA = 400;
const REFRESCO_HACE_MS = 30000;
const DURACION_APARECER = 250;
// Retomar (3f · 7): al abrir en texto, solo los últimos 3 mensajes de la
// conversación vigente, sin nada nuevo dicho todavía.
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

function tamanoReposo(mostrarTexto: boolean, conNudge = false) {
  return tamanoIsla(mostrarTexto, conNudge);
}

// Qué es un control (nunca un gesto de la píldora) y qué es el campo.
const SELECTOR_CONTROLES = ".chat, .pie, .semaforo__punto, .bolita, .asa, .historial, button, select, a";
const SELECTOR_CUADRO = ".campo";
// Desde dónde NO se arrastra la ventana: donde hay texto o controles.
const SELECTOR_SIN_ARRASTRE = ".chat__mensaje, .campo, .pie, .semaforo__punto, .bolita, .asa, .historial";

function clasificarObjetivo(objetivo: EventTarget | null) {
  const elemento = objetivo instanceof HTMLElement ? objetivo : null;
  const dentroDeControl = Boolean(elemento?.closest(SELECTOR_CONTROLES));
  const dentroDelCuadro = !dentroDeControl && Boolean(elemento?.closest(SELECTOR_CUADRO));
  const enBolita = Boolean(elemento?.closest(".bolita"));
  return { dentroDeControl, dentroDelCuadro, enBolita };
}

// Ley 3: sin cadena de culpa. Si el núcleo no responde, Remi lo dice con calma.
const FRASE_DE_FALLO = "No pude contestarte ahora. Prueba de nuevo en un rato.";

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
  // Piel dinero (3f · 3): la entrega viva del proyecto del bloque abierto,
  // si tiene una. null la mayoría del tiempo: hoy nada le pone proyecto_id
  // a una tarea todavía (ver nucleo/servidor.py) — queda listo para cuando sí.
  const [entregaDelBloque, setEntregaDelBloque] = useState<Entrega | null>(null);
  // Reloj de una línea (3f · 4): cuánto tardó la última vez esta misma tarea.
  const [ultimaVezDelBloqueMin, setUltimaVezDelBloqueMin] = useState<number | null>(null);
  // Nudges dentro del chat (3f · 6). null casi siempre: solo hay uno si el
  // núcleo tiene uno pendiente (/nudges/pendiente, que puede no existir aún).
  const [nudgePendiente, setNudgePendiente] = useState<NudgeContrato | null>(null);
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
  const [historialAbierto, setHistorialAbierto] = useState(false);
  // Hablando (ronda 2): si le hablaste en voz alta, la bolita baja al centro
  // mientras Remi piensa y habla ahí. Escrito, la ventana no se mueve.
  const [bajada, setBajada] = useState(false);
  const [fraseDicha, setFraseDicha] = useState("");
  const ventanaRef = useRef<HTMLDivElement>(null);
  const bolitaRef = useRef<HTMLDivElement>(null);
  const [conversaciones, setConversaciones] = useState<ConversacionDeAntes[]>([]);
  const [ultimaVezDeHoy, setUltimaVezDeHoy] = useState<number | null>(null);

  // Tema Noche/Claro y lectura biónica (3d · 11).
  const [lectura, cambiarLectura] = useLectura();
  const campoRef = useRef<CampoRef>(null);
  // Lo que había en el campo antes de dictar: lo dictado se suma detrás.
  const baseDictadoRef = useRef("");
  // Sube al empezar y al parar cada grabación. Una transcripción parcial
  // que vuelve de otra grabación (o de una ya parada) no escribe nada: el
  // 30/09 a las 23:45 el campo se volvía a llenar con lo ya enviado.
  const grabacionIdRef = useRef(0);
  // Enter con el dictado andando: al terminar de transcribir, se manda.
  const enviarAlTranscribirRef = useRef(false);
  // El último mensaje que mandaste, para «otra respuesta».
  const ultimoEnviadoRef = useRef<{ texto: string; origen: OrigenMensaje } | null>(null);

  // Lo último que el dictado mostró en el campo mientras hablabas: al parar,
  // eso se queda a la vista y la versión final lo completa.
  const ultimoParcialRef = useRef("");
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
  // V3: los tiempos de un turno de voz, para la línea «latencia …» del log.
  // fin_habla es cuando dejaste de hablar (la parada), transcrito cuando
  // Whisper devolvió el texto; lo demás lo pone enviar().
  const latenciaRef = useRef<{ finHablaMs: number; transcritoMs: number | null } | null>(null);
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
  const hayContenidoReposo = hayHace || hayUltimaVez;
  // Isla de reposo (3f · 1): al volver a reposo, 4 s mostrando el texto y
  // se encoge; con el mouse encima se vuelve a mostrar aunque ya se encogió.
  const [hoverIsla, setHoverIsla] = useState(false);
  const [vencioIsla, setVencioIsla] = useState(false);
  const mostrarTextoReposo = mostrarTextoIsla(vencioIsla ? MS_ISLA_VISIBLE : 0, hoverIsla, hayContenidoReposo);
  // El nudge en reposo: la isla se ensancha y lo dice ahí, sin abrir el chat.
  const nudgeEnReposo = nudgePendiente !== null && estado === "reposo";
  const reposoRef = useRef({ mostrarTextoReposo, nudgeEnReposo });
  reposoRef.current = { mostrarTextoReposo, nudgeEnReposo };

  useEffect(() => {
    if (estado !== "reposo") return;
    setVencioIsla(false);
    const id = window.setTimeout(() => setVencioIsla(true), MS_ISLA_VISIBLE);
    return () => window.clearTimeout(id);
  }, [estado]);

  // Mientras la animamos nosotros, los cambios de tamaño no son tuyos: no
  // se guardan.
  const animandoRef = useRef(false);
  // El verde del semáforo: agrandada al 90 % de la pantalla. Guarda de dónde
  // venía para volver; mientras está agrandada, su tamaño no se guarda.
  const [maximizada, setMaximizada] = useState(false);
  const maximizadaRef = useRef(false);
  const antesDeAgrandarRef = useRef<{ x: number; y: number; width: number; height: number } | null>(null);

  // Al arrancar: la píldora del tamaño justo y en el lugar donde la dejaste.
  useEffect(() => {
    const ventana = getCurrentWindow();
    const reposo = tamanoReposo(reposoRef.current.mostrarTextoReposo, reposoRef.current.nudgeEnReposo);
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
    const reposo = tamanoReposo(reposoRef.current.mostrarTextoReposo, reposoRef.current.nudgeEnReposo);
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
      if (animandoRef.current || maximizadaRef.current || accionesRef.current.estado === "reposo") return;
      window.clearTimeout(reloj);
      reloj = window.setTimeout(() => {
        void tamanoActual().then((t) => {
          if (animandoRef.current || maximizadaRef.current || accionesRef.current.estado === "reposo") return;
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

  // La isla se agranda o se encoge (200 ms) según haya texto para mostrar.
  const claveIsla = `${mostrarTextoReposo}-${nudgeEnReposo}`;
  const tamanoIslaAnteriorRef = useRef(claveIsla);
  useEffect(() => {
    // Durante la animación de cerrar, el tamaño lo pone ella.
    if (expandido || animandoRef.current) return;
    if (tamanoIslaAnteriorRef.current === claveIsla) {
      // Primer paint en reposo (o cambio de contenido sin cambio de tamaño):
      // fija el tamaño ya, sin animar.
      const { width, height } = tamanoReposo(mostrarTextoReposo, nudgeEnReposo);
      cambioDeTamanoRef.current = performance.now();
      void getCurrentWindow().setSize(new LogicalSize(width, height));
      return;
    }
    tamanoIslaAnteriorRef.current = claveIsla;
    const ventana = getCurrentWindow();
    const hasta = tamanoReposo(mostrarTextoReposo, nudgeEnReposo);
    void (async () => {
      animandoRef.current = true;
      cambioDeTamanoRef.current = performance.now();
      const desde = await tamanoActual();
      registrar("tamaño", { motivo: nudgeEnReposo ? "isla:nudge" : mostrarTextoReposo ? "isla:mostrar" : "isla:encoger", w: hasta.width, h: hasta.height });
      await animarTamano(ventana, desde, hasta, MS_ISLA_ENCOGER);
      cambioDeTamanoRef.current = performance.now();
      animandoRef.current = false;
    })();
  }, [expandido, claveIsla, mostrarTextoReposo, nudgeEnReposo]);

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

  // Al abrir: el chat de la conversación vigente, entero.
  useEffect(() => {
    if (!expandido) return;
    const miGeneracion = generacionRef.current;
    obtenerConversacion()
      .then(async (turnos) => {
        if (generacionRef.current !== miGeneracion) return;
        if (turnos.length > 0) {
          setMensajes((actuales) =>
            // Si ya hay mensajes de esta apertura (llegaron antes que la
            // historia), la historia va antes y no se duplica nada.
            actuales.length > 0 ? actuales : chatAlVolver(turnos).map((m) => ({ ...m, id: nuevoId() })),
          );
          return;
        }
        // Sin charla reciente: tres líneas del proyecto activo. Sin proyecto, silencio.
        const lineas = await dondeQuede().catch(() => [] as string[]);
        if (generacionRef.current !== miGeneracion || lineas.length === 0) return;
        setMensajes((actuales) =>
          actuales.length > 0 ? actuales : [{ id: nuevoId(), rol: "remi", texto: lineas.join("\n\n") }],
        );
      })
      .catch(() => undefined);
  }, [expandido]);

  // Piel dinero (3f · 3): el bloque abierto es el de la última respuesta de
  // Remi que abrió una tarea (`tipo: "hoy"`) y sigue sin cerrar — el mismo
  // criterio que «Hecha» en Chat.tsx. Si esa tarea tiene proyecto y ese
  // proyecto tiene una entrega viva, la bolita y el Reloj se pintan dinero.
  useEffect(() => {
    const ultimo = mensajes[mensajes.length - 1];
    const bloqueAbierto = ultimo?.tarea && ultimo.tarea.estado === "hoy" ? ultimo.tarea : null;
    if (!bloqueAbierto) {
      setEntregaDelBloque(null);
      setUltimaVezDelBloqueMin(null);
      return;
    }
    let vivo = true;
    if (bloqueAbierto.proyecto_id) {
      obtenerEntregaDeProyecto(bloqueAbierto.proyecto_id).then((entrega) => {
        if (vivo) setEntregaDelBloque(entrega);
      });
    } else {
      setEntregaDelBloque(null);
    }
    obtenerUltimaVezMin(bloqueAbierto.id).then((min) => {
      if (vivo) setUltimaVezDelBloqueMin(min);
    });
    return () => {
      vivo = false;
    };
  }, [mensajes]);

  // La bolita sabe a dónde bajar: un poco por encima del centro, que debajo
  // va la frase. Se mide al empezar a bajar, no antes.
  useEffect(() => {
    const bolita = bolitaRef.current;
    const ventana = ventanaRef.current;
    if (!bajada || !bolita || !ventana) return;
    const centroActual = bolita.offsetTop + bolita.offsetHeight / 2;
    bolita.style.setProperty("--baja-y", `${Math.max(0, ventana.clientHeight * 0.42 - centroActual)}px`);
  }, [bajada]);

  // La conversación por voz es una pantalla: al entrar, la bolita baja y el
  // texto se difumina, y así se queda mientras dura (no solo cuando Remi
  // habla). Se sale al tocar la bolita de nuevo o con la flecha (ahí el texto
  // vuelve y la conversación sigue). Sin voz de Remi (silenciada) no tiene
  // sentido esconder lo que contesta: ahí el texto se queda.
  useEffect(() => {
    if (modo === "dialogo") setBajada(!accionesRef.current.silenciado);
    else setBajada(false);
  }, [modo]);

  // — La voz de Remi —

  // Dice un texto. Mientras suena, el estado es «hablando» (la bolita late
  // con el volumen). Al terminar: en conversación de voz vuelve a
  // escucharte; si no, queda el chat abierto esperando.
  const decir = useCallback(async (frase: string, alTerminar?: () => void) => {
    const mia = ++locucionRef.current;
    setFraseDicha(frase);
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

  // V3: dice frases a medida que llegan del núcleo. Igual que decir(),
  // pero la locución queda abierta: enviar() le agrega cada frase con voz y
  // la cierra con el `fin`. Al terminar hace lo mismo que decir().
  const decirEnVivo = useCallback((alTerminar?: () => void, alPrimerSonido?: () => void) => {
    const mia = ++locucionRef.current;
    setFraseDicha("");
    setEstado("hablando");
    const { velocidad: vel, vozElegida: v } = accionesRef.current;
    const locucion = empezarLocucion(vel, v, alPrimerSonido);
    let dicho = "";
    void Promise.race([locucion.fin, new Promise((r) => window.setTimeout(r, TECHO_LOCUCION_MS))]).then(() => {
      if (locucionRef.current !== mia || accionesRef.current.estado !== "hablando") return;
      if (alTerminar) {
        alTerminar();
        return;
      }
      setEstado("escuchando");
    });
    return {
      agregar(frase: string) {
        dicho = dicho ? `${dicho} ${frase}` : frase;
        setFraseDicha(dicho);
        locucion.agregar(frase);
      },
      terminar: locucion.terminar,
    };
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
    setHistorialAbierto(false);
    callarse();
  }, []);

  // — El historial (T7) —
  const abrirHistorial = useCallback(() => {
    setAhoraMs(Date.now());
    setHistorialAbierto(true);
    obtenerConversaciones()
      .then(setConversaciones)
      .catch(() => setConversaciones([]));
  }, []);

  const elegirConversacion = useCallback((id: string) => {
    retomarConversacion(id)
      .then((turnos) => {
        generacionRef.current += 1;
        setMensajes(turnos.map((t) => ({ id: nuevoId(), rol: t.rol, texto: t.texto, historial: true })));
        setHistorialAbierto(false);
      })
      .catch(() => undefined);
  }, []);

  const conversacionNueva = useCallback(() => {
    empezarDeCero()
      .then(() => {
        generacionRef.current += 1;
        setMensajes([]);
        setHistorialAbierto(false);
      })
      .catch(() => undefined);
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
      // Hablándole en voz alta: «mmm, a ver…» al instante, mientras piensa.
      if (origen === "voz" && !accionesRef.current.silenciado) {
        decirMuletilla(accionesRef.current.vozElegida);
      }
      const elegido = paraEnviar(accionesRef.current.cerebro);
      const arranque = performance.now();
      registrar("enviar", {
        palabras: limpio.split(/\s+/).length,
        origen,
        cerebro: etiquetaDe(accionesRef.current.cerebro),
        reintento,
      });
      // V3: hablándole, la respuesta llega en frases y la voz arranca con
      // la primera. El mensaje de Remi aparece en el chat y va creciendo;
      // al final se reemplaza por la respuesta entera (la misma de /mensaje).
      const enDialogo = accionesRef.current.modo === "dialogo";
      const conVoz = origen === "voz" && !accionesRef.current.silenciado;
      const latencia = latenciaRef.current;
      latenciaRef.current = null;
      // En un objeto y no en variables sueltas: se escriben desde el
      // callback de cada frase, y así TypeScript no las da por nulas.
      const vivo = {
        habla: null as ReturnType<typeof decirEnVivo> | null,
        id: null as string | null,
        texto: "",
        primeraFraseMs: null as number | null,
        primerSonidoMs: null as number | null,
        finMs: null as number | null,
      };
      // Una sola línea por turno de voz, cuando ya se sabe todo: el fin y el
      // primer sonido pueden llegar en cualquier orden.
      const anotarLatencia = () => {
        if (!latencia || vivo.finMs === null) return;
        const desde = (ms: number | null) => (ms === null ? "-" : Math.round(ms - latencia.finHablaMs));
        registrar("latencia", {
          "fin_habla→transcrito": desde(latencia.transcritoMs),
          "→primera_frase": desde(vivo.primeraFraseMs),
          "→primer_sonido": desde(vivo.primerSonidoMs),
        });
      };
      let respuesta: Awaited<ReturnType<typeof enviarMensaje>> | null = null;
      try {
        if (conVoz) {
          respuesta = await enviarMensajeEnVivo(limpio, { think: true, ...elegido, origen }, (llegada) => {
            if (generacionRef.current !== miGeneracion) return;
            if (vivo.primeraFraseMs === null) vivo.primeraFraseMs = performance.now();
            vivo.texto = vivo.texto ? `${vivo.texto}\n${llegada.frase}` : llegada.frase;
            const texto = vivo.texto;
            if (vivo.id === null) {
              const id = nuevoId();
              vivo.id = id;
              setMensajes((actuales) => [...actuales, { id, rol: "remi", texto }]);
            } else {
              const id = vivo.id;
              setMensajes((actuales) => actuales.map((m) => (m.id === id ? { ...m, texto } : m)));
            }
            if (llegada.voz) {
              if (!vivo.habla) {
                vivo.habla = decirEnVivo(
                  enDialogo ? () => void empezarAEscucharRef.current("dialogo") : undefined,
                  () => {
                    vivo.primerSonidoMs = performance.now();
                    anotarLatencia();
                  },
                );
              }
              vivo.habla.agregar(llegada.voz);
            }
          });
          if (!respuesta && generacionRef.current === miGeneracion) {
            registrar("envivo:caída", { frases: vivo.texto ? vivo.texto.split("\n").length : 0 });
            respuesta = await enviarMensaje(limpio, { think: true, ...elegido, origen });
          }
        } else {
          respuesta = await enviarMensaje(limpio, { think: true, ...elegido, origen });
        }
      } catch (error) {
        console.error("no se pudo mandar el mensaje:", error);
      } finally {
        enviandoRef.current = false;
      }
      if (generacionRef.current !== miGeneracion) {
        vivo.habla?.terminar();
        return;
      }
      registrar(respuesta ? "respuesta" : "enviar:falló", {
        tipo: respuesta?.tipo ?? "-",
        ms: Math.round(performance.now() - arranque),
        enVivo: vivo.id !== null,
      });
      vivo.finMs = performance.now();
      if (vivo.habla === null || vivo.primerSonidoMs !== null) anotarLatencia();
      const ahora = Date.now();
      registrarInteraccion(ahora);
      setUltimaInteraccionMs(ahora);
      if (respuesta?.tokens) {
        const { modelo, entrada, salida } = respuesta.tokens;
        console.info(`[claude] ${modelo} · tokens entrada=${entrada} salida=${salida}`);
      }
      const visible = respuesta ? respuesta.texto || respuesta.voz : FRASE_DE_FALLO;
      const dicho = respuesta ? respuesta.voz : FRASE_DE_FALLO;
      if (vivo.id !== null) {
        const id = vivo.id;
        setMensajes((actuales) =>
          actuales.map((m) => (m.id === id ? { ...m, texto: visible, tarea: respuesta?.tarea, sesion: respuesta?.sesion } : m)),
        );
      } else {
        agregar({ rol: "remi", texto: visible, tarea: respuesta?.tarea, sesion: respuesta?.sesion });
      }
      // Habla si le hablaste (y la voz no está silenciada). Escrito, calla:
      // para oírla está el ícono de escuchar.
      if (conVoz) {
        if (vivo.habla) {
          // Ya está sonando lo que llegó en vivo; solo falta avisarle que no
          // viene más. Al terminar hace lo mismo que decir().
          vivo.habla.terminar();
          return;
        }
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
    [agregar, decir, decirEnVivo],
  );

  // — Escuchar —

  const abrirChat = useCallback(() => {
    setModo("texto");
    setEstado("escuchando");
    window.setTimeout(() => campoRef.current?.enfocar(), DURACION_APARECER);
  }, []);

  // Nudges dentro del chat (3f · 6): se pregunta cada 5 min si hay uno
  // pendiente. Si llega con la ventanita en reposo, la expande — sin
  // sonido, y sin pisar un nudge que ya estaba mostrado.
  useEffect(() => {
    let vivo = true;
    const consultar = () => {
      if (!vivo) return;
      obtenerNudgePendiente().then((nudge) => {
        if (!vivo || !nudge) return;
        // Uno a la vez, y nunca mientras escribes o hablas. Si ya lo dejaste
        // pasar (se fue solo a los 8 s), no vuelve a salir.
        if (nudgesVistosRef.current.has(nudge.id)) return;
        const { estado: actual, texto } = accionesRef.current;
        if (actual === "pensando" || actual === "hablando" || (actual === "escuchando" && texto.trim() !== "")) return;
        setNudgePendiente((previo) => previo ?? nudge);
      });
    };
    consultar();
    const id = window.setInterval(consultar, MS_ENTRE_CONSULTAS_NUDGE);
    return () => {
      vivo = false;
      window.clearInterval(id);
    };
  }, []);

  // En reposo el nudge se va solo a los 8 s, sin responderlo: ni «Listo» ni
  // «Ahora no», y no queda como fallo (ley 5). Con el mouse encima espera.
  const nudgesVistosRef = useRef(new Set<string>());
  const hoverIslaRef = useRef(false);
  hoverIslaRef.current = hoverIsla;
  useEffect(() => {
    if (!nudgeEnReposo || !nudgePendiente) return;
    const id = nudgePendiente.id;
    let temporizador = 0;
    const armar = (ms: number) => {
      temporizador = window.setTimeout(() => {
        if (hoverIslaRef.current) return armar(2000);
        nudgesVistosRef.current.add(id);
        setNudgePendiente((actual) => (actual?.id === id ? null : actual));
      }, ms);
    };
    armar(MS_NUDGE_VISIBLE);
    return () => window.clearTimeout(temporizador);
  }, [nudgeEnReposo, nudgePendiente]);

  const responderAlNudge = useCallback((respuesta: RespuestaNudge) => {
    setNudgePendiente((actual) => {
      if (actual) {
        nudgesVistosRef.current.add(actual.id);
        void responderNudge(actual.id, respuesta);
      }
      return null;
    });
  }, []);

  // — Banco de pruebas (⌘⌥ + tecla) —
  // Para ver en vivo cada pieza del diseño sin esperar a que pase de verdad:
  // fuerza un estado con datos de mentira. Nada de esto toca el núcleo: el
  // bloque de prueba («demo-») se cierra sin llamar al servidor.
  useEffect(() => {
    const TAREA_DEMO = {
      id: "demo-tarea", titulo: "Terminar el flujo de distribución", proyecto_id: null, estado: "hoy" as const,
      paso_minimo: "Abrir la tarjeta", estimado_min: null, real_min: null, hora: null, fecha_limite: null, compartible: false,
    };
    const sesionDemo = () => ({
      id: "demo-sesion", tarea_id: "demo-tarea", inicio: new Date(Date.now() - 12 * 60000).toISOString(),
      fin: null, real_min: 12, app_contexto: null,
    });
    const charla = (extra: Array<Omit<Mensaje, "id">> = []) =>
      setMensajes([
        { rol: "juan" as const, texto: "¿qué sigue hoy?" },
        { rol: "remi" as const, texto: "Hoy solo esto: la tarjeta. Cinco minutos." },
        ...extra,
      ].map((m) => ({ ...m, id: nuevoId() })));
    const nudgeDemo = (tipo: NudgeContrato["tipo"], voz: string) => {
      volverAReposo();
      window.setTimeout(() => setNudgePendiente({ id: `demo-${tipo}-${Date.now()}`, tipo, voz, salida_amable: true, respuesta: null }), 450);
    };
    const pasos: Record<string, () => void> = {
      Digit1: () => volverAReposo(),
      Digit2: () => { charla(); setBajada(false); setEstado("escuchando"); },
      Digit3: () => { charla(); setBajada(false); setEstado("pensando"); },
      Digit4: () => {
        charla();
        setBajada(true);
        setEstado("pensando");
        window.setTimeout(() => { setFraseDicha("Hoy solo esto: la tarjeta. Cinco minutos."); setEstado("hablando"); }, 1400);
        window.setTimeout(() => { setBajada(false); setEstado("escuchando"); }, 7500);
      },
      Digit5: () => { charla(); setBajada(false); setEstado("escuchando"); },
      Digit6: () => {
        charla([{ rol: "remi", texto: "Empezamos: terminar el flujo de distribución.", tarea: TAREA_DEMO, sesion: sesionDemo() }]);
        setBajada(false);
        setEstado("escuchando");
      },
      Digit7: () => {
        charla([{ rol: "remi", texto: "Empezamos: la entrega de Alfonso, que paga.", tarea: TAREA_DEMO, sesion: sesionDemo() }]);
        setBajada(false);
        setEstado("escuchando");
        window.setTimeout(
          () => setEntregaDelBloque({ id: "demo-entrega", cliente: "Alfonso", proyecto_id: "demo", fecha: new Date().toISOString(), monto: 1200, estado: "camino", compartible: true } as unknown as Entrega),
          120,
        );
      },
      Digit8: () => nudgeDemo("cuerpo", "Van dos horas. Agua, y seguimos."),
      Digit9: () => nudgeDemo("ritual", "Es hora de cerrar el día. ¿Lo revisamos juntos?"),
      Digit0: () => nudgeDemo("encoger", "Esto se quedó grande. Hoy solo el primer paso."),
      KeyN: () => { charla(); setBajada(false); setEstado("escuchando"); window.setTimeout(() => setNudgePendiente({ id: `demo-chat-${Date.now()}`, tipo: "cuerpo", voz: "Van dos horas. Agua, y seguimos.", salida_amable: true, respuesta: null }), 300); },
      KeyE: () => { setBajada(false); setMensajes([{ id: nuevoId(), rol: "juan", texto: "¿qué sigue hoy?" }, { id: nuevoId(), rol: "remi", texto: FRASE_DE_FALLO }]); setEstado("escuchando"); },
      KeyJ: () => { charla(); setBajada(false); setEstado("escuchando"); window.setTimeout(abrirHistorial, 250); },
    };
    function alTeclado(evento: KeyboardEvent) {
      if (!(evento.metaKey && evento.altKey)) return;
      const paso = pasos[evento.code];
      if (!paso) return;
      evento.preventDefault();
      registrar("demo", { tecla: evento.code });
      paso();
    }
    window.addEventListener("keydown", alTeclado);
    return () => window.removeEventListener("keydown", alTeclado);
  }, [volverAReposo, abrirHistorial]);

  const empezarAEscuchar = useCallback(async (modoNuevo: Modo) => {
    setModo(modoNuevo);
    setEstado("escuchando");
    setGrabando(true);
    grabacionIdRef.current += 1;
    baseDictadoRef.current = accionesRef.current.texto;
    ultimoParcialRef.current = "";
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
      latenciaRef.current = { finHablaMs: performance.now(), transcritoMs: null };
      grabacionIdRef.current += 1;
      grabacionDesdeRef.current = null;
      setGrabando(false);
      setTranscribiendo(true);
      // Dictando, lo que ya apareció en el campo se queda a la vista y
      // el campo queda libre mientras llega la versión final (Whisper tarda
      // más cuanto más hablaste: 55 s → 6 s). Conversando, o con Enter, no:
      // ahí hace falta el texto final para mandarlo.
      const previa = ultimoParcialRef.current;
      const adelantar = !enDialogo && !enviarAlTranscribirRef.current && previa !== "";
      if (adelantar) {
        registrar("dictado:adelantado", { caracteres: previa.length });
        setModo("texto");
        setEstado("escuchando");
        campoRef.current?.enfocar();
      } else {
        setEstado("pensando");
      }
      try {
        const transcripcion = await detenerEscuchaYTranscribir(origen);
        if (generacionRef.current !== miGeneracion) return;
        setTranscribiendo(false);
        registrar("transcrito", { origen, caracteres: transcripcion.length });
        if (latenciaRef.current) latenciaRef.current.transcritoMs = performance.now();
        vaciasSeguidasRef.current = 0;
        if (enDialogo) {
          setTexto(baseDictadoRef.current);
          await enviar(transcripcion, "voz");
          return;
        }
        // Dictado: el texto queda en el campo, para leerlo o corregirlo. Si
        // apretaste Enter mientras dictabas, se manda entero y el campo queda
        // limpio.
        const base = baseDictadoRef.current.trim();
        const completo = base ? `${base} ${transcripcion}` : transcripcion;
        if (enviarAlTranscribirRef.current) {
          enviarAlTranscribirRef.current = false;
          setModo("texto");
          await enviar(completo, "texto");
          return;
        }
        if (adelantar) {
          // Solo se completa si el campo sigue como lo dejó el dictado: si ya
          // lo editaste o lo mandaste, no se pisa.
          setTexto((actual) => (actual === previa ? completo : actual));
          return;
        }
        setTexto(completo);
        setModo("texto");
        setEstado("escuchando");
        campoRef.current?.enfocar();
      } catch (error) {
        if (generacionRef.current !== miGeneracion) return;
        setTranscribiendo(false);
        // Si no se entendió nada y habías apretado Enter, se manda lo que
        // ya estaba escrito.
        if (enviarAlTranscribirRef.current) {
          enviarAlTranscribirRef.current = false;
          setModo("texto");
          if (baseDictadoRef.current.trim()) {
            await enviar(baseDictadoRef.current, "texto");
            return;
          }
        }
        if (!adelantar) setTexto(baseDictadoRef.current);
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
      const deEsta = grabacionIdRef.current;
      transcribirParcial()
        .then((parcial) => {
          if (!vivo || !parcial || grabacionIdRef.current !== deEsta) return;
          const base = baseDictadoRef.current.trim();
          const visto = base ? `${base} ${parcial}` : parcial;
          ultimoParcialRef.current = visto;
          setTexto(visto);
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
      enviarAlTranscribirRef.current = false;
      grabacionIdRef.current += 1;
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
        // El cajón del historial se cierra primero; el siguiente Escape ya es el de siempre.
        if (historialAbierto) {
          setHistorialAbierto(false);
          return;
        }
        cancelar("escape");
        return;
      }
      if (evento.key.toLowerCase() === "m" && evento.metaKey && evento.shiftKey) {
        evento.preventDefault();
        setSilenciado(alternarSilencio());
        return;
      }
      // ⌘⇧C (3f · 8): copia el encargo cuando la respuesta activa es la
      // tarjeta de prompt (partirRespuesta lo marca como tipo "encargo").
      if (evento.key.toLowerCase() === "c" && evento.metaKey && evento.shiftKey) {
        const ultimo = mensajes[mensajes.length - 1];
        if (!ultimo || ultimo.rol !== "remi") return;
        const encargo = partirRespuesta(ultimo.texto).find((bloque) => bloque.tipo === "encargo");
        if (!encargo) return;
        evento.preventDefault();
        void copiarAlPortapapeles(encargo.texto).then((pudo) => registrar("encargo:copiar-atajo", { pudo }));
      }
    }
    window.addEventListener("keydown", alTeclado);
    return () => window.removeEventListener("keydown", alTeclado);
  }, [cancelar, mensajes, historialAbierto]);

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

  // Las muletillas se piden una vez, cuando Kokoro ya cargó (~15 s).
  useEffect(() => {
    const id = window.setTimeout(() => void precalentarMuletillas(accionesRef.current.vozElegida), 20000);
    return () => window.clearTimeout(id);
  }, []);

  useEffect(() => {
    if (vocesDisponibles.length > 0) return;
    obtenerVoces()
      .then(setVocesDisponibles)
      .catch(() => setVocesDisponibles([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandido]);

  // Cada media hora, en reposo: «piensas con X», y se va a los 4 s.
  useEffect(() => {
    const id = window.setInterval(() => {
      const ahora = Date.now();
      if (!tocaRecordar(ultimoRecordatorioRef.current, ahora, accionesRef.current.estado === "reposo")) return;
      ultimoRecordatorioRef.current = ahora;
      const etiqueta = etiquetaDe(accionesRef.current.cerebro);
      registrar("recordatorio:motor", { cerebro: etiqueta });
      setRecordatorio(`piensas con ${etiqueta}`);
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

  // Verde: agrandar al 90 % de la pantalla, centrada; otro click vuelve al
  // tamaño y lugar de antes.
  const alternarAgrandar = useCallback(async () => {
    const ventana = getCurrentWindow();
    animandoRef.current = true;
    cambioDeTamanoRef.current = performance.now();
    try {
      if (maximizadaRef.current && antesDeAgrandarRef.current) {
        const antes = antesDeAgrandarRef.current;
        await ventana.setPosition(new LogicalPosition(antes.x, antes.y));
        await ventana.setSize(new LogicalSize(antes.width, antes.height));
        maximizadaRef.current = false;
        setMaximizada(false);
        registrar("tamaño", { motivo: "restaurar", w: Math.round(antes.width), h: Math.round(antes.height) });
        return;
      }
      const pantalla = await pantallaActual();
      if (!pantalla) return;
      const [fisica, f, tam] = await Promise.all([ventana.outerPosition(), ventana.scaleFactor(), tamanoActual()]);
      antesDeAgrandarRef.current = { x: fisica.x / f, y: fisica.y / f, width: tam.width, height: tam.height };
      const grande = tamanoMaximo(pantalla);
      await ventana.setPosition(
        new LogicalPosition(
          Math.round(pantalla.x + (pantalla.width - grande.width) / 2),
          Math.round(pantalla.y + (pantalla.height - grande.height) / 2),
        ),
      );
      await ventana.setSize(new LogicalSize(grande.width, grande.height));
      maximizadaRef.current = true;
      setMaximizada(true);
      registrar("tamaño", { motivo: "agrandar", w: grande.width, h: grande.height });
    } finally {
      window.setTimeout(() => {
        animandoRef.current = false;
      }, MS_GUARDAR_VENTANA + 100);
    }
  }, []);

  // Al volver a la píldora, deja de estar agrandada: la próxima vez abre del
  // tamaño guardado.
  useEffect(() => {
    if (expandido || !maximizadaRef.current) return;
    maximizadaRef.current = false;
    setMaximizada(false);
    const antes = antesDeAgrandarRef.current;
    if (antes) void getCurrentWindow().setPosition(new LogicalPosition(antes.x, antes.y));
  }, [expandido]);

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

  // Paga de verdad: tiene monto y no está ya cobrada.
  const esDinero = entregaDelBloque != null && entregaDelBloque.monto != null && entregaDelBloque.estado !== "pagada";

  const escuchar = useCallback(
    (frase: string) => {
      registrar("escuchar", { palabras: frase.split(/\s+/).length });
      void decir(frase);
    },
    [decir],
  );

  if (estado === "reposo") {
    return (
      <div
        className="ventanita ventanita--reposo"
        onMouseDown={alPresionar}
        onMouseEnter={() => setHoverIsla(true)}
        onMouseLeave={() => setHoverIsla(false)}
      >
        <Semaforo enPildora onVerde={abrirChat} />
        {nudgeEnReposo && nudgePendiente ? (
          <>
            <div className="nudge-punto">
              <StatusDot estado="reposo" />
            </div>
          <Nudge
            voz={nudgePendiente.voz}
            tipo={nudgePendiente.tipo}
            enIsla
            onResponder={responderAlNudge}
            bionica={lectura.bionica ? lectura.intensidad : null}
          />
          </>
        ) : (
          <div className="punto-zona">
            <StatusDot estado="reposo" />
          </div>
        )}
        {!nudgeEnReposo && mostrarTextoReposo && recordatorio !== null && (
          <p className="num hace recordatorio-motor">{recordatorio}</p>
        )}
        {!nudgeEnReposo && mostrarTextoReposo && recordatorio === null && ultimaVezDeHoy !== null && (
          <p className="num hace">la última vez: {formatearDuracion(ultimaVezDeHoy)}</p>
        )}
        {!nudgeEnReposo && mostrarTextoReposo && recordatorio === null && ultimaVezDeHoy === null && ultimaInteraccionMs !== null && (
          <p className="num hace">{formatearHace(ultimaInteraccionMs, ahoraMs)}</p>
        )}
      </div>
    );
  }

  return (
    <div
      ref={ventanaRef}
      className={`ventanita ventanita--chat ventanita--${estado}${bajada ? " ventanita--baja" : ""}`}
      onMouseDown={alPresionar}
    >
      <Semaforo
        enPildora={false}
        onMinimizar={volverAReposo}
        onVerde={() => void alternarAgrandar()}
        maximizada={maximizada}
      />
      <div
        ref={bolitaRef}
        className="bolita"
        role="button"
        tabIndex={0}
        aria-label={grabando ? "Parar de escuchar" : "Hablarle a Remi (dos toques: conversación)"}
        title={grabando ? (modo === "dialogo" ? "Terminar la conversación" : "Parar y ver el texto") : "Un toque: dictar · dos: conversar"}
      >
        <StatusDot estado={estado} escuchandoVoz={grabando} medirVoz={estadoDeVoz} dinero={esDinero} />
        {grabando && modo === "dialogo" && <p className="num modo-escucha">conversación</p>}
        {transcribiendo && <p className="num trabajando">transcribiendo</p>}
      </div>

      {bajada && (
        <button
          type="button"
          className="volver-texto"
          aria-label="Volver al texto"
          title="Ver el texto (la conversación sigue)"
          onClick={() => {
            registrar("volverAlTexto");
            setBajada(false);
          }}
        >
          <svg width="8" height="12" viewBox="0 0 8 12" aria-hidden="true">
            <path d="M7 1 L1 6 L7 11 Z" fill="currentColor" />
          </svg>
        </button>
      )}

      {bajada && estado === "hablando" && (
        <div className="habla">
          <p className="display-it habla__frase">{fraseDicha}</p>
          <p className="num habla__esc">esc · callar</p>
        </div>
      )}

      <Historial
        abierto={historialAbierto}
        conversaciones={conversaciones}
        ahoraMs={ahoraMs}
        onAbrir={abrirHistorial}
        onCerrar={() => setHistorialAbierto(false)}
        onElegir={elegirConversacion}
        onNueva={conversacionNueva}
      />

      <Chat
        mensajes={mensajes}
        onEscuchar={escuchar}
        onCallar={callar}
        onCopiar={copiar}
        onReintentar={reintentar}
        onCerrarBloque={(id) => (id.startsWith("demo-") ? Promise.resolve(25) : cerrarTarea(id))}
        bionica={lectura.bionica ? lectura.intensidad : null}
        ultimaVezMin={ultimaVezDelBloqueMin}
        dinero={esDinero}
        onEnlace={(url) => {
          // Los links de una búsqueda (3c · 8) se abren en el navegador.
          registrar("enlace", { url });
          void openUrl(url).catch((error) => console.error("no pude abrir el link:", error));
        }}
      />

      {nudgePendiente && (
        <Nudge
          voz={nudgePendiente.voz}
          tipo={nudgePendiente.tipo}
          onResponder={responderAlNudge}
          bionica={lectura.bionica ? lectura.intensidad : null}
        />
      )}

      <Campo
        ref={campoRef}
        valor={texto}
        onCambio={setTexto}
        onEnviar={() => {
          // Enter mientras dictás: para, transcribe lo último y manda todo.
          if (accionesRef.current.grabando && accionesRef.current.modo === "voz") {
            enviarAlTranscribirRef.current = true;
            void detenerYTranscribir("enter");
            return;
          }
          void enviar(texto, "texto");
        }}
        onPegarLargo={preguntarSiGuardo}
      />

      <div
        className="asa"
        aria-hidden="true"
        title="Arrastra para cambiar el tamaño"
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
        <div className="pie__derecha">
          <ChipLectura lectura={lectura} onCambiar={cambiarLectura} />
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
    </div>
  );
}

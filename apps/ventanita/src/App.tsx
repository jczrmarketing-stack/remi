import { useCallback, useEffect, useRef, useState } from "react";
import { LogicalSize, getCurrentWindow } from "@tauri-apps/api/window";
import { StatusDot } from "./componentes/StatusDot";
import { Reloj } from "./componentes/Reloj";
import { PromptTerminal } from "./componentes/PromptTerminal";
import { AccionesRespuesta } from "./componentes/AccionesRespuesta";
import { AjustesVoz } from "./componentes/AjustesVoz";
import { Semaforo } from "./componentes/Semaforo";
import { BotonCancelar } from "./componentes/BotonCancelar";
import { ChipModelo } from "./componentes/ChipModelo";
import { Encargo } from "./componentes/Encargo";
import { limpiarMarkdown } from "./markdown";
import {
  enviarMensaje,
  obtenerMotores,
  obtenerUltimaVezDeHoy,
  obtenerUltimaVezMin,
  type MotorDePensar,
  type TipoMensaje,
} from "./servidor";
import { MS_RECORDATORIO_VISIBLE, tocaRecordar } from "./recordatorio";
import { animarTamano } from "./movimiento";
import { callarse, despertarAudio, estadoDeVoz, hablar, obtenerVoces, vozOcupada, type VozDisponible } from "./voz";
import { copiarAlPortapapeles } from "./portapapeles";
import { formatearDuracion, formatearHace, registrarInteraccion, ultimaInteraccion } from "./tiempo";
import {
  alternarSilencio,
  type Cerebro,
  cerebroDe,
  eleccionDe,
  estaSilenciado,
  estaSinPensar,
  fijarModo,
  fijarMotor,
  fijarNivel,
  fijarSinPensar,
  fijarVelocidad,
  fijarVoz,
  MOTOR_POR_DEFECTO,
  type Nivel,
  nivelPorDefecto,
  obtenerModo,
  obtenerMotor,
  obtenerNivel,
  tieneNivel,
  type ModoPensar,
  obtenerVelocidad,
  obtenerVoz,
  type PreferenciaVoz,
  type Velocidad,
} from "./preferencias";
import {
  activarCortePorSilencio,
  alDetectarSilencio,
  cancelarEscucha,
  alPalanca,
  detenerEscuchaYTranscribir,
  iniciarEscucha,
  type OrigenParada,
} from "./microfono";
import {
  cortePorSilencioAplica,
  decidir,
  decidirPalanca,
  decidirTrasVacia,
  RACHA_VACIA,
  rachaSigueViva,
  type Accion,
  type Racha,
} from "./gestos";

// Qué es un control (nunca un gesto) y qué es el cuadro (gesto si está
// vacío y la racha sigue viva). Los botones del cuadro —el toggle de
// pensar— cuentan como control aunque estén dentro del cuadro.
const SELECTOR_CONTROLES = ".acciones-respuesta, .semaforo, .chip-modelo, .encargo, .voz, button, select";
const SELECTOR_CUADRO = ".prompt-terminal";

function clasificarObjetivo(objetivo: EventTarget | null) {
  const elemento = objetivo instanceof HTMLElement ? objetivo : null;
  const dentroDeControl = Boolean(elemento?.closest(SELECTOR_CONTROLES));
  const dentroDelCuadro = !dentroDeControl && Boolean(elemento?.closest(SELECTOR_CUADRO));
  return { dentroDeControl, dentroDelCuadro };
}
import { enchufarConsola, registrar } from "./registro";
import type { Estado, Modo, OrigenMensaje } from "./tipos";
import "./estilos.css";
import "./App.css";

// Reposo es una píldora. Sin historia (primer uso), 120×44: solo el punto.
// Con «hace 6 min» debajo, 120×64. Y con el dato medido de la ley 1 («la
// última vez: 1 h 40») hace falta ancho: la línea es del doble de largo y
// no se parte, se lee entera o no se muestra.
const TAMANO_REPOSO_MINIMO = { width: 120, height: 44 };
const TAMANO_REPOSO_CON_HACE = { width: 120, height: 64 };
const TAMANO_REPOSO_ULTIMA_VEZ = { width: 210, height: 64 };
// Expandida: 420 de ancho, y de alto lo que pida lo que hay adentro, entre
// 210 y 520 (maqueta de Juan Camilo, 30/09/2026). Escribiendo, 210: el cuadro,
// el chip y los atajos. Contestando, crece con la respuesta.
const TAMANO_EXPANDIDO = { width: 420, height: 210 };
const ALTO_MAXIMO = 520;
// Cada cuánto se refresca el «hace N min» en reposo. Es relativo y en
// minutos: medio minuto sobra y nada parpadea.
const REFRESCO_HACE_MS = 30000;

function tamanoReposo(hayHace: boolean, hayUltimaVez: boolean) {
  if (hayUltimaVez) return TAMANO_REPOSO_ULTIMA_VEZ;
  return hayHace ? TAMANO_REPOSO_CON_HACE : TAMANO_REPOSO_MINIMO;
}
const DURACION_APARECER = 250;
// Tiempo de "hablando" cuando Remi NO dice la frase en voz alta (mensaje
// escrito, o voz silenciada): depende del largo del texto, para leerla.
// Un click la cierra antes en cualquier momento. Cuando sí habla, dura lo
// que dure la locución real (a la velocidad elegida), con un techo por si
// el sintetizador nunca avisa que terminó.
// Leer un párrafo lleva tiempo: ~260 ms por palabra, hasta 45 s. Y con el
// puntero encima de la respuesta no se cierra nunca (ver `sostenido`).
const MS_POR_PALABRA_HABLANDO = 260;
const DURACION_HABLANDO_MINIMA = 2500;
const DURACION_HABLANDO_MAXIMA = 45000;
const TECHO_LOCUCION_MS = 60000;

function duracionHablando(frase: string): number {
  const palabras = frase.trim() ? frase.trim().split(/\s+/).length : 0;
  const calculada = DURACION_HABLANDO_MINIMA + palabras * MS_POR_PALABRA_HABLANDO;
  return Math.min(DURACION_HABLANDO_MAXIMA, calculada);
}
// Por debajo de esto es un click; por encima, arrastrás la ventana.
const UMBRAL_ARRASTRE_PX = 4;


// Qué pasó con lo que dijiste, además de la respuesta. Solo si la escribió
// el modelo: «Guardada. La miramos en dos días.» ya lo dice sola.

function notaDe(tipo: TipoMensaje, delModelo: boolean): string | null {
  if (!delModelo) return null;
  if (tipo === "idea") return "a la bandeja";
  if (tipo === "hoy") return "reloj corriendo";
  return null;
}

// Ley 3: sin cadena de culpa. Si el núcleo no responde, Remi lo dice
// con calma y vuelve a reposo — nunca regaña ni cuenta el fallo.
function fraseDeFallo(): string {
  return "No pude guardarlo. Lo intento más tarde.";
}

// Antes del primer render: si algo falla al montar, tiene que quedar escrito.
enchufarConsola();

export default function App() {
  const [estado, setEstado] = useState<Estado>("reposo");
  const [modo, setModo] = useState<Modo>("texto");
  const [texto, setTexto] = useState("");
  // `voz` es lo que se dice; `respuestaTexto`, lo que se ve (completo).
  const [voz, setVoz] = useState("");
  const [respuestaTexto, setRespuestaTexto] = useState("");
  // Lo que además pasó con lo que dijiste, cuando la respuesta la escribió
  // el modelo: «guardada en la bandeja» o «reloj corriendo». Las frases
  // fijas ya lo dicen solas, así que ahí no hace falta.
  const [notaRespuesta, setNotaRespuesta] = useState<string | null>(null);
  // De qué tipo fue la última respuesta: un encargo se muestra distinto
  // (bloque mono + Copiar) y no se cierra solo.
  const [tipoRespuesta, setTipoRespuesta] = useState<TipoMensaje | null>(null);
  const [origenMensaje, setOrigenMensaje] = useState<OrigenMensaje>("texto");
  const [grabando, setGrabando] = useState(false);
  // Entre cortar la grabación y ver el texto: Remi transcribe (whisper
  // local). Antes ese hueco era mudo; ahora se ve, en `pensar`.
  const [transcribiendo, setTranscribiendo] = useState(false);
  const [silenciado, setSilenciado] = useState(() => estaSilenciado());
  const [velocidad, setVelocidad] = useState<Velocidad>(() => obtenerVelocidad());
  const [vozElegida, setVozElegida] = useState<PreferenciaVoz>(() => obtenerVoz());
  const [vocesDisponibles, setVocesDisponibles] = useState<VozDisponible[]>([]);
  // Pensar con Claude: opt-in POR MENSAJE. Nace apagado y se apaga solo
  // después de cada envío — nunca queda prendido de fondo gastando tokens.
  // Remi piensa siempre. «sin pensar» lo apaga y queda puesto (persistido).
  // «sin pensar» ya no se elige (30/09/2026): Remi piensa siempre. Si quedó
  // puesto de antes, se apaga al arrancar.
  const [sinPensar, setSinPensar] = useState(() => {
    if (estaSinPensar()) fijarSinPensar(false);
    return false;
  });
  // Rápido / equilibrio / inteligente: viaja en cada mensaje.
  // Prompt ya no es un modo aparte: está implícito. Uno guardado de antes
  // vuelve a Sonnet.
  const [modoPensar, setModoPensar] = useState<ModoPensar>(() => {
    const guardado = obtenerModo();
    if (guardado !== "prompt") return guardado;
    fijarModo("equilibrio");
    return "equilibrio";
  });
  // Con qué motor, elegido a conciencia en el dropdown y guardado.
  const [motor, setMotor] = useState(() => obtenerMotor());
  const [motores, setMotores] = useState<MotorDePensar[]>([]);
  // Cuánto piensa el modelo de Anthropic elegido (el «Medio» del chip).
  const [nivel, setNivel] = useState<Nivel>(
    () =>
      obtenerNivel() ??
      nivelPorDefecto(cerebroDe({ motor: obtenerMotor(), modo: obtenerModo(), sinPensar: estaSinPensar() })),
  );
  const cerebro: Cerebro = cerebroDe({ motor, modo: modoPensar, sinPensar });
  // Lo que Juan Camilo mandó: se ve bajo el punto gris mientras Remi piensa.
  const [textoEnviado, setTextoEnviado] = useState("");
  const ventanaRef = useRef<HTMLDivElement>(null);
  // Cada respuesta nueva suma uno. La locución se arranca una vez por
  // respuesta (y de nuevo solo si pedís leer, o cambiás velocidad o voz):
  // ahora que la respuesta se queda, pasar el mouse no la repite.
  const respuestaIdRef = useRef(0);
  const ultimaLocucionRef = useRef("");
  const locucionEnCursoRef = useRef<Promise<void> | null>(null);
  const altoRef = useRef<number>(TAMANO_EXPANDIDO.height);
  // El recordatorio de cada media hora: una etiqueta bajo el punto, en el
  // lugar del «hace N min», que aparece con un movimiento y se va.
  const [recordatorio, setRecordatorio] = useState<string | null>(null);
  const ultimoRecordatorioRef = useRef(Date.now());
  // Leer en voz alta a demanda: cada click suma uno y la locución
  // arranca (o se reinicia). Cero = nadie pidió leer.
  const [lecturas, setLecturas] = useState(0);
  const [copiado, setCopiado] = useState(false);
  // Ley 1 hecha visible en el Reloj: null hasta que sepamos si hay dato
  // real, y se queda null si no lo hay (nunca un número inventado).
  const [sesionInicio, setSesionInicio] = useState<string | null>(null);
  const [ultimaVezMin, setUltimaVezMin] = useState<number | null>(null);
  // Ley 1 en reposo: cuándo fue la última interacción (null = nunca).
  const [ultimaInteraccionMs, setUltimaInteraccionMs] = useState<number | null>(() =>
    ultimaInteraccion(),
  );
  const [ahoraMs, setAhoraMs] = useState(() => Date.now());
  // Ley 1 en reposo, medida y no de reloj: si lo que está en curso ya se
  // hizo antes, vale más decir cuánto tomó que cuánto hace que no lo tocás.
  const [ultimaVezDeHoy, setUltimaVezDeHoy] = useState<number | null>(null);

  // Los handlers viven en efectos y listeners; el ref evita re-suscribir.
  const textoVacio = texto.trim() === "";
  const accionesRef = useRef({ grabando, modo, estado, silenciado, sinPensar, textoVacio, motor, modoPensar, nivel });
  accionesRef.current = { grabando, modo, estado, silenciado, sinPensar, textoVacio, motor, modoPensar, nivel };

  // Cada vez que se vuelve a reposo a mano (click o Escape), esto sube:
  // si un fetch/invoke que ya estaba en vuelo resuelve DESPUÉS, se nota
  // que quedó viejo y no pisa el estado — si no, una respuesta tardía
  // podía saltar a "hablando" de la nada después de haber cancelado.
  const generacionRef = useRef(0);
  // true mientras un POST /mensaje está en vuelo. Es lo que impide mandar
  // dos veces, sin confundirlo con «pensando», que también es transcribir.
  const enviandoRef = useRef(false);
  // Cuándo cambió de tamaño la ventana por última vez (reloj de
  // performance.now). Los clicks fantasma llegan pegados a eso.
  const cambioDeTamanoRef = useRef<number | null>(null);
  // Cuándo arrancó —o se re-armó— la grabación viva (reloj de
  // performance.now). Es lo que mide el periodo de gracia de los gestos.
  const grabacionDesdeRef = useRef<number | null>(null);
  // En diálogo: escuchas vacías seguidas. No es un contador de fallos del
  // usuario (ley 3): es Remi dándose cuenta de que no era el momento.
  const vaciasSeguidasRef = useRef(0);
  const rearmeRef = useRef(0);

  // Cada cambio de estado queda escrito: es la columna vertebral del log.
  useEffect(() => {
    registrar("estado", { a: estado });
  }, [estado]);

  const expandido = estado !== "reposo";
  const expandidoAnteriorRef = useRef(expandido);
  const hayHace = ultimaInteraccionMs !== null || recordatorio !== null;
  const hayUltimaVez = ultimaVezDeHoy !== null;
  const reposoRef = useRef({ hayHace, hayUltimaVez });
  reposoRef.current = { hayHace, hayUltimaVez };

  // macOS restaura el tamaño de la última sesión (la app siempre arranca
  // en reposo, la ventana no debería): forzar el tamaño real al montar.
  useEffect(() => {
    const ventana = getCurrentWindow();
    const { width, height } = tamanoReposo(
      reposoRef.current.hayHace,
      reposoRef.current.hayUltimaVez,
    );
    // Los límites min/max vienen compilados desde tauri.conf.json, y un
    // binario que no se recompiló trae los viejos (320×180): macOS clampea
    // el setSize a ese mínimo y la ventana no encoge. Fijarlos en tiempo de
    // ejecución ANTES de pedir el tamaño hace que el reposo real entre por
    // hot reload sin depender de que Rust se vuelva a construir.
    registrar("tamaño", { motivo: "montar", w: width, h: height });
    cambioDeTamanoRef.current = performance.now();
    void (async () => {
      await ventana.setMinSize(
        new LogicalSize(TAMANO_REPOSO_MINIMO.width, TAMANO_REPOSO_MINIMO.height),
      );
      await ventana.setMaxSize(
        new LogicalSize(TAMANO_EXPANDIDO.width, ALTO_MAXIMO),
      );
      await ventana.setSize(new LogicalSize(width, height));
    })();
  }, []);

  useEffect(() => {
    if (expandidoAnteriorRef.current === expandido) return;
    expandidoAnteriorRef.current = expandido;
    const ventana = getCurrentWindow();
    const reposo = tamanoReposo(reposoRef.current.hayHace, reposoRef.current.hayUltimaVez);
    const actual = { width: TAMANO_EXPANDIDO.width, height: altoRef.current };
    const desde = expandido ? reposo : actual;
    const hasta = expandido ? TAMANO_EXPANDIDO : reposo;
    altoRef.current = TAMANO_EXPANDIDO.height;
    registrar("tamaño", {
      motivo: expandido ? "expandir" : "encoger",
      w: hasta.width,
      h: hasta.height,
    });
    cambioDeTamanoRef.current = performance.now();
    void animarTamano(ventana, desde, hasta, DURACION_APARECER).then(() => {
      // La animación dura 250 ms: el «último cambio» es cuando termina.
      cambioDeTamanoRef.current = performance.now();
    });
  }, [expandido]);

  // Expandida, el alto sigue al contenido: escribiendo, 210; pensando o
  // contestando, lo que mida la frase, hasta 520 (después se desplaza
  // adentro). Se mide después de la animación de expandir, que dura 250 ms.
  useEffect(() => {
    if (!expandido) return;
    const id = window.setTimeout(() => {
      const raiz = ventanaRef.current;
      if (!raiz) return;
      const estilo = getComputedStyle(raiz);
      const hueco = parseFloat(estilo.rowGap) || 0;
      let alto =
        parseFloat(estilo.paddingTop) + parseFloat(estilo.paddingBottom) +
        parseFloat(estilo.borderTopWidth) + parseFloat(estilo.borderBottomWidth);
      let hijos = 0;
      for (const hijo of Array.from(raiz.children) as HTMLElement[]) {
        if (getComputedStyle(hijo).position === "absolute") continue;
        alto += Math.max(hijo.scrollHeight, hijo.offsetHeight);
        hijos += 1;
      }
      alto += hueco * Math.max(0, hijos - 1);
      const escribiendo = estado === "escuchando" && !grabando && modo !== "dialogo";
      const meta =
        escribiendo
          ? TAMANO_EXPANDIDO.height
          : Math.min(ALTO_MAXIMO, Math.max(TAMANO_EXPANDIDO.height, Math.ceil(alto)));
      if (meta === altoRef.current) return;
      altoRef.current = meta;
      registrar("tamaño", { motivo: `contenido:${estado}`, w: TAMANO_EXPANDIDO.width, h: meta });
      cambioDeTamanoRef.current = performance.now();
      void getCurrentWindow().setSize(new LogicalSize(TAMANO_EXPANDIDO.width, meta));
    }, DURACION_APARECER + 30);
    return () => window.clearTimeout(id);
  }, [expandido, estado, respuestaTexto, textoEnviado, tipoRespuesta, transcribiendo, grabando, modo]);

  // El dato de la ley 1 llega después de volver a reposo (hay que
  // preguntárselo al núcleo): cuando llega, la píldora se ensancha para
  // que la línea entre entera.
  useEffect(() => {
    if (expandido) return;
    const { width, height } = tamanoReposo(hayHace, hayUltimaVez);
    registrar("tamaño", { motivo: "reposo", w: width, h: height });
    cambioDeTamanoRef.current = performance.now();
    void getCurrentWindow().setSize(new LogicalSize(width, height));
  }, [expandido, hayHace, hayUltimaVez]);

  // En reposo, el «hace N min» se refresca solo, despacio.
  useEffect(() => {
    if (expandido || !hayHace) return;
    setAhoraMs(Date.now());
    const id = window.setInterval(() => setAhoraMs(Date.now()), REFRESCO_HACE_MS);
    return () => window.clearInterval(id);
  }, [expandido, hayHace]);

  // Al volver a reposo se pregunta si hay algo de hoy con historial. Si el
  // núcleo no contesta, queda el «hace N min» y listo: nada que avisar.
  useEffect(() => {
    if (expandido) return;
    obtenerUltimaVezDeHoy()
      .then(setUltimaVezDeHoy)
      .catch(() => setUltimaVezDeHoy(null));
  }, [expandido, ultimaInteraccionMs]);

  const volverAReposo = useCallback(() => {
    generacionRef.current += 1;
    setEstado("reposo");
    setModo("texto");
    setGrabando(false);
    setTranscribiendo(false);
    setTexto("");
    setVoz("");
    setRespuestaTexto("");
    setTextoEnviado("");
    setSesionInicio(null);
    setUltimaVezMin(null);
    window.clearTimeout(rearmeRef.current);
    vaciasSeguidasRef.current = 0;
    grabacionDesdeRef.current = null;
    setLecturas(0);
    setCopiado(false);
    callarse();
  }, []);

  // La X y Escape: cancelan lo que esté pasando, sin transcribir ni mandar.
  // Si estaba grabando, se corta y se borra el audio (Whisper no trabaja);
  // si estaba pensando, la respuesta que llegue ya no es de esta
  // generación y se descarta; si hablaba, se calla.
  const cancelar = useCallback(
    (origen: "escape" | "x") => {
      const { grabando: grabandoActual, estado: estadoActual } = accionesRef.current;
      registrar("cancelar", { origen, estado: estadoActual, grabando: grabandoActual });
      if (grabandoActual) {
        void cancelarEscucha(origen).catch(() => undefined);
      }
      volverAReposo();
    },
    [volverAReposo],
  );

  const enviar = useCallback(
    async (mensaje: string, reintento = false) => {
      const limpio = mensaje.trim();
      if (!limpio) return;
      // Un doble Cmd+Enter (u onEnviar disparado dos veces) no manda dos
      // tareas. La guarda mira si hay un ENVÍO en curso, no el estado de la
      // pantalla: antes miraba «pensando», y el diálogo pone pensando
      // mientras transcribe, así que al ir a mandar lo transcrito la guarda
      // lo frenaba en silencio. El diálogo nunca pudo mandar (17:22:16).
      if (enviandoRef.current) {
        registrar("enviar:ignorado", { motivo: "ya hay un envío en curso" });
        return;
      }
      if (accionesRef.current.estado === "hablando" && !reintento) {
        registrar("enviar:ignorado", { motivo: "Remi está hablando" });
        return;
      }
      enviandoRef.current = true;
      if (reintento) callarse();
      // Una respuesta nueva arranca limpia: sin «copiada» y sin la lectura
      // que pediste para la anterior.
      setLecturas(0);
      setCopiado(false);
      const miGeneracion = generacionRef.current;
      // Todo mensaje pasa por el modelo —texto, dictado, diálogo— salvo que
      // «sin pensar» esté puesto. Antes pensar era opt-in y se apagaba solo
      // tras cada envío: por texto, Remi nunca pensaba (19:26, 23 ms).
      const think = !accionesRef.current.sinPensar;
      setEstado("pensando");
      const arranque = performance.now();
      const motorElegido = accionesRef.current.motor;
      const modoElegido = accionesRef.current.modoPensar;
      // El nivel solo viaja con un modelo de Anthropic.
      const nivelElegido =
        motorElegido === "claude" && modoElegido !== "prompt" ? accionesRef.current.nivel : null;
      setTextoEnviado(limpio);
      registrar("enviar", {
        palabras: limpio.split(/\s+/).length,
        think,
        motor: think ? motorElegido : "-",
        modo: think ? modoElegido : "-",
        nivel: think && nivelElegido ? nivelElegido : "-",
      });
      try {
        const respuesta = await enviarMensaje(limpio, think, motorElegido, modoElegido, nivelElegido);
        if (generacionRef.current !== miGeneracion) return; // cancelado mientras esperaba
        registrar("respuesta", {
          tipo: respuesta.tipo,
          ms: Math.round(performance.now() - arranque),
        });
        const ahora = Date.now();
        registrarInteraccion(ahora);
        setUltimaInteraccionMs(ahora);
        if (respuesta.tokens) {
          const { modelo, entrada, salida } = respuesta.tokens;
          console.info(`[claude] ${modelo} · tokens entrada=${entrada} salida=${salida}`);
        } else if (think) {
          console.info("[claude] pidió pensar pero el núcleo siguió sin IA (¿falta la clave en nucleo/.env?)");
        }
        setVoz(respuesta.voz);
        setRespuestaTexto(respuesta.texto || respuesta.voz);
        respuestaIdRef.current += 1;
        setNotaRespuesta(notaDe(respuesta.tipo, respuesta.tokens !== null));
        setTipoRespuesta(respuesta.tipo);
        // Solo un bloque abierto tiene reloj: una idea que enfría y un
        // cierre no tienen nada que medir.
        setSesionInicio(respuesta.sesion?.inicio ?? null);
        const tareaId = respuesta.tarea?.id;
        if (tareaId !== undefined) {
          // Si esto falla, el Reloj simplemente no se renderiza — no es
          // motivo para no poder contestar (ley 3, sin culpa).
          obtenerUltimaVezMin(tareaId)
            .then((valor) => {
              if (generacionRef.current === miGeneracion) setUltimaVezMin(valor);
            })
            .catch(() => {
              if (generacionRef.current === miGeneracion) setUltimaVezMin(null);
            });
        }
      } catch (error) {
        if (generacionRef.current !== miGeneracion) return;
        registrar("enviar:falló", { ms: Math.round(performance.now() - arranque) });
        console.error("no se pudo mandar el mensaje:", error);
        setVoz(fraseDeFallo());
        setRespuestaTexto(fraseDeFallo());
        setNotaRespuesta(null);
        setTipoRespuesta(null);
      } finally {
        enviandoRef.current = false;
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
    const cortarSolo = modoNuevo === "dialogo";
    grabacionDesdeRef.current = performance.now();
    registrar("iniciarEscucha", { modo: modoNuevo, cortarSolo });
    try {
      // En diálogo corta sola cuando dejás de hablar; en modo voz,
      // como Handy: vos la cortás con otro click.
      await iniciarEscucha(cortarSolo);
    } catch (error) {
      // Sin micrófono disponible: cae a escritura manual, sin culpa (ley 3).
      console.error("no se pudo prender el micrófono:", error);
      registrar("iniciarEscucha:falló", { modo: modoNuevo });
      grabacionDesdeRef.current = null;
      setGrabando(false);
      setModo("texto");
      setOrigenMensaje("texto");
    }
  }, []);

  const detenerYTranscribir = useCallback(async (origen: OrigenParada) => {
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
      if (generacionRef.current !== miGeneracion) return; // cancelado mientras transcribía
      setTranscribiendo(false);
      registrar("transcrito", { origen, caracteres: transcripcion.length });
      vaciasSeguidasRef.current = 0;
      setTexto(transcripcion);
      if (enDialogo) {
        // En diálogo no se edita: lo dicho se manda solo.
        await enviar(transcripcion);
        return;
      }
      setEstado("escuchando");
    } catch (error) {
      if (generacionRef.current !== miGeneracion) return;
      setTranscribiendo(false);
      registrar("sinTranscripcion", { origen, enDialogo });
      // No escuchó nada (o no se entendió): sin culpa (ley 3).
      console.error("no se pudo transcribir:", error);
      if (!enDialogo) {
        setEstado("escuchando");
        return;
      }
      // En diálogo no hay cuadro para escribir: si no la dejamos escuchando
      // de nuevo, queda muda. Pero no en el acto —un dedo tardío caía sobre
      // la escucha nueva y la mataba— y no para siempre: dos vacías
      // seguidas quieren decir que no era el momento, y Remi se va callada.
      vaciasSeguidasRef.current += 1;
      const tras = decidirTrasVacia(vaciasSeguidasRef.current);
      if (tras.tipo === "reposo") {
        registrar("dialogo:meVoy", { vacias: vaciasSeguidasRef.current });
        volverAReposo();
        return;
      }
      registrar("dialogo:rearmo", { vacias: vaciasSeguidasRef.current, enMs: tras.enMs });
      window.clearTimeout(rearmeRef.current);
      rearmeRef.current = window.setTimeout(() => {
        if (generacionRef.current !== miGeneracion) return;
        void empezarAEscuchar("dialogo");
      }, tras.enMs);
    }
  }, [enviar, empezarAEscuchar, volverAReposo]);

  // El micrófono avisa cuando dejaste de hablar (solo en modo diálogo).
  // Si en 10 s no dijiste nada, Remi deja de esperar y vuelve a reposo —
  // sin frase, sin culpa (ley 3): simplemente no era el momento.
  useEffect(() => {
    const suscripcion = alDetectarSilencio((motivo) => {
      const { grabando: grabandoActual, modo: modoActual } = accionesRef.current;
      registrar("silencio", { motivo, grabando: grabandoActual, modo: modoActual });
      if (!grabandoActual) return;
      // Rust solo vigila el silencio en diálogo, pero si un aviso viejo
      // llegara durante un dictado, el dictado no se corta igual.
      if (!cortePorSilencioAplica(modoActual)) {
        registrar("silencio:ignorado", { motivo: "el dictado no corta por silencio" });
        return;
      }
      if (motivo === "sin_voz") {
        void cancelarEscucha("silencio:sin_voz").catch(() => undefined);
        volverAReposo();
        return;
      }
      void detenerYTranscribir("silencio:fin");
    });
    return () => {
      void suscripcion.then((desuscribir) => desuscribir());
    };
  }, [detenerYTranscribir, volverAReposo]);

  // Mute local a la ventana (no global de sistema): Cmd+Shift+M funciona
  // aunque estés escribiendo, porque los navegadores/webviews no meten
  // combos con Cmd en el campo de texto. Escape cancela todo.
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

  const cambiarVelocidad = useCallback((nueva: Velocidad) => {
    fijarVelocidad(nueva);
    setVelocidad(nueva);
  }, []);

  const cambiarVoz = useCallback((nueva: PreferenciaVoz) => {
    fijarVoz(nueva);
    setVozElegida(nueva);
  }, []);

  const cambiarMotor = useCallback((nuevo: string) => {
    fijarMotor(nuevo);
    setMotor(nuevo);
  }, []);

  // El chip: un modelo se traduce a motor + modo + «sin pensar», y el
  // nivel vuelve al de ese modelo.
  const cambiarCerebro = useCallback((nuevo: Cerebro) => {
    const eleccion = eleccionDe(nuevo);
    fijarMotor(eleccion.motor);
    setMotor(eleccion.motor);
    fijarModo(eleccion.modo);
    setModoPensar(eleccion.modo);
    fijarSinPensar(eleccion.sinPensar);
    setSinPensar(eleccion.sinPensar);
    if (tieneNivel(nuevo)) {
      const n = nivelPorDefecto(nuevo);
      fijarNivel(n);
      setNivel(n);
    }
  }, []);

  const cambiarNivel = useCallback((nuevo: Nivel) => {
    fijarNivel(nuevo);
    setNivel(nuevo);
  }, []);

  // Los motores los nombra el núcleo, con qué le falta a cada uno. Si no
  // contesta, el dropdown muestra el guardado y listo.
  useEffect(() => {
    obtenerMotores()
      .then((lista) => {
        setMotores(lista);
        // Si el motor guardado hoy no está (Ollama apagado, sin clave), no
        // se manda a ciegas para fallar: vuelve a Claude, y queda dicho.
        const actual = lista.find((m) => m.id === accionesRef.current.motor);
        if (actual && !actual.disponible) {
          registrar("motor:noDisponible", { motor: actual.id, detalle: actual.detalle });
          cambiarMotor(MOTOR_POR_DEFECTO);
        }
      })
      .catch(() => setMotores([]));
  }, [cambiarMotor]);

  // Cada media hora, en reposo: «pensás con X», con un solo movimiento, y
  // se va a los 4 s. Se mide desde el último recordatorio, no desde el
  // último uso, así que usar Remi seguido no lo posterga para siempre.
  useEffect(() => {
    const id = window.setInterval(() => {
      const ahora = Date.now();
      if (!tocaRecordar(ultimoRecordatorioRef.current, ahora, accionesRef.current.estado === "reposo")) return;
      ultimoRecordatorioRef.current = ahora;
      const actual = accionesRef.current.motor;
      const etiqueta = motores.find((m) => m.id === actual)?.label ?? actual;
      registrar("recordatorio:motor", { motor: actual });
      setRecordatorio(`pensás con ${etiqueta}`);
      window.setTimeout(() => setRecordatorio(null), MS_RECORDATORIO_VISIBLE);
    }, 60 * 1000);
    return () => window.clearInterval(id);
  }, [motores]);

  // Las voces las nombra el núcleo. Si no contesta, el selector queda solo
  // con "Auto" y Remi habla con la voz del sistema: nada que avisar.
  useEffect(() => {
    obtenerVoces()
      .then(setVocesDisponibles)
      .catch(() => setVocesDisponibles([]));
  }, []);

  const leerEnVozAlta = useCallback(() => {
    setLecturas((n) => n + 1);
  }, []);

  const copiar = useCallback(async () => {
    // Lo que dijiste y lo que contestó Remi, tal como se vieron.
    // Como en Claude: la respuesta, tal cual llegó.
    const pudo = await copiarAlPortapapeles(respuestaTexto);
    if (!pudo) {
      console.warn("[portapapeles] no se pudo copiar");
      return;
    }
    setCopiado(true);
  }, [respuestaTexto]);

  // Remi habla solo si ESTE mensaje llegó por voz y no está silenciada —
  // mirado una sola vez al entrar — o si pediste leerlo (botón). Si habla,
  // "hablando" dura hasta que la locución termina de verdad (cambiar la
  // velocidad o volver a pedir leer la reinicia); si no, un tiempo
  // proporcional al texto. Al terminar, en diálogo vuelve a escucharte
  // sola; si no, reposo. Un click la cierra antes (ver alClick).
  useEffect(() => {
    if (estado !== "hablando") return;

    let vigente = true;
    // Ninguna respuesta se cierra sola (Juan Camilo, 30/09/2026: «el
    // mensaje no se puede quitar hasta que yo lo quiera quitar»). Queda
    // hasta la X, Escape o un click cuando Remi ya terminó de hablar. La
    // excepción es el diálogo: al terminar vuelve a escucharte, con la
    // respuesta todavía a la vista bajo el punto.
    const queda = accionesRef.current.modo !== "dialogo";
    const terminar = () => {
      if (!vigente) return;
      vigente = false;
      if (queda) return;
      if (accionesRef.current.modo === "dialogo") {
        setTexto("");
        setVoz("");
        void empezarAEscuchar("dialogo");
        return;
      }
      volverAReposo();
    };

    registrar("hablando", { origen: origenMensaje, lecturas, velocidad, palabras: voz.split(/\s+/).length });
    const habla = lecturas > 0 || (origenMensaje === "voz" && !accionesRef.current.silenciado);
    const locucion = `${respuestaIdRef.current}|${lecturas}|${velocidad}|${vozElegida}`;
    let techo: number | undefined;
    if (habla && locucion !== ultimaLocucionRef.current) {
      ultimaLocucionRef.current = locucion;
      locucionEnCursoRef.current = hablar(voz, velocidad, vozElegida);
      void locucionEnCursoRef.current.then(terminar);
      techo = window.setTimeout(terminar, TECHO_LOCUCION_MS);
    } else if (habla) {
      // Re-render con la misma locución en curso: se engancha al mismo fin.
      void locucionEnCursoRef.current?.then(terminar);
    } else if (!habla && !queda) {
      techo = window.setTimeout(terminar, duracionHablando(respuestaTexto));
    }

    return () => {
      vigente = false;
      window.clearTimeout(techo);
      // Solo se calla si se fue de «hablando»: un re-render cualquiera no
      // puede cortarla a mitad de frase.
      if (accionesRef.current.estado !== "hablando") callarse();
    };
  }, [
    estado,
    voz,
    respuestaTexto,
    tipoRespuesta,
    origenMensaje,
    velocidad,
    vozElegida,
    lecturas,
    empezarAEscuchar,
    volverAReposo,
  ]);

  // Click: escribís · doble click: te escucha · triple click: dialogan.
  // Las reglas viven en gestos.ts; acá solo se ejecuta lo que decidan.
  const ejecutar = useCallback(
    (accion: Accion, origen: OrigenParada, ahora: number) => {
      switch (accion.tipo) {
        case "nada":
          return;
        case "abrirTexto":
          empezarATipear();
          return;
        case "grabarVoz":
          // Si el 2.º click cayó en el cuadro, el cuadro tiene el foco: se
          // lo sacamos antes de que desaparezca, para que no quede un caret
          // parpadeando en ningún lado ni el teclado vaya a un textarea que
          // ya no está.
          if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
          void empezarAEscuchar("voz");
          return;
        case "pasarADialogo":
          // La grabación sigue: solo cambia el modo y se prende el corte.
          setModo("dialogo");
          grabacionDesdeRef.current = ahora;
          registrar("pasarADialogo");
          void activarCortePorSilencio().catch((error) => {
            console.error("no pude activar el corte por silencio:", error);
          });
          return;
        case "pararGrabacion":
          void detenerYTranscribir(origen);
          return;
        case "mandarTexto":
          void enviar(texto);
          return;
        case "volverAReposo":
          volverAReposo();
          return;
      }
    },
    [texto, enviar, empezarATipear, empezarAEscuchar, detenerYTranscribir, volverAReposo],
  );

  const rachaRef = useRef<Racha>(RACHA_VACIA);

  // Cada click pasa por gestos.ts, que decide sin mirar el DOM ni el reloj
  // de verdad: acá solo se junta la entrada y se ejecuta la acción. Lo que
  // decide está probado con la secuencia real del log.
  const alClick = useCallback(
    (evento: MouseEvent) => {
      if (evento.button !== 0) return;
      const ahora = performance.now();
      const { estado: estadoActual, grabando: grabandoActual, modo: modoActual } = accionesRef.current;
      const rachaAnterior = rachaRef.current;
      const { dentroDeControl, dentroDelCuadro } = clasificarObjetivo(evento.target);
      const msDesdeCambioDeTamano =
        cambioDeTamanoRef.current === null ? null : Math.round(ahora - cambioDeTamanoRef.current);

      const { accion, racha } = decidir({
        estado: estadoActual,
        modo: modoActual,
        grabando: grabandoActual,
        textoVacio: texto.trim() === "",
        dentroDeControl,
        dentroDelCuadro,
        grabacionDesde: grabacionDesdeRef.current,
        msDesdeCambioDeTamano,
        // Un click cierra la respuesta solo si Remi ya no está hablando.
        respuestaQueda: !vozOcupada(),
        ahora,
        racha: rachaAnterior,
      });
      rachaRef.current = racha;

      // isTrusted, detail y la posición: para saber de dónde salen los
      // fantasmas (¿los sintetiza algo? ¿caen todos en el mismo punto?).
      registrar("click", {
        n: racha.n,
        estado: estadoActual,
        modo: modoActual,
        grabando: grabandoActual,
        msDesdeAnterior: rachaAnterior.n === 0 ? -1 : Math.round(ahora - rachaAnterior.ultimo),
        msDesdeResize: msDesdeCambioDeTamano ?? -1,
        confiable: evento.isTrusted,
        detail: evento.detail,
        xy: `${evento.screenX},${evento.screenY}`,
        accion: accion.tipo,
        ...(accion.tipo === "nada" ? { razon: accion.razon } : {}),
      });

      ejecutar(accion, "click", ahora);
    },
    [texto, ejecutar],
  );

  // El gesto se escucha sobre window, en fase de captura: así el textarea
  // no se traga el click, que es lo que pasaba con onClick en el div. Y en
  // mousedown, si este va a ser el 2.º o 3.º click de una racha sobre el
  // cuadro vacío, se le impide al textarea tomar el foco y posicionar el
  // caret: ese click es un gesto, no un click para escribir.
  useEffect(() => {
    const alPresionarEnCaptura = (evento: MouseEvent) => {
      if (evento.button !== 0) return;
      const { dentroDelCuadro } = clasificarObjetivo(evento.target);
      if (!dentroDelCuadro) return;
      if (accionesRef.current.textoVacio && rachaSigueViva(rachaRef.current, performance.now())) {
        evento.preventDefault();
        registrar("mousedown", { rama: "gesto sobre el cuadro vacío: sin foco ni caret" });
      }
    };
    window.addEventListener("mousedown", alPresionarEnCaptura, { capture: true });
    window.addEventListener("click", alClick, { capture: true });
    return () => {
      window.removeEventListener("mousedown", alPresionarEnCaptura, { capture: true });
      window.removeEventListener("click", alClick, { capture: true });
    };
  }, [alClick]);

  // La palanca global: Rust la desrebota y avisa; acá se decide con el
  // mismo módulo y se ejecuta por la misma función que un click. No hay un
  // camino paralelo que pueda desincronizarse del gesto.
  useEffect(() => {
    const suscripcion = alPalanca(() => {
      const { estado: estadoActual, modo: modoActual, grabando: grabandoActual } = accionesRef.current;
      const accion = decidirPalanca({ estado: estadoActual, modo: modoActual, grabando: grabandoActual });
      registrar("palanca", {
        estado: estadoActual,
        modo: modoActual,
        grabando: grabandoActual,
        accion: accion.tipo,
        ...(accion.tipo === "nada" ? { razon: accion.razon } : {}),
      });
      if (accion.tipo === "terminarDialogo") {
        // Se cierra la escucha y lo dicho se transcribe igual; con el modo
        // en "voz", después no se vuelve a armar.
        setModo("voz");
        void detenerYTranscribir("atajo");
        return;
      }
      ejecutar(accion, "atajo", performance.now());
    });
    return () => {
      void suscripcion.then((desuscribir) => desuscribir());
    };
  }, [ejecutar, detenerYTranscribir]);

  // Se arrastra desde cualquier parte de la ventanita, en cualquier estado,
  // salvo dentro del PromptTerminal (ahí hay que poder hacer click y
  // seleccionar texto, no mover la ventana). startDragging() llamado en
  // mousedown se come el evento click en macOS — por eso medimos el
  // movimiento nosotros y solo arrastramos pasado el umbral; por debajo,
  // es un click de verdad y llega a alClick.
  const alPresionar = useCallback((evento: React.MouseEvent<HTMLDivElement>) => {
    if (evento.button !== 0) return;
    // El audio de la voz se analiza (para que el punto lata) solo con un
    // contexto despierto, y eso pide un gesto.
    despertarAudio();
    if ((evento.target as HTMLElement).closest(".prompt-terminal, .acciones-respuesta, .semaforo, .chip-modelo, .boton-cancelar")) return;

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
    <div ref={ventanaRef} className={`ventanita ventanita--${estado}`} onMouseDown={alPresionar}>
      <Semaforo />
      {estado !== "reposo" && <BotonCancelar onCancelar={() => cancelar("x")} />}
      {/* El punto. El modelo se elige en el chip, debajo del cuadro. */}
      <div className="punto-zona">
        <StatusDot estado={estado} escuchandoVoz={grabando} medirVoz={estadoDeVoz} />
      </div>

      {/* Ley 1 en reposo. Si hay algo de hoy que ya hiciste antes, el dato
          medido gana sobre el reloj: sirve más para decidir. */}
      {/* El recordatorio del motor usa el mismo renglón que «hace N min»:
          no agranda nada, solo lo reemplaza cuatro segundos. */}
      {estado === "reposo" && recordatorio !== null && (
        <p className="num hace recordatorio-motor">{recordatorio}</p>
      )}
      {estado === "reposo" && recordatorio === null && ultimaVezDeHoy !== null && (
        <p className="num hace">la última vez: {formatearDuracion(ultimaVezDeHoy)}</p>
      )}
      {estado === "reposo" && recordatorio === null && ultimaVezDeHoy === null && ultimaInteraccionMs !== null && (
        <p className="num hace">{formatearHace(ultimaInteraccionMs, ahoraMs)}</p>
      )}

      {/* El 3.er click no cambia nada visible: dictado y diálogo se ven
          igual, y a las 16:59 eso hizo creer que el triple click no había
          entrado. Una palabra chica bajo el punto, mientras escucha. */}
      {estado === "escuchando" && grabando && modo === "dialogo" && (
        <p className="num modo-escucha">diálogo</p>
      )}
      {/* En diálogo, lo último que dijo Remi sigue a la vista mientras te
          escucha: a 2× no siempre se entiende al oído. */}
      {estado === "escuchando" && modo === "dialogo" && respuestaTexto !== "" && (
        <p className="display-it voz voz--tuya">{limpiarMarkdown(respuestaTexto)}</p>
      )}

      {/* Estado visible mientras whisper trabaja: el punto ya está en
          `pensar`; esta línea lo nombra para que no sea un hueco mudo. */}
      {estado === "pensando" && transcribiendo && (
        <p className="num trabajando">transcribiendo</p>
      )}
      {/* Mientras Remi piensa: lo que le dijiste, bajo el punto gris. */}
      {estado === "pensando" && !transcribiendo && textoEnviado !== "" && (
        <p className="display-it voz voz--tuya">{textoEnviado}</p>
      )}

      {estado === "hablando" && tipoRespuesta === "encargo" && <Encargo texto={respuestaTexto} />}
      {estado === "hablando" && tipoRespuesta !== "encargo" && (
        <p className="display-it voz">{limpiarMarkdown(respuestaTexto)}</p>
      )}
      {estado === "hablando" && (
        <AccionesRespuesta
          onEscuchar={leerEnVozAlta}
          onCallar={callarse}
          onCopiar={() => void copiar()}
          copiado={copiado}
          onReintentar={() => {
            registrar("reintentar", { palabras: textoEnviado.split(/\s+/).length });
            void enviar(textoEnviado, true);
          }}
        />
      )}
      {/* Lo de más (nota y Reloj) solo con el mouse encima: en la maqueta
          la respuesta va sola bajo el punto, con sus tres acciones. */}
      {estado === "hablando" && (
        <div className="extras-respuesta">
        {estado === "hablando" && notaRespuesta !== null && (
          <p className="num nota-respuesta">{notaRespuesta}</p>
        )}
        {estado === "hablando" && ultimaVezMin !== null && sesionInicio !== null && (
          <Reloj
            minutosTranscurridos={(Date.now() - new Date(sesionInicio).getTime()) / 60000}
            ultimaVezMin={ultimaVezMin}
          />
        )}
        </div>
      )}

      {/* Mientras el micrófono está abierto, o mientras Remi habla, no hay
          cuadro — una sola locura por pantalla (ley 4): se ve que escucha o
          que contesta, no un textarea deshabilitado de fondo. */}
      {estado === "escuchando" && !grabando && modo !== "dialogo" && (
        <PromptTerminal
          valor={texto}
          deshabilitado={estado !== "escuchando"}
          enfocar={estado === "escuchando" && !grabando}
          onCambio={setTexto}
          onEnviar={() => void enviar(texto)}
          chip={
            <div className="prompt-terminal__ajustes">
            <ChipModelo
              cerebro={cerebro}
              nivel={nivel}
              motores={motores}
              deshabilitado={estado !== "escuchando"}
              onCerebro={cambiarCerebro}
              onNivel={cambiarNivel}
            />
            <AjustesVoz
              velocidad={velocidad}
              onVelocidad={cambiarVelocidad}
              voces={vocesDisponibles}
              voz={vozElegida}
              onVoz={cambiarVoz}
            />
            </div>
          }
        />
      )}
    </div>
  );
}

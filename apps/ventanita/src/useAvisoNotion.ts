// El aviso de Notion llega a la ventanita: la trae encima de las demás ventanas,
// entra deslizándose, suena una vez y se va cuando contestas. Lo puro
// (qué mostrar, dónde ponerla) está en avisoNotion.ts.
import { invoke } from "@tauri-apps/api/core";
import { LogicalPosition, LogicalSize, currentMonitor, getCurrentWindow } from "@tauri-apps/api/window";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  avisoEnPantalla,
  lugarDelAviso,
  MS_ENTRE_CONSULTAS_AVISO_NOTION,
  obtenerAvisoNotionPendiente,
  responderAvisoNotion,
  TAMANO_AVISO_NOTION,
  type AvisoDeNotion,
  type RespuestaAvisoNotion,
} from "./avisoNotion";
import type { Pantalla } from "./ventana";

// Lo mismo que dura la animación en la tarjeta (DURACION_APARECER de App).
const MS_SALIDA = 250;
// Tras contestar, el núcleo puede tardar en soltarlo; no se vuelve a pintar el mismo.
const MS_IGNORAR_TRAS_RESPONDER = 15000;

interface Geometria {
  x: number;
  y: number;
  width: number;
  height: number;
}
interface Previo {
  actual: Geometria | null;
  elevada: boolean;
}

async function pantallaActual(): Promise<Pantalla | null> {
  const monitor = await currentMonitor();
  if (!monitor) return null;
  const f = monitor.scaleFactor;
  return {
    x: monitor.position.x / f,
    y: monitor.position.y / f,
    width: monitor.size.width / f,
    height: monitor.size.height / f,
  };
}

async function elevar(previo: Previo, id: string, sonados: Set<string>): Promise<void> {
  const ventana = getCurrentWindow();
  avisoEnPantalla.activo = true;
  previo.elevada = true;
  if (!previo.actual) {
    const [posicion, tamano, f] = await Promise.all([ventana.outerPosition(), ventana.outerSize(), ventana.scaleFactor()]);
    previo.actual = { x: posicion.x / f, y: posicion.y / f, width: tamano.width / f, height: tamano.height / f };
  }
  const pantalla = await pantallaActual();
  await ventana.setSize(new LogicalSize(TAMANO_AVISO_NOTION.width, TAMANO_AVISO_NOTION.height));
  if (pantalla) {
    const lugar = lugarDelAviso(pantalla, TAMANO_AVISO_NOTION);
    await ventana.setPosition(new LogicalPosition(lugar.x, lugar.y));
  }
  await ventana.setAlwaysOnTop(true);
  await ventana.setVisibleOnAllWorkspaces(true);
  await ventana.show();
  // Sin setFocus: no le quita el teclado a lo que estás escribiendo.
  if (!sonados.has(id)) {
    sonados.add(id);
    void invoke("sonar_aviso").catch(() => undefined);
  }
}

async function bajar(previo: Previo, restaurar: boolean): Promise<void> {
  // Nada que bajar si nunca se subió: no se toca la ventana de nadie.
  if (!previo.elevada) return;
  const ventana = getCurrentWindow();
  await ventana.setAlwaysOnTop(false);
  await ventana.setVisibleOnAllWorkspaces(false);
  const antes = previo.actual;
  previo.actual = null;
  if (restaurar && antes) {
    await ventana.setSize(new LogicalSize(antes.width, antes.height));
    await ventana.setPosition(new LogicalPosition(antes.x, antes.y));
  }
  previo.elevada = false;
  avisoEnPantalla.activo = false;
}

/**
 * `puedeMostrar`: solo en reposo y sin un nudge en la isla — nunca mientras
 * escribes o hablas. Mientras no se puede, ni siquiera se le pregunta al
 * núcleo (preguntar «saca» el aviso y gasta el presupuesto del día).
 */
export function useAvisoNotion(puedeMostrar: boolean) {
  const [aviso, setAviso] = useState<AvisoDeNotion | null>(null);
  const [saliendo, setSaliendo] = useState(false);
  const puedeRef = useRef(puedeMostrar);
  puedeRef.current = puedeMostrar;
  const avisoRef = useRef(aviso);
  avisoRef.current = aviso;
  const saliendoRef = useRef(false);
  const ignorarRef = useRef<{ id: string; hasta: number } | null>(null);
  const sonadosRef = useRef(new Set<string>());
  const previoRef = useRef<Previo>({ actual: null, elevada: false });
  const colaRef = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    let vivo = true;
    const consultar = async () => {
      if (!puedeRef.current && avisoRef.current === null) return;
      const nuevo = await obtenerAvisoNotionPendiente();
      if (!vivo || saliendoRef.current) return;
      const ignorar = ignorarRef.current;
      if (nuevo && ignorar && ignorar.id === nuevo.id && Date.now() < ignorar.hasta) return;
      setAviso((previo) => (previo && nuevo && previo.id === nuevo.id ? previo : nuevo));
    };
    void consultar();
    const id = window.setInterval(() => void consultar(), MS_ENTRE_CONSULTAS_AVISO_NOTION);
    return () => {
      vivo = false;
      window.clearInterval(id);
    };
  }, []);

  const id = aviso?.id ?? null;
  useEffect(() => {
    const visible = id !== null && puedeMostrar;
    const hacer = visible
      ? () => elevar(previoRef.current, id, sonadosRef.current)
      : () => bajar(previoRef.current, id === null);
    // En fila: subir y bajar no se pisan aunque lleguen seguidos.
    colaRef.current = colaRef.current.then(hacer).catch(() => undefined);
  }, [id, puedeMostrar]);

  const responder = useCallback((respuesta: RespuestaAvisoNotion) => {
    const actual = avisoRef.current;
    if (!actual || saliendoRef.current) return;
    saliendoRef.current = true;
    ignorarRef.current = { id: actual.id, hasta: Date.now() + MS_IGNORAR_TRAS_RESPONDER };
    sonadosRef.current.delete(actual.id); // si vuelve (Ahora no → 2 h), suena otra vez, una
    void responderAvisoNotion(actual.id, respuesta);
    setSaliendo(true);
    window.setTimeout(() => {
      setAviso((previo) => (previo?.id === actual.id ? null : previo));
      setSaliendo(false);
      saliendoRef.current = false;
    }, MS_SALIDA);
  }, []);

  return { aviso, saliendo, responder };
}

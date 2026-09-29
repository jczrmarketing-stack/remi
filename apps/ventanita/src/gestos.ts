// La lógica de los gestos, sin React y sin Tauri: entra el estado y el
// reloj, sale una acción. Así se puede probar la secuencia exacta que quedó
// en el log en vez de intentar reproducirla a mano con el mouse.
//
// Lo que cambió respecto del diseño viejo: ya NO hay temporizador de
// decisión. El 2.º click empieza a grabar en el acto y el 3.º cambia el modo
// sobre la grabación en curso. Esperar 520 ms a ver si venía un tercero era
// justo lo que hacía que el triple casi nunca saliera, y que el click
// siguiente cayera sobre una grabación recién nacida y la matara.
import type { Estado, Modo } from "./tipos";

// Dos clicks cuentan como racha si entran en esta ventana. 700 y no 550:
// el 1.er click hace crecer la ventana (250 ms de animación) y el cuadro
// aparece bajo el mouse; el 2.º de la prueba real de las 16:18 llegó a
// 584 ms. Un doble click humano sobre algo que se mueve no entra en 550.
export const MS_RACHA = 700;
// El triple click se mide desde el PRIMER click: tres clicks en menos de
// dos segundos son un triple, aunque el 3.º venga lento. Con 700 ms entre
// cada uno, un ritmo tranquilo (0, 700, 1600) dejaba al 3.º fuera de la
// racha y, ya fuera de la gracia, PARABA la grabación (16:51:35).
export const MS_TRIPLE = 2000;
// Desde que arranca (o se re-arma, o pasa a diálogo) una grabación, ningún
// click la para. Es el resto de la racha del usuario: los dedos siguen
// cayendo después del gesto, y no tienen por qué cortar lo que el gesto
// acaba de abrir. 1000 y no 900: el 4.º click de la secuencia de las 15:31
// cayó a 934 ms del 3.º.
export const MS_GRACIA = 1000;

export interface Racha {
  /** Cuántos clicks seguidos van. 0 = no hay racha en curso. */
  n: number;
  /** Cuándo cayó el primero de esta racha. */
  primero: number;
  /** Cuándo cayó el último, en ms del mismo reloj que `ahora`. */
  ultimo: number;
}

export const RACHA_VACIA: Racha = { n: 0, primero: 0, ultimo: 0 };

/**
 * Si un click ahora seguiría la racha. El 2.º tiene que venir pegado al
 * 1.º (MS_RACHA); del 3.º en adelante alcanza con estar dentro de los
 * MS_TRIPLE del primero. Lo usa también el mousedown de App, para no darle
 * el foco al cuadro en un click que va a ser gesto.
 */
export function rachaSigueViva(racha: Racha, ahora: number): boolean {
  if (racha.n === 0) return false;
  if (ahora - racha.ultimo < MS_RACHA) return true;
  return racha.n >= 2 && ahora - racha.primero < MS_TRIPLE;
}

export interface Entrada {
  estado: Estado;
  modo: Modo;
  grabando: boolean;
  /** Si el cuadro de texto está vacío (un 2.º click puede reemplazarlo). */
  textoVacio: boolean;
  /**
   * El click cayó sobre un control (botones, selector, toggle): nunca es un
   * gesto y no toca la racha.
   */
  dentroDeControl: boolean;
  /**
   * El click cayó dentro del cuadro de texto. Con el cuadro vacío y la racha
   * viva, ES un gesto: el 1.er click hace crecer la ventana y el cuadro
   * aparece justo debajo del mouse, así que el 2.º y el 3.º caen adentro sí
   * o sí. Solo con texto escrito (o fuera de la racha) es para escribir.
   */
  dentroDelCuadro: boolean;
  /** Cuándo arrancó —o se re-armó— la grabación viva. null si no hay. */
  grabacionDesde: number | null;
  ahora: number;
  racha: Racha;
}

export type Accion =
  /** No hacer nada. `razon` va al log: sin eso no se entiende un gesto. */
  | { tipo: "nada"; razon: string }
  | { tipo: "abrirTexto" }
  | { tipo: "grabarVoz" }
  | { tipo: "pasarADialogo" }
  | { tipo: "pararGrabacion" }
  | { tipo: "mandarTexto" }
  | { tipo: "volverAReposo" };

export interface Decision {
  accion: Accion;
  /** La racha ya actualizada: el que llama la guarda para el próximo click. */
  racha: Racha;
}

function siguienteRacha(racha: Racha, ahora: number): Racha {
  // `n > 0` y no `ultimo !== 0`: el reloj puede empezar en 0 (en las
  // pruebas empieza ahí), y un 0 no puede querer decir «nunca».
  if (rachaSigueViva(racha, ahora)) {
    return { n: racha.n + 1, primero: racha.primero, ultimo: ahora };
  }
  return { n: 1, primero: ahora, ultimo: ahora };
}

export function decidir(entrada: Entrada): Decision {
  const {
    estado,
    modo,
    grabando,
    textoVacio,
    dentroDeControl,
    dentroDelCuadro,
    grabacionDesde,
    ahora,
  } = entrada;

  // Un click sobre un control no es un gesto y tampoco corta la racha: el
  // usuario puede estar tocando el toggle entre clicks.
  if (dentroDeControl) {
    return { accion: { tipo: "nada", razon: "dentro de un control" }, racha: entrada.racha };
  }

  // La racha se cuenta ANTES de mirar si cayó en el cuadro. Antes se
  // descartaba primero, y como el cuadro aparece bajo el mouse tras el 1.er
  // click, el 2.º siempre caía adentro: n=1 para siempre, el doble click era
  // imposible por diseño (13 clicks seguidos así en el log de las 16:18).
  const racha = siguienteRacha(entrada.racha, ahora);

  if (dentroDelCuadro && (!textoVacio || racha.n < 2)) {
    const razon = textoVacio ? "dentro del cuadro (1.º de una racha)" : "dentro del cuadro (escribiendo)";
    return { accion: { tipo: "nada", razon }, racha };
  }

  const enGracia = grabacionDesde !== null && ahora - grabacionDesde < MS_GRACIA;

  // — La racha que arma el gesto —

  if (racha.n === 1 && estado === "reposo") {
    return { accion: { tipo: "abrirTexto" }, racha };
  }

  // 2.º click: a grabar, ya. Sin esperar a ver si viene un tercero.
  if (racha.n === 2 && !grabando && textoVacio && estado === "escuchando") {
    return { accion: { tipo: "grabarVoz" }, racha };
  }

  // 3.º click: la grabación SIGUE, solo pasa a diálogo. Reiniciarla perdería
  // lo que ya dijiste mientras hacías el gesto.
  if (racha.n === 3 && grabando && modo === "voz") {
    return { accion: { tipo: "pasarADialogo" }, racha };
  }

  // 4.º y siguientes de la misma racha: sobran, se absorben.
  if (racha.n >= 4 && grabando) {
    return { accion: { tipo: "nada", razon: `absorbido (n=${racha.n})` }, racha };
  }

  // — Con una grabación viva —

  if (grabando) {
    if (enGracia) {
      const desde = Math.round(ahora - (grabacionDesde ?? ahora));
      return { accion: { tipo: "nada", razon: `gracia (${desde} ms)` }, racha };
    }
    // Pasada la gracia, un click para la grabación, en dictado y en
    // diálogo. Antes en diálogo no paraba nunca («lo corta el silencio») y
    // el 29/09 a las 16:44 eso dejó a Juan Camilo trabado 50 segundos
    // dando dobles clicks a una escucha que no cortaba. En diálogo, parar
    // manda lo dicho igual que el silencio; para terminar el diálogo,
    // Escape o la palanca.
    return { accion: { tipo: "pararGrabacion" }, racha };
  }

  // — Transcribiendo —
  // Un doble click para parar es dos clicks: el 1.º para, el 2.º cae con
  // la grabación ya cerrada y Remi transcribiendo. Ese 2.º no puede
  // cancelar. Un click suelto en pensando (n=1) sigue siendo la salida.
  if (estado === "pensando" && racha.n >= 2) {
    return { accion: { tipo: "nada", razon: `2.º click del que paró (n=${racha.n})` }, racha };
  }

  // — Sin grabación —

  // Mientras Remi habla, un click no la calla ni la manda a reposo: el
  // 29/09 a las 17:43 una respuesta que iba bien se canceló por tocar la
  // ventana. Para cortarla está Escape; si no, termina sola.
  if (estado === "hablando") {
    return { accion: { tipo: "nada", razon: "Remi está hablando (Escape para cortar)" }, racha };
  }

  if (estado === "escuchando" && !textoVacio) {
    return { accion: { tipo: "mandarTexto" }, racha };
  }

  if (estado === "reposo") {
    return { accion: { tipo: "abrirTexto" }, racha };
  }

  return { accion: { tipo: "volverAReposo" }, racha };
}

// La palanca (atajo global). No es un click: no cuenta para la racha ni
// respeta la gracia, porque es una tecla, no un dedo que sigue cayendo.
// Sin grabación, graba en modo voz; con grabación, la para. En diálogo, lo
// termina: la escucha se cierra y no se vuelve a armar.
export type AccionPalanca =
  | { tipo: "grabarVoz" }
  | { tipo: "pararGrabacion" }
  | { tipo: "terminarDialogo" }
  | { tipo: "nada"; razon: string };

export function decidirPalanca(entrada: Pick<Entrada, "estado" | "modo" | "grabando">): AccionPalanca {
  if (entrada.grabando) {
    return entrada.modo === "dialogo" ? { tipo: "terminarDialogo" } : { tipo: "pararGrabacion" };
  }
  if (entrada.estado === "pensando" || entrada.estado === "hablando") {
    return { tipo: "nada", razon: `Remi está ${entrada.estado}` };
  }
  return { tipo: "grabarVoz" };
}

// — El corte por silencio —
// Solo el diálogo se corta solo. El dictado lo cortás vos: podés callarte
// cuatro segundos pensando la frase y no tiene por qué mandarse sola.
export function cortePorSilencioAplica(modo: Modo): boolean {
  return modo === "dialogo";
}

// — Escuchas vacías en diálogo —
// Re-armar en el acto hacía que un dedo tardío cayera sobre la escucha
// nueva y la matara. Y re-armar para siempre dejaba a Remi escuchando una
// habitación vacía: dos vacías seguidas quieren decir que no era el
// momento, y se va callada. No es un contador de fallos de nadie (ley 3).
export const MS_ANTES_DE_REARMAR = 1200;
export const MAX_VACIAS_SEGUIDAS = 2;

export type TrasVacia = { tipo: "rearmar"; enMs: number } | { tipo: "reposo" };

export function decidirTrasVacia(vaciasSeguidas: number): TrasVacia {
  if (vaciasSeguidas >= MAX_VACIAS_SEGUIDAS) return { tipo: "reposo" };
  return { tipo: "rearmar", enMs: MS_ANTES_DE_REARMAR };
}

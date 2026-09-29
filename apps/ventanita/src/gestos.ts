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
// Desde que arranca (o se re-arma) una grabación, ningún click la para. Es
// el resto de la racha del usuario: los dedos siguen cayendo después del
// gesto, y no tienen por qué cortar lo que el gesto acaba de abrir.
export const MS_GRACIA = 900;

export interface Racha {
  /** Cuántos clicks seguidos van. 0 = no hay racha en curso. */
  n: number;
  /** Cuándo cayó el último, en ms del mismo reloj que `ahora`. */
  ultimo: number;
}

export const RACHA_VACIA: Racha = { n: 0, ultimo: 0 };

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
  const seguida = racha.n > 0 && ahora - racha.ultimo < MS_RACHA;
  return { n: seguida ? racha.n + 1 : 1, ultimo: ahora };
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
    // El diálogo lo corta el silencio, o Escape, o el atajo: nunca un click.
    // Si un click lo cortara, cada dedo tardío mataría la escucha recién
    // re-armada, que es exactamente lo que pasaba.
    if (modo === "dialogo") {
      return { accion: { tipo: "nada", razon: "en diálogo corta el silencio" }, racha };
    }
    return { accion: { tipo: "pararGrabacion" }, racha };
  }

  // — Sin grabación —

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

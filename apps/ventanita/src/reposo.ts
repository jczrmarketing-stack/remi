// Isla de reposo (3f · 1): sin nada que decir, es solo el punto, 120×44. Al
// volver a reposo con algo para mostrar («la última vez» o «hace N min»),
// se agranda a 210×64 por 4 s y se encoge de nuevo en 200 ms. Con el mouse
// encima vuelve a mostrarse, sin importar el reloj.
export const TAMANO_ISLA_MINIMA = { width: 120, height: 44 };
export const TAMANO_ISLA_CON_TEXTO = { width: 210, height: 64 };
export const MS_ISLA_VISIBLE = 4000;
export const MS_ISLA_ENCOGER = 200;

/** Si la isla debe mostrar el texto («la última vez» / «hace N min») ahora. */
export function mostrarTextoIsla(msDesdeReposo: number, hover: boolean, hayContenido: boolean): boolean {
  if (!hayContenido) return false;
  if (hover) return true;
  return msDesdeReposo < MS_ISLA_VISIBLE;
}

export function tamanoIsla(mostrarTexto: boolean) {
  return mostrarTexto ? TAMANO_ISLA_CON_TEXTO : TAMANO_ISLA_MINIMA;
}

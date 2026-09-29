// Cada media hora, en reposo, Remi te recuerda con qué motor estás
// pensando: una etiqueta chica bajo el punto, un solo movimiento de 250 ms
// y se va. No es una alarma ni una animación permanente (el DS dice «nada
// respira»): es un «ah, sigo con este» para decidir si cambiar.
export const MS_ENTRE_RECORDATORIOS = 30 * 60 * 1000;
export const MS_RECORDATORIO_VISIBLE = 4000;

/**
 * Si toca recordar ahora. Solo en reposo: mientras trabajás no se te
 * interrumpe, y el reloj no se reinicia por usar la app — se mide desde el
 * último recordatorio, no desde el último click.
 */
export function tocaRecordar(ultimo: number, ahora: number, enReposo: boolean): boolean {
  return enReposo && ahora - ultimo >= MS_ENTRE_RECORDATORIOS;
}

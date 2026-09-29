import { getCurrentWindow } from "@tauri-apps/api/window";
import { registrar } from "../registro";
import "./Semaforo.css";

/**
 * Los dos puntos de la esquina superior izquierda, como los de macOS, pero
 * solo cuando el mouse se acerca: el resto del tiempo no existen. Es la
 * ÚNICA forma con el mouse de cerrar u ocultar la ventanita: un click en
 * cualquier otro lado es un gesto de Remi, nunca un «cerrame».
 *
 * Rojo cierra la app. Amarillo la oculta sin cortar nada: si Remi estaba
 * hablando, sigue hablando; vuelve con el atajo de mostrar o abriendo Remi
 * de nuevo. No hay verde: en una píldora no hay nada que maximizar, y el
 * sistema de diseño no tiene ese color.
 */
export function Semaforo() {
  return (
    <div className="semaforo" aria-label="Ventana">
      <button
        type="button"
        className="semaforo__punto semaforo__punto--cerrar"
        aria-label="Cerrar Remi"
        title="Cerrar Remi"
        onClick={(evento) => {
          evento.stopPropagation();
          registrar("semaforo", { accion: "cerrar" });
          void getCurrentWindow().close();
        }}
      />
      <button
        type="button"
        className="semaforo__punto semaforo__punto--ocultar"
        aria-label="Ocultar (vuelve con el atajo de mostrar)"
        title="Ocultar: vuelve con ⌘⌥⇧L o abriendo Remi de nuevo"
        onClick={(evento) => {
          evento.stopPropagation();
          registrar("semaforo", { accion: "ocultar" });
          void getCurrentWindow().hide();
        }}
      />
    </div>
  );
}

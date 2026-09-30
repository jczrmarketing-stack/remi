import { getCurrentWindow } from "@tauri-apps/api/window";
import { registrar } from "../registro";
import "./Semaforo.css";

interface Props {
  // En la píldora los puntos son más chicos: no pueden tapar la bolita.
  enPildora: boolean;
  // Amarillo: volver a la píldora. En la píldora ya está minimizada.
  onMinimizar?: () => void;
  // Verde: en el chat agranda / vuelve; en la píldora abre el chat.
  onVerde: () => void;
  maximizada?: boolean;
}

/**
 * Los tres puntos de macOS en la esquina, solo con el mouse cerca. Los tres
 * tienen vuelta (Juan Camilo, 30/09: el amarillo escondía y no volvía):
 *  · rojo: oculta Remi; vuelve con un click en su ícono del Dock o ⌘⌥⇧L.
 *  · amarillo: minimiza a la píldora, que siempre queda a la vista.
 *  · verde: agranda al 90 % de la pantalla, y otro click la devuelve.
 */
export function Semaforo({ enPildora, onMinimizar, onVerde, maximizada = false }: Props) {
  const tituloVerde = enPildora ? "Abrir el chat" : maximizada ? "Volver al tamaño de antes" : "Agrandar";
  return (
    <div className={`semaforo${enPildora ? " semaforo--pildora" : ""}`} aria-label="Ventana">
      <button
        type="button"
        className="semaforo__punto semaforo__punto--cerrar"
        aria-label="Ocultar Remi (vuelve con el ícono del Dock)"
        title="Ocultar: vuelve con un click en Remi en el Dock, o ⌘⌥⇧L"
        onClick={(evento) => {
          evento.stopPropagation();
          registrar("semaforo", { accion: "ocultar" });
          void getCurrentWindow().hide();
        }}
      />
      <button
        type="button"
        className="semaforo__punto semaforo__punto--minimizar"
        aria-label="Minimizar a la píldora"
        title={enPildora ? "Ya está minimizada" : "Minimizar a la píldora"}
        disabled={!onMinimizar}
        onClick={(evento) => {
          evento.stopPropagation();
          registrar("semaforo", { accion: "minimizar" });
          onMinimizar?.();
        }}
      />
      <button
        type="button"
        className="semaforo__punto semaforo__punto--agrandar"
        aria-label={tituloVerde}
        title={tituloVerde}
        onClick={(evento) => {
          evento.stopPropagation();
          registrar("semaforo", { accion: enPildora ? "abrir" : maximizada ? "restaurar" : "agrandar" });
          onVerde();
        }}
      />
    </div>
  );
}

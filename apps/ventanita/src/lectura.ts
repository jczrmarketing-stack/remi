// Cómo se lee Remi (3d · 11): tema Noche o Claro, y lectura biónica con su
// intensidad. Se guarda y se aplica a toda la ventana (data-tema en <html>,
// que elige los tokens «dia» del DS en tokens.css).
import { useCallback, useEffect, useState } from "react";

export type Tema = "noche" | "claro";

export interface Lectura {
  tema: Tema;
  bionica: boolean;
  // 0 = suave, 1 = fuerte.
  intensidad: number;
}

export const LECTURA_POR_DEFECTO: Lectura = { tema: "noche", bionica: false, intensidad: 0.5 };
const CLAVE = "remi.lectura";

export function obtenerLectura(): Lectura {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (!crudo) return LECTURA_POR_DEFECTO;
    const v = JSON.parse(crudo) as Partial<Lectura>;
    return {
      tema: v.tema === "claro" ? "claro" : "noche",
      bionica: v.bionica === true,
      intensidad:
        typeof v.intensidad === "number" && Number.isFinite(v.intensidad)
          ? Math.min(1, Math.max(0, v.intensidad))
          : LECTURA_POR_DEFECTO.intensidad,
    };
  } catch {
    return LECTURA_POR_DEFECTO;
  }
}

export function fijarLectura(lectura: Lectura): void {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(lectura));
  } catch {
    // Sin almacenamiento, se lee con lo de siempre.
  }
}

export function aplicarTema(tema: Tema): void {
  if (tema === "claro") document.documentElement.dataset.tema = "claro";
  else delete document.documentElement.dataset.tema;
}

export function useLectura(): [Lectura, (cambio: Partial<Lectura>) => void] {
  const [lectura, setLectura] = useState<Lectura>(() => obtenerLectura());
  useEffect(() => aplicarTema(lectura.tema), [lectura.tema]);
  const cambiar = useCallback((cambio: Partial<Lectura>) => {
    setLectura((actual) => {
      const nueva = { ...actual, ...cambio };
      fijarLectura(nueva);
      return nueva;
    });
  }, []);
  return [lectura, cambiar];
}

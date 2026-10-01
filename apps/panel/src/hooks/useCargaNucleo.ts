"use client";
// Carga datos del núcleo; si no contesta, expone el error para que la
// página muestre <Apagado> en vez de romper. `recargar` es lo que cada
// vista llama después de una acción (cerrar hito, responder un nudge).
import { useCallback, useEffect, useState } from "react";

export function useCargaNucleo<T>(cargar: () => Promise<T>) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(() => {
    let vivo = true;
    setCargando(true);
    cargar()
      .then((valor) => {
        if (!vivo) return;
        setDatos(valor);
        setError(null);
      })
      .catch((e: Error) => {
        if (!vivo) return;
        setError(e);
      })
      .finally(() => {
        if (vivo) setCargando(false);
      });
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => recargar(), [recargar]);

  return { datos, error, cargando, recargar };
}

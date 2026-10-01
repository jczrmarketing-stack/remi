"use client";
// Preferencias de lectura: se guardan en este dispositivo (localStorage),
// nunca en el núcleo. Compartidas por contexto para que la cabecera y la
// página vean el mismo valor sin leer el storage dos veces por render.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type PielReloj = "instrumento" | "brasa" | "terminal";

export type Preferencias = {
  tema: "noche" | "dia";
  bionica: boolean;
  intensidad: number; // 55–85
  aire: 1.6 | 1.7 | 1.8;
  pielReloj: PielReloj;
};

export const POR_DEFECTO: Preferencias = {
  tema: "noche",
  bionica: false,
  intensidad: 70,
  aire: 1.7,
  pielReloj: "instrumento",
};

const CLAVE = "remi-panel:preferencias";

function leer(): Preferencias {
  if (typeof window === "undefined") return POR_DEFECTO;
  try {
    const crudo = window.localStorage.getItem(CLAVE);
    if (!crudo) return POR_DEFECTO;
    return { ...POR_DEFECTO, ...JSON.parse(crudo) };
  } catch {
    return POR_DEFECTO;
  }
}

function guardar(prefs: Preferencias) {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(prefs));
  } catch {
    // Privado o bloqueado: la sesión sigue, solo no se recuerda.
  }
}

type Contexto = { prefs: Preferencias; actualizar: (cambios: Partial<Preferencias>) => void };

const PreferenciasContext = createContext<Contexto | null>(null);

export function PreferenciasProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Preferencias>(POR_DEFECTO);

  useEffect(() => {
    setPrefs(leer());
  }, []);

  useEffect(() => {
    document.documentElement.dataset.tema = prefs.tema;
  }, [prefs.tema]);

  const actualizar = useCallback((cambios: Partial<Preferencias>) => {
    setPrefs((actual) => {
      const nuevo = { ...actual, ...cambios };
      guardar(nuevo);
      return nuevo;
    });
  }, []);

  return <PreferenciasContext.Provider value={{ prefs, actualizar }}>{children}</PreferenciasContext.Provider>;
}

export function usePreferencias(): Contexto {
  const contexto = useContext(PreferenciasContext);
  if (!contexto) throw new Error("usePreferencias() necesita <PreferenciasProvider>");
  return contexto;
}
